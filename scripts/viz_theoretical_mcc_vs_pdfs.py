"""viz_theoretical_mcc_vs_pdfs.py

Reproduces outputs/figures/theoretical_mcc_vs_pdfs.png and updates the
"Current" marker to today's date and PDF count.

Note: the original generation script could not be located in the local
scripts/ tree or the elasmo_analyses GitHub repo, so this script reconstructs
the chart from the figure's anchor points (which encode a theoretical
diminishing-returns curve, not real validation data).

Anchor points (from the original chart):
    (    0, 0.00 )
    (15000, 0.78 )   "Early March"
    (16554, 0.85 )   "Current" (Mar 19, 2026)
    (18000, 0.90 )
    (25000, 0.95 )
    (30000, 0.99 )   "~30K SharkRefs max"
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, MultipleLocator

# ---------------------------------------------------------------------------
# Update these two values to refresh the chart.
# ---------------------------------------------------------------------------
TODAY      = date(2026, 5, 7)
CURRENT_N  = 18_292        # PDFs in master library (per 2026-05-05 instructions doc)
# Windows strftime doesn't support %-d, so build the date label manually:
TODAY_LBL  = f"{TODAY.day} {TODAY.strftime('%b')} {TODAY.year}"

# Output paths
BASE  = Path(r"C:/Users/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel")
FIGS  = BASE / "outputs" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
OUT_PNG = FIGS / "theoretical_mcc_vs_pdfs_may2026.png"
OUT_PDF = FIGS / "theoretical_mcc_vs_pdfs_may2026.pdf"

# ---------------------------------------------------------------------------
# Theoretical curve: anchor points + smooth interpolation through them.
# Keep "Early March" (mid-March 2026 snapshot at 16,554 PDFs) on the curve as
# historical context.
# ---------------------------------------------------------------------------
# Note: the original chart placed "Early March" at the 15,000 PDF / 78% MCC
# anchor and "Current" at the 16,554 / 85% anchor.
anchors_x = np.array([0,    15_000, 16_554, 18_000, 25_000, 30_000], dtype=float)
anchors_y = np.array([0.00, 0.78,   0.85,   0.90,   0.95,   0.99],   dtype=float)
EARLY_MARCH_X, EARLY_MARCH_Y = 15_000, 0.78
PREV_CURRENT_X, PREV_CURRENT_Y = 16_554, 0.85   # snapshot at Mar 19, 2026

# Linearly interpolate the segments at higher resolution so the line is smooth.
xs = np.linspace(0, 30_000, 1000)
ys = np.interp(xs, anchors_x, anchors_y)

# Where on the same curve does the new "Current" sit?
current_y = float(np.interp(CURRENT_N, anchors_x, anchors_y))

# ---------------------------------------------------------------------------
# Figure setup — match the original dimensions (12 x 8 in @ 300 dpi).
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#666666",
    "axes.linewidth": 0.8,
    "axes.labelcolor": "#333333",
    "xtick.color": "#555555",
    "ytick.color": "#555555",
    "grid.color": "#dddddd",
    "grid.linewidth": 0.6,
})

fig, ax = plt.subplots(figsize=(12, 8), dpi=300)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# Reference line: ~30K SharkRefs max
ax.axhline(1.0, color="#888888", linestyle=(0, (4, 3)), linewidth=0.9, zorder=1)
ax.text(450, 0.985, "~30K SharkRefs max",
        fontsize=10, color="#666666", va="bottom", zorder=2)

# Main curve
BLUE = "#1f6dbb"
ax.plot(xs, ys, color=BLUE, linewidth=2.4, zorder=3)

# Future-projection anchor markers
for x, y in [(18_000, 0.90), (25_000, 0.95), (30_000, 0.99)]:
    ax.plot([x], [y], marker="o", markersize=7, color=BLUE, zorder=4)

# Open circle = "Early March" (15,000 PDFs / 78% MCC)
ax.plot([EARLY_MARCH_X], [EARLY_MARCH_Y], marker="o", markersize=6,
        color="white", markeredgecolor=BLUE, markeredgewidth=1.6, zorder=4)
ax.annotate(
    "Early March:\n15,000 PDFs",
    xy=(EARLY_MARCH_X, EARLY_MARCH_Y),
    xytext=(EARLY_MARCH_X - 1100, EARLY_MARCH_Y - 0.005),
    fontsize=9, color=BLUE, ha="right", va="top", zorder=5,
)

# Mid-March snapshot (16,554 PDFs / 85% MCC) — small blue dot, no callout
ax.plot([PREV_CURRENT_X], [PREV_CURRENT_Y], marker="o", markersize=6,
        color="white", markeredgecolor=BLUE, markeredgewidth=1.6, zorder=4)
ax.annotate(
    "Mid March:\n16,554 PDFs",
    xy=(PREV_CURRENT_X, PREV_CURRENT_Y),
    xytext=(PREV_CURRENT_X + 350, PREV_CURRENT_Y - 0.04),
    fontsize=9, color=BLUE, ha="left", va="top", zorder=5,
)

# "Current" marker — today's PDF count
RED = "#c0392b"
ax.plot([CURRENT_N], [current_y], marker="o", markersize=11,
        color=RED, markeredgecolor="white", markeredgewidth=1.5, zorder=6)
ax.annotate(
    f"Current ({TODAY_LBL}):\n{CURRENT_N:,} PDFs",
    xy=(CURRENT_N, current_y),
    xytext=(CURRENT_N + 800, current_y - 0.04),
    fontsize=10.5, color=RED, ha="left", va="top", weight="bold",
    zorder=7,
)

# "Diminishing returns" italic note in the lower-right
ax.text(
    0.78, 0.25,
    "Diminishing returns:\neach additional PDF\nadds less accuracy",
    transform=ax.transAxes,
    fontsize=10, color="#777777", style="italic",
    ha="left", va="top",
)

# Axes formatting
ax.set_xlim(-500, 30_500)
ax.set_ylim(-0.02, 1.05)
ax.xaxis.set_major_locator(MultipleLocator(5_000))
ax.yaxis.set_major_locator(MultipleLocator(0.10))
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v * 100)}%"))
ax.set_xlabel("Number of PDFs Processed", fontsize=11, labelpad=8)
ax.set_ylabel("MCC Score", fontsize=11, labelpad=8)

# Grid: light, behind data
ax.grid(True, which="major", axis="both", color="#e6e6e6", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

# Title + subtitle (left-aligned, like original)
fig.text(0.06, 0.955, "Theoretical Validation Accuracy vs PDF Coverage",
         fontsize=15, weight="bold", color="#222222", ha="left")
fig.text(0.06, 0.928,
         "MCC (Matthews Correlation Coefficient) — diminishing returns with more PDFs",
         fontsize=11, color="#666666", ha="left")

plt.subplots_adjust(left=0.085, right=0.97, top=0.90, bottom=0.085)

fig.savefig(OUT_PNG, dpi=300, facecolor="white")
fig.savefig(OUT_PDF, facecolor="white")
print("Saved:", OUT_PNG)
print("Saved:", OUT_PDF)
print(f"Current point: ({CURRENT_N}, {current_y:.3f})  [{TODAY_LBL}]")
