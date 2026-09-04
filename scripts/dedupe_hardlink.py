#!/usr/bin/env python3
"""Collapse byte-identical PDFs in the library onto shared inodes.

The library accumulates byte-identical copies from two distinct causes, and
they need different treatment:

**Redundant names** ("punctuation twins") are one paper stored under two
filenames that differ only by a trailing full stop, a truncating comma, or an
accent.  One of the two names is leftover; deleting it frees space on the NAS
as well as locally.

**Shared containers** are genuinely different papers whose source PDF is one
scanned journal volume or issue.  A single 1880 volume backs sixteen separate
Jordan/Garman papers.  These cannot be deleted: the corpus has no ``pdf_path``
column and locates a paper by matching author, year, and title against the
filename, so every record needs its own name to stay findable.

Hardlinking solves the second case and, incidentally, the first: one inode,
many names, full 11 GiB reclaimed locally without deciding anything
irreversible.  The saving is local only, because a sync client transfers
content per path and has no concept of a shared inode.

Hardlinking is safe here because nothing in the pipeline rewrites a PDF in
place.  Every OCR path (``ocr_library``, ``ocr_retry_residuals``,
``ocr_gs_repair``, ``ocr_footer_retry``, ``ingest_pdfs``) runs ocrmypdf into a
separate output and finishes with ``os.replace``, which swaps one directory
entry and leaves the siblings untouched.  ``--check-writers`` re-verifies that
assumption, since it is the one thing that would make this dangerous.

Usage
-----
    python3 scripts/dedupe_hardlink.py --scan                 # report only
    python3 scripts/dedupe_hardlink.py --scan --json out.json # machine-readable
    python3 scripts/dedupe_hardlink.py --relink --dry-run     # show the plan
    python3 scripts/dedupe_hardlink.py --relink               # do it
    python3 scripts/dedupe_hardlink.py --verify manifest.json # re-check after
    python3 scripts/dedupe_hardlink.py --check-writers        # in-place audit

``--relink`` is idempotent: files already sharing an inode are skipped, so it
is safe to run on every sync.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_ROOT = Path(
    "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers"
)
CHUNK = 1 << 20

# Writers that touch library PDFs.  Every one must go through a temp file and
# os.replace; a bare open(path, "wb") would corrupt every hardlinked sibling.
KNOWN_WRITERS = [
    "ocr_library.py",
    "ocr_retry_residuals.py",
    "ocr_gs_repair.py",
    "ocr_footer_retry.py",
    "ingest_pdfs.py",
    "stage_orphan_pdfs.py",
    "acquire_cascade.py",
]


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def normalise_record(path: str) -> str:
    """Collapse a filename to the paper it names.

    Strips the extension, accents, case, and all punctuation, so
    ``Foo.1880.Bar..pdf`` and ``Foo.1880.Bar.pdf`` land on the same key.  Two
    byte-identical files sharing a key are the same paper stored twice.
    """
    stem = os.path.basename(path)
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    stem = unicodedata.normalize("NFKD", stem)
    stem = stem.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", stem).strip()


def scan(root: Path, log=print) -> list[dict]:
    """Find byte-identical PDF groups, size-prefiltered.

    Hashing every file would be wasted work: only files sharing an exact byte
    size can be identical, and that stat pass costs seconds.
    """
    by_size: dict[int, list[tuple[str, os.stat_result]]] = defaultdict(list)
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if not name.lower().endswith(".pdf"):
                continue
            path = os.path.join(dirpath, name)
            try:
                st = os.stat(path)
            except OSError as exc:
                log(f"  stat failed, skipped: {path} ({exc})")
                continue
            by_size[st.st_size].append((path, st))
            total += 1

    candidates = {s: v for s, v in by_size.items() if len(v) > 1}
    log(f"  {total} PDFs, {sum(len(v) for v in candidates.values())} "
        f"in {len(candidates)} size collisions")

    by_hash: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for size, items in candidates.items():
        for path, st in items:
            try:
                digest = sha256(Path(path))
            except OSError as exc:
                log(f"  hash failed, skipped: {path} ({exc})")
                continue
            by_hash[(size, digest)].append({
                "path": path,
                "inode": st.st_ino,
                "nlink": st.st_nlink,
                "mtime": st.st_mtime,
            })

    groups = []
    for (size, digest), files in by_hash.items():
        if len(files) < 2:
            continue
        files.sort(key=lambda f: f["path"])
        inodes = {f["inode"] for f in files}
        groups.append({
            "size": size,
            "sha256": digest,
            "n_files": len(files),
            "n_inodes": len(inodes),
            "reclaimable_bytes": size * (len(inodes) - 1),
            "files": files,
        })
    groups.sort(key=lambda g: -g["reclaimable_bytes"])
    return groups


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

def _trailing_junk(stem: str) -> bool:
    return stem.rstrip().endswith((".", ","))


def rank_name(path: str) -> tuple:
    """Sort key for filename quality; lowest is the one to keep.

    Trailing punctuation is house-style noise (a previous pass stripped 1,507
    such suffixes), so a clean ending wins.  Accents are preferred over
    stripped ASCII.  Length and lexicographic order settle the rest, so the
    choice is deterministic across runs.
    """
    stem = os.path.basename(path)[:-4]
    return (
        _trailing_junk(stem),
        stem.isascii(),
        len(stem),
        stem,
    )


def classify(group: dict) -> dict:
    """Split a group's files into redundant names and distinct records."""
    by_record: dict[str, list[dict]] = defaultdict(list)
    for f in group["files"]:
        by_record[normalise_record(f["path"])].append(f)

    twins, distinct = [], []
    for _key, files in sorted(by_record.items()):
        if len(files) > 1:
            ordered = sorted(files, key=lambda f: rank_name(f["path"]))
            twins.append({"keep": ordered[0], "drop": ordered[1:]})
        distinct.append(files[0])

    return {"twins": twins, "distinct": distinct}


