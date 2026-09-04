#!/usr/bin/env python3
"""Tests for dedupe_hardlink, exercised on throwaway trees.

The tool mutates a 97 GB library that is synced to a NAS, so the behaviours
worth pinning down are the ones whose failure would be silent: a path that
ends up pointing at the wrong content, a file that vanishes mid-run, and an
edit that gets reverted because the scan was stale.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dedupe_hardlink as dh


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """A miniature of the real failure: one volume behind several papers,
    plus a punctuation twin, plus files that must not be touched."""
    volume = b"%PDF-1.4 scanned 1880 volume" + b"x" * 4096
    root = tmp_path / "SharkPapers"
    write(root / "1880" / "Jordan.1880.Description of a new ray.pdf", volume)
    write(root / "1880" / "Garman.1880.Synopsis of the Rhinobatidae.pdf", volume)
    write(root / "1880" / "Garman.1880.Synopsis of the Rhinobatidae..pdf", volume)
    write(root / "1990" / "Unique.1990.Only copy of this one.pdf",
          b"%PDF-1.4 unique" + b"y" * 900)
    # Same size as the volume but different bytes: the size prefilter must not
    # confuse cheap candidacy with identity.
    write(root / "1990" / "SameSize.1990.Different content.pdf",
          b"%PDF-1.4 scanned 1880 volume" + b"z" * 4096)
    return root


def test_scan_finds_only_byte_identical_files(library):
    groups = dh.scan(library, log=lambda *_: None)
    assert len(groups) == 1
    assert groups[0]["n_files"] == 3
    assert groups[0]["n_inodes"] == 3
    names = {os.path.basename(f["path"]) for f in groups[0]["files"]}
    assert "SameSize.1990.Different content.pdf" not in names


def test_classify_separates_twins_from_distinct_records(library):
    groups = dh.scan(library, log=lambda *_: None)
    result = dh.classify(groups[0])
    assert len(result["twins"]) == 1
    twin = result["twins"][0]
    # The trailing full stop is the leftover; the clean name is kept.
    assert twin["keep"]["path"].endswith("Rhinobatidae.pdf")
    assert len(twin["drop"]) == 1
    assert twin["drop"][0]["path"].endswith("Rhinobatidae..pdf")
    # Jordan and Garman are different papers sharing one volume.
    assert len(result["distinct"]) == 2


def test_relink_collapses_inodes_and_preserves_every_path(library):
    groups = dh.scan(library, log=lambda *_: None)
    before = {str(p): p.read_bytes()
              for p in library.rglob("*.pdf")}

    actions = dh.relink_group(groups[0], dry_run=False, log=lambda *_: None)

    assert all(a["status"] == "linked" for a in actions)
    after = {str(p): p.read_bytes() for p in library.rglob("*.pdf")}
    assert after == before, "every path must survive with identical content"

    inodes = {p.stat().st_ino for p in library.rglob("*.pdf")
              if p.read_bytes() == before[str(
                  library / "1880" / "Jordan.1880.Description of a new ray.pdf")]}
    assert len(inodes) == 1, "the three copies should share one inode"


def test_verify_catches_content_drift(library):
    groups = dh.scan(library, log=lambda *_: None)
    actions = dh.relink_group(groups[0], dry_run=False, log=lambda *_: None)
    ok, bad = dh.verify(actions, log=lambda *_: None)
    assert (ok, bad) == (len(actions), 0)

    # Break one path the way a wrong-inode link would, and confirm it is seen.
    victim = Path(actions[0]["path"])
    victim.unlink()
    victim.write_bytes(b"%PDF-1.4 something else entirely")
    ok, bad = dh.verify(actions, log=lambda *_: None)
    assert bad == 1


def test_relink_is_idempotent(library):
    groups = dh.scan(library, log=lambda *_: None)
    dh.relink_group(groups[0], dry_run=False, log=lambda *_: None)

    groups2 = dh.scan(library, log=lambda *_: None)
    assert groups2[0]["n_inodes"] == 1
    actions = dh.relink_group(groups2[0], dry_run=False, log=lambda *_: None)
    assert actions == [], "a second pass should have nothing to do"


def test_relink_skips_a_file_that_changed_since_the_scan(library):
    groups = dh.scan(library, log=lambda *_: None)
    victim = Path(groups[0]["files"][0]["path"])
    # Stand in for an OCR pass landing between scan and relink.  Relinking
    # would silently revert it.
    victim.write_bytes(b"%PDF-1.4 freshly OCRed" + b"q" * 4096)
    os.utime(victim, (0, 0))

    actions = dh.relink_group(groups[0], dry_run=False, log=lambda *_: None)
    statuses = {a["path"]: a["status"] for a in actions}
    assert statuses.get(str(victim), "").startswith("skipped")
    assert victim.read_bytes().startswith(b"%PDF-1.4 freshly OCRed")


def test_dry_run_touches_nothing(library):
    groups = dh.scan(library, log=lambda *_: None)
    before = {str(p): p.stat().st_ino for p in library.rglob("*.pdf")}
    actions = dh.relink_group(groups[0], dry_run=True, log=lambda *_: None)
    assert all(a["status"] == "planned" for a in actions)
    after = {str(p): p.stat().st_ino for p in library.rglob("*.pdf")}
    assert after == before


def test_no_temp_files_left_behind(library):
    groups = dh.scan(library, log=lambda *_: None)
    dh.relink_group(groups[0], dry_run=False, log=lambda *_: None)
    assert not list(library.rglob(".*relink*"))


def test_writer_audit_passes_on_the_real_pipeline():
    """The hardlink safety argument rests on this; assert it rather than
    trusting a one-off grep."""
    problems = dh.check_writers(Path(__file__).resolve().parent,
                                log=lambda *_: None)
    assert problems == [], f"in-place PDF writes found: {problems}"


def test_cli_scan_reports_without_mutating(library, tmp_path):
    out = tmp_path / "scan.json"
    before = {str(p): p.stat().st_ino for p in library.rglob("*.pdf")}
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "dedupe_hardlink.py"),
         "--root", str(library), "--scan", "--json", str(out)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text())
    assert payload["stats"]["groups"] == 1
    assert payload["stats"]["twin_files"] == 1
    after = {str(p): p.stat().st_ino for p in library.rglob("*.pdf")}
    assert after == before
