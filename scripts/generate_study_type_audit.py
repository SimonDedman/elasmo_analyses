#!/usr/bin/env python3
"""Build outputs/study_type_audit.html — DataTables review of the classifier.

Covers only papers with an extractable PDF (broad-scope rule). Columns:
  lit_id · year · publisher · journal · study_type · signal · matched
  · title (linked to paper PDF / DOI).

Default filter: study_type != empirical
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
PARQUET = PROJECT / "outputs" / "literature_review_enriched.parquet"
QUEUE_JSON = PROJECT / "docs" / "papers_data.json"
BY_PUBLISHER = PROJECT / "outputs" / "by_publisher"
OUTPUT_DATA = PROJECT / "docs" / "study_type_audit_data.json"
OUTPUT_HTML = PROJECT / "docs" / "study_type_audit.html"


def load_publisher_map() -> dict[str, str]:
    """Build journal -> publisher mapping from available sources."""
    mapping: dict[str, str] = {}
    if QUEUE_JSON.exists():
        for entry in json.loads(QUEUE_JSON.read_text()):
            j = (entry.get("journal") or "").strip()
            pub = (entry.get("publisher") or "").strip()
            if j and pub and j not in mapping:
                mapping[j] = pub
    if BY_PUBLISHER.exists():
        for csv_path in sorted(BY_PUBLISHER.glob("*.csv")):
            df = pd.read_csv(csv_path, usecols=["journal", "publisher"])
            for j, pub in zip(df["journal"].fillna(""), df["publisher"].fillna("")):
                j, pub = str(j).strip(), str(pub).strip()
                if j and pub and j not in mapping:
                    mapping[j] = pub
    return mapping


def main() -> None:
    print("Loading parquet…")
    df = pd.read_parquet(
        PARQUET,
        columns=[
            "literature_id", "year", "title", "authors", "journal", "doi",
            "study_type", "study_type_signal", "study_type_evidence",
        ],
    )
    df["literature_id"] = df["literature_id"].astype(str)
    df = df.drop_duplicates(subset="literature_id", keep="first")

    # Keep only PDF'd papers (signal != no_pdf)
    before = len(df)
    df = df[df["study_type_signal"].fillna("") != "no_pdf"]
    print(f"  {len(df):,} PDF'd papers (dropped {before - len(df):,} no-PDF rows)")

    # Publisher lookup
    pub_map = load_publisher_map()
    df["publisher"] = (
        df["journal"].fillna("").astype(str).map(pub_map).fillna("unknown")
    )

    # Clean up types for JSON
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.rename(columns={
        "study_type": "type",
        "study_type_signal": "signal",
        "study_type_evidence": "matched",
    })
    records = df[[
        "literature_id", "year", "publisher", "journal",
        "type", "signal", "matched", "title", "doi",
    ]].fillna("").astype(str).to_dict(orient="records")
    # Coerce year back to int strings
    for r in records:
        if r["year"].endswith(".0"):
            r["year"] = r["year"][:-2]
        # Truncate matched snippet for table cell
        r["matched"] = r["matched"][:80]

    OUTPUT_DATA.write_text(json.dumps(records, indent=1, ensure_ascii=False))
    print(f"  wrote {OUTPUT_DATA.relative_to(PROJECT)} ({len(records):,} rows)")

    # Summary counts
    summary = df.groupby(["signal", "type"]).size().unstack(fill_value=0)
    print("\nSignal × type:")
    print(summary)

    # ---- HTML shell (DataTables, matches remaining_downloads.html style) ----
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>Study-type classifier audit</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css">
<link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.2/css/buttons.dataTables.min.css">
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 12px; color: #2c3e50; }}
h1 {{ margin: 0 0 4px 0; font-size: 1.4rem; }}
.subtitle {{ color:#7f8c8d; font-size:0.8rem; margin-bottom:10px; }}
.stats {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; }}
.stat-box {{ background:#ecf0f1; padding:6px 12px; border-radius:4px; text-align:center; }}
.stat-number {{ font-size:18px; font-weight:bold; color:#2c3e50; }}
.stat-label {{ font-size:10px; color:#7f8c8d; text-transform:uppercase; }}
table.dataTable {{ font-size:0.85rem; }}
td.signal-banner {{ background:#d6f5d6; }}
td.signal-title_kw {{ background:#fff4cc; }}
td.signal-default_empirical {{ background:#f5f5f5; color:#999; }}
.type-pill {{ display:inline-block; padding:1px 7px; border-radius:10px; font-size:0.75rem; font-weight:bold; color:#fff; }}
.type-review {{ background:#8e44ad; }}
.type-letter {{ background:#2980b9; }}
.type-corrigendum {{ background:#e67e22; }}
.type-synthesis {{ background:#16a085; }}
.type-conceptual {{ background:#d35400; }}
.type-empirical {{ background:#95a5a6; }}
.updated {{ color:#999; font-size:0.75rem; margin-top:8px; }}
</style>
</head><body>
<h1>Study-type classifier audit</h1>
<p class="subtitle">Papers with a PDF (no-PDF papers excluded). Default filter: <code>type != empirical</code>. Clear the type search box to see all rows.</p>
<div class="stats">
  <div class="stat-box"><div class="stat-number" id="stat-total">…</div><div class="stat-label">PDF'd papers</div></div>
  <div class="stat-box"><div class="stat-number" id="stat-banner">…</div><div class="stat-label">Banner signal</div></div>
  <div class="stat-box"><div class="stat-number" id="stat-title">…</div><div class="stat-label">Title fallback</div></div>
  <div class="stat-box"><div class="stat-number" id="stat-default">…</div><div class="stat-label">Default empirical</div></div>
  <div class="stat-box"><div class="stat-number" id="stat-nonemp">…</div><div class="stat-label">Non-empirical</div></div>
</div>
<table id="tbl" class="display compact" style="width:100%">
  <thead><tr>
    <th>LID</th><th>Year</th><th>Publisher</th><th>Journal</th>
    <th>Type</th><th>Signal</th><th>Matched</th><th>Title</th>
  </tr></thead>
</table>
<p class="updated">Updated: {pd.Timestamp.today():%Y-%m-%d} · <a href="https://github.com/SimonDedman/elasmo_analyses/blob/main/docs/schema_proposals/study_type_proposal.md">classifier rules</a></p>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js"></script>
<script>
$.getJSON('study_type_audit_data.json', function(data) {{
  // Summary stats
  var total = data.length;
  var bannerN = data.filter(r => r.signal === 'banner').length;
  var titleN  = data.filter(r => r.signal === 'title_kw').length;
  var defaultN = data.filter(r => r.signal === 'default_empirical').length;
  var nonemp  = data.filter(r => r.type !== 'empirical').length;
  $('#stat-total').text(total.toLocaleString());
  $('#stat-banner').text(bannerN.toLocaleString());
  $('#stat-title').text(titleN.toLocaleString());
  $('#stat-default').text(defaultN.toLocaleString());
  $('#stat-nonemp').text(nonemp.toLocaleString());

  function escapeHtml(s) {{ return String(s||'').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}}[c])); }}

  var rows = data.map(r => [
    escapeHtml(r.literature_id),
    escapeHtml(r.year),
    escapeHtml(r.publisher),
    escapeHtml(r.journal),
    '<span class="type-pill type-' + escapeHtml(r.type) + '">' + escapeHtml(r.type) + '</span>',
    '<span class="signal-' + escapeHtml(r.signal) + '">' + escapeHtml(r.signal) + '</span>',
    escapeHtml(r.matched),
    r.doi
      ? '<a href="https://doi.org/' + encodeURIComponent(r.doi) + '" target="_blank">' + escapeHtml(r.title) + '</a>'
      : escapeHtml(r.title),
  ]);

  $('#tbl').DataTable({{
    data: rows,
    pageLength: 50,
    order: [[4, 'asc'], [1, 'desc']],
    search: {{ search: 'review|letter|corrigendum|synthesis|conceptual', regex: true, smart: false }},
    columnDefs: [
      {{ targets: 5, createdCell: function(td, cellData, rowData) {{
        // Apply a signal class to colour the signal cell
        var m = (cellData||'').match(/signal-(\\w+)/);
        if (m) {{ td.className += ' signal-' + m[1]; }}
      }}}},
    ],
  }});
}});
</script>
</body></html>
"""
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  wrote {OUTPUT_HTML.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
