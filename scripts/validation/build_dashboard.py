"""Assemble a self-contained HTML dashboard (inline base64 PNGs + the A/B
viability memo) from the figures produced by make_dashboard.R.

Inputs (outputs/validation/):
    figures/per_column_pr.png
    figures/improvement.png
    ab_viability.md (optional -- omitted section text if missing)

Output:
    outputs/validation/dashboard.html
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/validation"


def _img(name):
    p = OUT / "figures" / name
    b = base64.b64encode(p.read_bytes()).decode()
    return f'<img style="max-width:100%" src="data:image/png;base64,{b}">'


def main():
    memo = (OUT / "ab_viability.md").read_text() if (OUT / "ab_viability.md").exists() else ""
    html = f"""<!doctype html><meta charset=utf-8><title>Extraction validation</title>
<style>body{{font-family:system-ui;margin:2rem;max-width:1000px}}pre{{background:#f4f4f4;padding:1rem;white-space:pre-wrap}}</style>
<h1>Extraction validation dashboard</h1>
<h2>Per-column precision &amp; recall</h2>{_img('per_column_pr.png')}
<h2>Rule improvement (before &rarr; after)</h2>{_img('improvement.png')}
<h2>LLM extraction A/B viability</h2><pre>{memo}</pre>"""
    (OUT / "dashboard.html").write_text(html)
    print("wrote dashboard.html")


if __name__ == "__main__":
    main()