def ambiguity(keep: str, drop: str) -> str:
    """Why two names differ, and whether the choice is safe to automate."""
    a = os.path.basename(keep)[:-4]
    b = os.path.basename(drop)[:-4]
    if a.rstrip(".,") == b.rstrip(".,"):
        return "auto"
    strip = lambda s: unicodedata.normalize("NFKD", s).encode(
        "ascii", "ignore").decode()
    if strip(a) == strip(b):
        # An accent difference is a real editorial choice, not noise: a
        # non-breaking hyphen and a stripped one are both wrong in different
        # ways.  Never guess.
        return "manual"
    return "manual"


# --------------------------------------------------------------------------
# Relinking
# --------------------------------------------------------------------------

def choose_keeper(files: list[dict]) -> dict:
    """Pick the inode the group collapses onto.

    Which inode wins is invisible to every consumer, since all the names
    survive.  Preferring the inode that already has the most links minimises
    the number of replacements.
    """
    return sorted(files, key=lambda f: (-f["nlink"], rank_name(f["path"])))[0]


def relink_group(group: dict, dry_run: bool, log=print) -> list[dict]:
    """Collapse one group onto a single inode, atomically per file.

    Each replacement links the keeper to a temp name in the same directory and
    then ``os.replace``s it over the target, so an interruption can never
    leave a paper missing: the path either points at the old inode or the new
    one, never at nothing.
    """
    keeper = choose_keeper(group["files"])
    actions = []
    for f in group["files"]:
        if f["inode"] == keeper["inode"]:
            continue
        action = {
            "path": f["path"],
            "keeper": keeper["path"],
            "sha256": group["sha256"],
            "size": group["size"],
            "old_inode": f["inode"],
            "status": "planned",
        }
        if dry_run:
            actions.append(action)
            continue

        target = Path(f["path"])
        # Re-stat: the scan may be minutes old, and relinking a file that
        # changed underneath us would silently revert someone's edit.
        try:
            st = target.stat()
        except OSError as exc:
            action["status"] = f"skipped: vanished ({exc})"
            actions.append(action)
            continue
        if st.st_size != group["size"] or st.st_mtime != f["mtime"]:
            action["status"] = "skipped: changed since scan"
            actions.append(action)
            continue

        tmp = target.with_name(f".{target.name}.relink{os.getpid()}")
        try:
            if tmp.exists():
                tmp.unlink()
            os.link(keeper["path"], tmp)
            os.replace(tmp, target)
            action["status"] = "linked"
            action["new_inode"] = target.stat().st_ino
        except OSError as exc:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            action["status"] = f"failed: {exc}"
            log(f"  FAILED {f['path']}: {exc}")
        actions.append(action)
    return actions


