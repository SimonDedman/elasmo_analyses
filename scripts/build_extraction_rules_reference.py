#!/usr/bin/env python3
"""Regenerate the two public views of the keyword rules from their single source of truth,
scripts/extract_schema_columns.py, and link every rule back to the line that defines it.

Writes  outputs/extraction_rules.json and docs/schema_proposals/extraction_rules.json (public copy): every keyword column of the 7 schemas (eco_, pr_, gear_,
                                                 imp_, d_, b_, sb_): terms, threshold, anchors, case-sensitive
                                                 terms, prerequisites, proximity filter, section weights, and
                                                 the defining line + GitHub URL
        docs/schema_proposals/extraction_review_reference.md   Part 2: the keyword table of each schema section
                                                 is replaced in place (prose, derived-column tables and the
                                                 hand-written Label / Known issues cells are kept; a sub-basin
                                                 section is added after the ocean-basin one)
        docs/schema_proposals/extraction_review_reference.html via pandoc, as before

    python3 scripts/build_extraction_rules_reference.py [--check]

--check reports what would change and exits 1 if the tables are stale, for use before a commit.
Both outputs were hand-maintained until 2026-10-07 and had drifted (d_fisheries showed 8 of 13 terms,
gear_ghost was missing, nine listed columns no longer existed in the extractor).
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_schema_columns as X  # noqa: E402

SRC = ROOT / "scripts" / "extract_schema_columns.py"
MD = ROOT / "docs" / "schema_proposals" / "extraction_review_reference.md"
HTML = MD.with_suffix(".html")
JSON_OUT = ROOT / "outputs" / "extraction_rules.json"
JSON_PUBLIC = ROOT / "docs" / "schema_proposals" / "extraction_rules.json"   # outputs/ is git-ignored; this copy is on the site
GH = "https://github.com/SimonDedman/elasmo_analyses/blob/main/scripts/extract_schema_columns.py"
SCHEMA_TITLES = {"eco_": "Ecosystem", "pr_": "Pressure", "gear_": "Gear", "imp_": "Impact", "d_": "Discipline",
                 "b_": "Ocean basin", "sb_": "Sub-basin"}
LABELS = {"gear_ghost": "Ghost gear"}   # labels for columns added since the table was hand-written
TABLE_HDR = re.compile(r"^\| Column \| Label \| Keywords \|")


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def source_lines():
    """column name -> 1-based line of its BinaryColumn(...) definition in the extractor."""
    out = {}
    for i, line in enumerate(SRC.read_text().splitlines(), 1):
        m = re.search(r'BinaryColumn\(\s*"([a-z_0-9]+)"', line)
        if m:
            out.setdefault(m.group(1), i)
    return out


def techniques(col, proximity):
    """Technique codes from the legend in Part 1, derived from the column definition itself."""
    t = ["KFT"]
    if any("*" in x for x in col.terms):
        t.append("WC")
    if any(" " in x or "-" in x for x in col.terms):
        t.append("PH")
    if any(X._parse_and_term(x) for x in col.terms):
        t.append("AND")
    if any("\\" in x for x in col.terms):
        t.append("RX")
    if col.case_sensitive_terms:
        t.append("AC")
    if col.anchors:
        t.append("ANC")
    if col.prerequisite_terms:
        t.append("PRE")
    if proximity:
        t.append("KPC")
    t.append("SW")
    return ", ".join(t)


def rules():
    lines = source_lines()
    out = {}
    for schema in X.ALL_SCHEMAS:
        d = out.setdefault(schema.prefix, {})
        for c in schema.columns:
            ln = lines.get(c.name)
            d[c.name] = {"terms": list(c.terms), "threshold": c.threshold, "anchors": list(c.anchors or []),
                         "case_sensitive_terms": sorted(c.case_sensitive_terms or []),
                         "prerequisite_terms": dict(c.prerequisite_terms or {}),
                         "proximity": c.name in X.PROXIMITY_CHECK_COLUMNS,
                         "line": ln, "url": f"{GH}#L{ln}" if ln else None}
    return out


def write_json(R, head):
    doc = {"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M %Z"), "source": "scripts/extract_schema_columns.py",
                     "commit": head, "regenerate_with": "python3 scripts/build_extraction_rules_reference.py",
                     "n_rules": sum(len(v) for v in R.values()),
                     "section_weights": X._SECTION_WEIGHTS,
                     "note": "Line numbers and URLs point at the commit named here; they drift as the extractor is edited, "
                             "so regenerate after any change to it."}}
    doc.update(R)
    for path in (JSON_OUT, JSON_PUBLIC):
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return doc


def label_from_name(name):
    if name in LABELS:
        return LABELS[name]
    return name.split("_", 1)[1].replace("_", " ").capitalize()


def parse_old_rows(block):
    """Hand-written cells worth keeping from the current table: column -> (label, notes). Names listed in an
    earlier run's "no longer keyword columns" footer are carried as empty entries so the footer persists."""
    keep = {}
    for line in block:
        if line.startswith("*No longer keyword"):
            for name in re.findall(r"`([a-z_0-9]+)`", line):
                keep.setdefault(name, ("", ""))
            continue
        m = re.match(r"^\| `([a-z_0-9]+)` \|(.*)\|\s*$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        keep[m.group(1)] = (cells[0] if cells else "", cells[-1] if cells else "")
    return keep


def render_table(prefix, R, old):
    cols = R[prefix]
    with_anchors = any(v["anchors"] for v in cols.values())
    hdr = ["Column", "Label", "Keywords", "Threshold"] + (["Anchors"] if with_anchors else []) + ["Techniques", "Source", "Known issues / notes"]
    rows = ["| " + " | ".join(hdr) + " |", "|" + "|".join("-" * (len(h) + 2) for h in hdr) + "|"]
    for name, v in cols.items():
        label, notes = old.get(name, (label_from_name(name), ""))
        kws = ", ".join(("**" + t + "**" if t in v["case_sensitive_terms"] else t) for t in v["terms"])
        if v["prerequisite_terms"]:
            kws += " (" + "; ".join(f"{k} only with {' / '.join(p)}" for k, p in v["prerequisite_terms"].items()) + ")"
        col = next(c for s in X.ALL_SCHEMAS for c in s.columns if c.name == name)
        cells = [f"`{name}`", label or label_from_name(name), kws.replace("|", "\\|"), str(v["threshold"])]
        if with_anchors:
            cells.append(", ".join(v["anchors"]))
        cells += [techniques(col, v["proximity"]), f"[L{v['line']}]({v['url']})" if v["line"] else "", notes]
        rows.append("| " + " | ".join(cells) + " |")
    removed = sorted(set(old) - set(cols))
    tail = ["", f"*Case-sensitive terms in bold. Rows regenerated from the extractor; the Label and Known issues cells are hand-written and kept.*"]
    if removed:
        tail.append(f"*No longer keyword columns in the extractor (rows dropped from this table): {', '.join('`' + r + '`' for r in removed)}.*")
    return rows + tail


def update_md(R, head, check=False):
    text = MD.read_text()
    lines = text.split("\n")
    heads = [(i, m.group(1)) for i, l in enumerate(lines) if (m := re.match(r"^### .*\(`([a-z]+_)`\)", l))]
    found = {p: i for i, p in heads}
    changed = []
    # bottom-up, so earlier line numbers never shift under us
    for i, prefix in sorted(heads, reverse=True):
        if prefix not in R:
            continue
        j = next((k for k in range(i + 1, len(lines)) if re.match(r"^##(#)? ", lines[k])), len(lines))
        t0 = next((k for k in range(i, j) if TABLE_HDR.match(lines[k])), None)
        if t0 is None:
            continue
        t1 = t0
        while t1 < j and lines[t1].startswith("|"):
            t1 += 1
        f1 = t1   # swallow an earlier generated footer
        while f1 < j and (lines[f1].strip() == "" or lines[f1].startswith("*Case-sensitive") or lines[f1].startswith("*No longer keyword")):
            f1 += 1
        old = parse_old_rows(lines[t0:f1])
        new = render_table(prefix, R, old) + [""]
        if lines[t0:f1] != new:
            changed.append(prefix)
        lines[t0:f1] = new
        lines[i] = re.sub(r"— \d+ (binary )?columns?", lambda m: f"— {len(R[prefix])} {m.group(1) or ''}columns", lines[i], count=1)
    found = {m.group(1): i for i, l in enumerate(lines) if (m := re.match(r"^### .*\(`([a-z]+_)`\)", l))}   # positions moved above
    if "sb_" not in found and "b_" in found:
        i = found["b_"]
        j = next((k for k in range(i + 1, len(lines)) if re.match(r"^##(#)? ", lines[k])), len(lines))
        new = [f"### Sub-basin (`sb_`) — {len(R['sb_'])} columns", "",
               "Forty-three named seas and regional sub-basins, one column each, matched the same way as the ocean basins. "
               "Added to the register 2026-10-06 as the geography topic *Sub-basins and seas* on the topic review pages.", ""]
        new += render_table("sb_", R, {}) + ["", "---", ""]
        lines[j:j] = new
        changed.append("sb_")
    text2 = "\n".join(lines)
    text2 = re.sub(r"^\*Generated: .*\*$",
                   f"*Prose written 2026-04-03. Part 2 keyword tables regenerated from the extractor by `scripts/build_extraction_rules_reference.py` "
                   f"on {time.strftime('%Y-%m-%d')} (commit {head}); re-run it after any edit to `scripts/extract_schema_columns.py`.*",
                   text2, count=1, flags=re.M)
    lo = min(v["line"] for d in R.values() for v in d.values() if v["line"])
    hi = max(v["line"] for d in R.values() for v in d.values() if v["line"])
    text2 = re.sub(r"^\*\*Source of truth for all keyword/threshold definitions:\*\* .*$",
                   lambda m: f"**Source of truth for all keyword/threshold definitions:** [`scripts/extract_schema_columns.py` lines {lo}–{hi}]({GH}#L{lo}-L{hi}) "
                   f"(the `BinaryColumn(...)` definitions; each row below links to its own line). Proximity-filtered columns: "
                   f"[`PROXIMITY_CHECK_COLUMNS`]({GH}#L{_line_of('PROXIMITY_CHECK_COLUMNS: frozenset')}); section weights: "
                   f"[`_SECTION_WEIGHTS`]({GH}#L{_line_of('_SECTION_WEIGHTS: dict')}). Machine-readable copy: "
                   f"[`extraction_rules.json`](./extraction_rules.json) (also `outputs/extraction_rules.json`).",
                   text2, count=1, flags=re.M)
    if text2 != text and not changed:
        changed.append("header")
    if not check:
        MD.write_text(text2)
    return changed


def _line_of(needle):
    for i, l in enumerate(SRC.read_text().splitlines(), 1):
        if l.startswith(needle):
            return i
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report staleness, write nothing, exit 1 if stale")
    args = ap.parse_args()
    R = rules()
    head = git_head()
    changed = update_md(R, head, check=args.check)
    if args.check:
        old = json.loads(JSON_OUT.read_text()) if JSON_OUT.exists() else {}
        same = all(old.get(p, {}).get(n, {}).get(k) == v for p, d in R.items() for n, r in d.items() for k, v in r.items() if k not in ("line", "url"))
        print(f"md sections stale: {changed or 'none'}; json stale: {not same}")
        sys.exit(1 if changed or not same else 0)
    doc = write_json(R, head)
    subprocess.run(["pandoc", "-s", "--metadata", "pagetitle=Extraction Logic Review Reference", "-f", "gfm", "-t", "html",
                    str(MD), "-o", str(HTML)], check=True)
    n = doc["_meta"]["n_rules"]
    print(f"{n} rules in {len(R)} schemas -> {JSON_OUT.relative_to(ROOT)}; md sections rewritten: {', '.join(changed) or 'none'}; "
          f"{HTML.relative_to(ROOT)} via pandoc; commit {head}")


if __name__ == "__main__":
    main()
