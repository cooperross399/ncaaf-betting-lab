"""The forward ledger on `card-feed` can never be one file GitHub refuses.

On 2026-11-02 the feed's single `forward_evidence.csv` reached 105 MB and
every publish after it was rejected (GitHub's limit is 100 MB). The ledger
now travels as gzip in byte slices under `forward_evidence/`, the old file
is still read so the branch as it stood restores, and the round trip is
byte for byte: no frozen opinion may be lost to a storage change.

These tests run git against a local bare repository; nothing touches the
network and nothing is written inside the checkout.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ncaaf_betting_lab.leagues import DEFAULT_LEAGUE_KEY, league_for

LEAGUE = league_for(DEFAULT_LEAGUE_KEY)

ROOT = Path(__file__).resolve().parents[1]


def load_feed():
    spec = importlib.util.spec_from_file_location("card_feed", ROOT / "scripts" / "card_feed.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["card_feed"] = module
    spec.loader.exec_module(module)
    return module


def ledger_bytes(rows: int) -> bytes:
    header = "snapshot_date,game_id,market,selection,line,gates_in_force\n"
    gates = "x" * 186
    body = "".join(
        f"2026-10-{1 + i % 28:02d},{i},spread,home,-3.5,{gates}\n" for i in range(rows)
    )
    return (header + body).encode()


def test_packing_round_trips_byte_for_byte_and_slices_a_large_ledger() -> None:
    feed = load_feed()
    data = os.urandom(5000) + ledger_bytes(500)  # incompressible head forces slices
    parts = feed.pack_ledger(data, part_bytes=1024)
    assert len(parts) > 1
    assert all(len(p) <= 1024 for p in parts.values())
    assert feed.unpack_ledger(parts) == data
    # Deterministic, so an unchanged ledger is unchanged blobs.
    assert feed.pack_ledger(data, part_bytes=1024) == parts


def test_a_missing_slice_is_refused_not_restored_short() -> None:
    feed = load_feed()
    parts = feed.pack_ledger(os.urandom(4000), part_bytes=1000)
    del parts[sorted(parts)[1]]
    with pytest.raises(feed.FeedError):
        feed.unpack_ledger(parts)


def test_the_slices_sit_far_under_githubs_limit() -> None:
    feed = load_feed()
    assert feed.LEDGER_PART_BYTES < feed.MAX_BLOB_BYTES < 100 * 1024 * 1024


def git(cwd: Path, *args: str, stdin: bytes | None = None) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, input=stdin, capture_output=True, check=True
    ).stdout.decode()


@pytest.fixture
def local_feed(tmp_path, monkeypatch):
    feed = load_feed()
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)

    def make():
        workdir = Path(os.path.realpath(str(tmp_path))) / f"work{len(list(tmp_path.glob('work*')))}"
        workdir.mkdir()
        subprocess.run(["git", "init", "-q", str(workdir)], check=True)
        handle = feed.Feed("owner/repo", "token", workdir)
        handle.remote = str(bare)
        return handle

    processed, archive, outputs = (tmp_path / n for n in ("processed", "archive", "outputs"))
    for d in (processed, archive, outputs):
        d.mkdir()
    monkeypatch.setattr(feed, "_feed", make)
    monkeypatch.setattr(feed, "PROCESSED_DIR", processed)
    monkeypatch.setattr(feed, "ARCHIVE_DIR", archive)
    monkeypatch.setattr(feed, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(feed, "_today", lambda league: "2026-11-02")
    return feed, bare, processed


def seed_legacy(bare: Path, tmp_path: Path, data: bytes) -> None:
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", str(seed)], check=True)
    sha = git(seed, "hash-object", "-w", "--stdin", stdin=data).strip()
    status = git(seed, "hash-object", "-w", "--stdin",
                 stdin=json.dumps({"slate_date": "2026-11-01"}).encode()).strip()
    tree = git(seed, "mktree", stdin=(
        f"100644 blob {status}\tlatest_status.json\n"
        f"100644 blob {sha}\tforward_evidence.csv\n").encode()).strip()
    commit = git(seed, "-c", "user.name=t", "-c", "user.email=t@t",
                 "commit-tree", tree, "-m", "legacy").strip()
    git(seed, "push", "-q", str(bare), f"{commit}:refs/heads/card-feed")


def test_the_legacy_single_file_restores_and_migrates_without_losing_a_row(
    local_feed, tmp_path
) -> None:
    feed, bare, processed = local_feed
    league = LEAGUE
    original = ledger_bytes(2000)
    seed_legacy(bare, tmp_path, original)

    assert feed.cmd_restore(league) == 0
    local = processed / feed.LEDGER_FILENAME
    assert local.read_bytes() == original

    appended = original + b"2026-11-02,9999,spread,away,3.5,y\n"
    local.write_bytes(appended)
    assert feed.cmd_publish(league, run_id="1") == 0

    tip = git(bare, "ls-tree", "-r", "-l", "card-feed")
    assert "forward_evidence/forward_evidence.csv.gz.part000" in tip
    assert "\tforward_evidence.csv\n" not in tip + "\n"
    assert all(int(line.split()[3]) < 100 * 1024 * 1024
               for line in tip.splitlines() if " blob " in line)

    local.unlink()
    assert feed.cmd_restore(league) == 0
    assert local.read_bytes() == appended


def test_a_run_with_no_local_ledger_carries_the_feeds_forward(local_feed, tmp_path) -> None:
    feed, bare, processed = local_feed
    original = ledger_bytes(300)
    local = processed / feed.LEDGER_FILENAME
    local.write_bytes(original)
    assert feed.cmd_publish(LEAGUE, run_id="1") == 0
    local.unlink()
    assert feed.cmd_publish(LEAGUE, run_id="2") == 0
    assert feed.cmd_restore(LEAGUE) == 0
    assert local.read_bytes() == original