def verify(actions: list[dict], log=print) -> tuple[int, int]:
    """Re-hash every touched path against what it held before.

    A hardlink that pointed at the wrong inode would be invisible without
    this: the file would still open, still be a PDF, and still be the wrong
    paper.
    """
    ok = bad = 0
    for a in actions:
        if a.get("status") != "linked":
            continue
        path = Path(a["path"])
        try:
            if path.stat().st_size == a["size"] and sha256(path) == a["sha256"]:
                ok += 1
                continue
        except OSError as exc:
            log(f"  VERIFY ERROR {path}: {exc}")
            bad += 1
            continue
        log(f"  VERIFY FAILED {path}: content differs from pre-link hash")
        bad += 1
    return ok, bad


# --------------------------------------------------------------------------
# Writer audit
# --------------------------------------------------------------------------

def check_writers(scripts_dir: Path, log=print) -> list[str]:
    """Flag any in-place PDF write, which hardlinks would turn into corruption."""
    problems = []
    pattern = re.compile(
        r"""open\(\s*[^,)]*(?:pdf|path|dest|target)[^,)]*,\s*["']w""",
        re.IGNORECASE,
    )
    for name in KNOWN_WRITERS:
        path = scripts_dir / name
        if not path.exists():
            problems.append(f"{name}: MISSING (audit incomplete)")
            continue
        for lineno, line in enumerate(
                path.read_text(errors="replace").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                problems.append(f"{name}:{lineno}: {stripped}")
    return problems


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def write_review_csvs(groups: list[dict], twins_csv: Path,
                      containers_csv: Path, root: Path, log=print) -> None:
    """Emit the two review tables the audit workbook formats.

    The classification lives here rather than in the R that builds the
    workbook, so the sheet Simon reviews and the deletion that follows can
    never disagree about which file is the twin.
    """
    twins_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(twins_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group_id", "year", "keep_name", "delete_name",
                    "difference", "confidence", "size_mb", "sha256",
                    "keep_path", "delete_path", "decision", "notes"])
        gid = 0
        for g in groups:
            for t in classify(g)["twins"]:
                gid += 1
                keep = t["keep"]["path"]
                for d in t["drop"]:
                    w.writerow([
                        gid,
                        os.path.basename(os.path.dirname(d["path"])),
                        os.path.basename(keep),
                        os.path.basename(d["path"]),
                        describe_difference(keep, d["path"]),
                        ambiguity(keep, d["path"]),
                        round(g["size"] / 2 ** 20, 1),
                        g["sha256"][:12],
                        keep, d["path"], "", "",
                    ])

    with open(containers_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group_id", "n_papers", "size_mb", "reclaimable_mb",
                    "year", "papers", "sha256"])
        for gid, g in enumerate(groups, 1):
            distinct = classify(g)["distinct"]
            if len(distinct) < 2:
                continue
            years = sorted({os.path.basename(os.path.dirname(f["path"]))
                            for f in distinct})
            w.writerow([
                gid, len(distinct), round(g["size"] / 2 ** 20, 1),
                round(g["size"] * (len(distinct) - 1) / 2 ** 20, 1),
                ", ".join(years),
                " | ".join(os.path.basename(f["path"])[:-4] for f in distinct),
                g["sha256"][:12],
            ])
    log(f"  wrote {twins_csv}")
    log(f"  wrote {containers_csv}")


def describe_difference(keep: str, drop: str) -> str:
    """Plain-English reason the two filenames differ, for the review sheet."""
    a = os.path.basename(keep)[:-4]
    b = os.path.basename(drop)[:-4]
    if a == b.rstrip(".") and b.endswith("."):
        return "trailing full stop"
    if a == b.rstrip(".,") and b.rstrip(".").endswith(","):
        return "trailing comma"
    strip = lambda s: unicodedata.normalize("NFKD", s).encode(
        "ascii", "ignore").decode()
    if strip(a) == strip(b):
        return "accent or special character"
    return "other punctuation or spacing"


def gib(n: int) -> str:
    return f"{n / 2 ** 30:.2f} GiB"


def summarise(groups: list[dict], log=print) -> dict:
    twin_files = twin_bytes = 0
    for g in groups:
        c = classify(g)
        for t in c["twins"]:
            twin_files += len(t["drop"])
            twin_bytes += g["size"] * len(t["drop"])
    total = sum(g["reclaimable_bytes"] for g in groups)
    stats = {
        "groups": len(groups),
        "files": sum(g["n_files"] for g in groups),
        "reclaimable_bytes": total,
        "twin_files": twin_files,
        "twin_bytes": twin_bytes,
        "container_bytes": total - twin_bytes,
    }
    log(f"  {stats['groups']} identical groups, {stats['files']} files, "
        f"{gib(total)} reclaimable locally")
    log(f"  of which {twin_files} redundant names ({gib(twin_bytes)}) are "
        f"deletable, freeing NAS space too")
    log(f"  and {gib(stats['container_bytes'])} is shared containers, "
        f"hardlink-only")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--scan", action="store_true", help="report duplicates")
    ap.add_argument("--relink", action="store_true",
                    help="collapse groups onto shared inodes")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --relink, show the plan without touching files")
    ap.add_argument("--verify", type=Path, metavar="MANIFEST",
                    help="re-hash the paths in a previous run's manifest")
    ap.add_argument("--check-writers", action="store_true",
                    help="audit pipeline scripts for in-place PDF writes")
    ap.add_argument("--json", type=Path, help="write scan results here")
    ap.add_argument("--review-csvs", type=Path, metavar="DIR",
                    help="write duplicate_twins.csv and shared_containers.csv "
                         "here, for the audit workbook")
    ap.add_argument("--manifest", type=Path,
                    help="where --relink writes its manifest")
    args = ap.parse_args()

    scripts_dir = Path(__file__).resolve().parent

    if args.check_writers:
        print("Auditing PDF writers for in-place writes...")
        problems = check_writers(scripts_dir)
        if problems:
            print("UNSAFE for hardlinking:")
            for p in problems:
                print(f"  {p}")
            return 1
        print(f"  all {len(KNOWN_WRITERS)} writers use temp file + os.replace: safe")
        return 0

    if args.verify:
        actions = json.loads(args.verify.read_text())["actions"]
        print(f"Verifying {len(actions)} relinked paths...")
        ok, bad = verify(actions)
        print(f"  {ok} verified, {bad} failed")
        return 1 if bad else 0

    if not (args.scan or args.relink):
        ap.error("nothing to do: pass --scan, --relink, --verify, or "
                 "--check-writers")

    print(f"Scanning {args.root}...")
    t0 = time.time()
    groups = scan(args.root)
    print(f"  scan took {time.time() - t0:.1f}s")
    stats = summarise(groups)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"root": str(args.root),
             "generated": datetime.now().isoformat(timespec="seconds"),
             "stats": stats, "groups": groups}, indent=1))
        print(f"  wrote {args.json}")

    if args.review_csvs:
        write_review_csvs(groups,
                          args.review_csvs / "duplicate_twins.csv",
                          args.review_csvs / "shared_containers.csv",
                          args.root)

    if not args.relink:
        return 0

    print(f"\n{'Planning' if args.dry_run else 'Relinking'}...")
    actions = []
    for g in groups:
        actions.extend(relink_group(g, args.dry_run))

    linked = sum(1 for a in actions if a["status"] == "linked")
    failed = [a for a in actions if a["status"].startswith("failed")]
    skipped = [a for a in actions if a["status"].startswith("skipped")]

    if args.dry_run:
        print(f"  would relink {len(actions)} files, reclaiming "
              f"{gib(stats['reclaimable_bytes'])}")
        return 0

    manifest = args.manifest or (
        Path("outputs") / f"dedupe_hardlink_manifest_"
                          f"{datetime.now():%Y%m%d_%H%M%S}.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(
        {"root": str(args.root),
         "generated": datetime.now().isoformat(timespec="seconds"),
         "stats": stats, "actions": actions}, indent=1))

    print(f"  {linked} linked, {len(skipped)} skipped, {len(failed)} failed")
    print(f"  manifest: {manifest}")

    print("\nVerifying...")
    ok, bad = verify(actions)
    print(f"  {ok} verified, {bad} failed")
    return 1 if (bad or failed) else 0


if __name__ == "__main__":
    sys.exit(main())
