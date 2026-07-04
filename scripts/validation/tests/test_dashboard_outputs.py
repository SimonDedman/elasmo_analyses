"""Dashboard builders are only exercised end-to-end here, driven by a
synthetic fixture -- the real metrics.parquet / improvement_log.csv /
ab_viability.md are produced by the live Fable validation run (Tasks 1-6),
which has not executed yet. This test writes a small stand-in fixture
matching the schema score.py.run() actually emits (column, tp, fp, fn, tn,
precision, recall, f1, set; set in {silver_rules_vs_fable, gold_rules_vs_human}),
then runs make_dashboard.R and build_dashboard.py as subprocesses (the same
way the end-to-end run order does) and asserts the real artifacts exist and
are non-trivial in size.

NOTE: this deliberately overwrites outputs/validation/{metrics.parquet,
improvement_log.csv, ab_viability.md} if present. Those three files are
git-ignored build/pipeline artifacts (see .gitignore: outputs/* is ignored,
only outputs/validation/ and outputs/validation/*.csv are excepted -- so
metrics.parquet, ab_viability.md and the figures/dashboard.html stay
ignored). They do not exist yet in this repo; when the live pipeline
produces real ones later, a subsequent test run will cleanly overwrite this
synthetic fixture with the real thing.
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/validation"


def _write_synthetic_fixture():
    OUT.mkdir(parents=True, exist_ok=True)

    metrics = pd.DataFrame(
        [
            # worst-first candidates mixed in on purpose -- the R script
            # must do its own precision/recall-based ordering, not rely on
            # input order.
            {"column": "d_taxonomy", "tp": 2, "fp": 8, "fn": 6, "tn": 84,
             "precision": 0.20, "recall": 0.25, "f1": 0.222, "set": "silver_rules_vs_fable"},
            {"column": "eco_pelagic", "tp": 18, "fp": 2, "fn": 3, "tn": 77,
             "precision": 0.90, "recall": 0.857, "f1": 0.878, "set": "silver_rules_vs_fable"},
            {"column": "pr_bycatch", "tp": 10, "fp": 5, "fn": 5, "tn": 80,
             "precision": 0.667, "recall": 0.667, "f1": 0.667, "set": "silver_rules_vs_fable"},
            {"column": "gear_longline", "tp": 0, "fp": 0, "fn": 4, "tn": 96,
             "precision": float("nan"), "recall": 0.0, "f1": float("nan"), "set": "silver_rules_vs_fable"},
            # a gold row too, to confirm the R filter to silver_rules_vs_fable
            # actually excludes it (if it leaked in, the figure would show
            # a 5th/duplicated column).
            {"column": "d_taxonomy", "tp": 3, "fp": 4, "fn": 3, "tn": 90,
             "precision": 0.429, "recall": 0.50, "f1": 0.462, "set": "gold_rules_vs_human"},
        ]
    )
    metrics.to_parquet(OUT / "metrics.parquet")

    improvement_log = pd.DataFrame(
        [
            {"column": "d_taxonomy", "change_type": "add_terms",
             "silver_f1_before": 0.222, "silver_f1_after": 0.410,
             "gold_f1_after": 0.380, "accepted": True},
            {"column": "gear_longline", "change_type": "threshold",
             "silver_f1_before": 0.0, "silver_f1_after": 0.333,
             "gold_f1_after": 0.300, "accepted": True},
            {"column": "pr_bycatch", "change_type": "add_terms",
             "silver_f1_before": 0.667, "silver_f1_after": 0.667,
             "gold_f1_after": 0.650, "accepted": False},
        ]
    )
    improvement_log.to_csv(OUT / "improvement_log.csv", index=False)

    (OUT / "ab_viability.md").write_text(
        "# LLM extraction A/B viability\n\n"
        "- Papers Fable-labelled: 4 (synthetic fixture)\n"
        "- Mean tokens/paper: 1200 in / 150 out\n"
        "- Fable-vs-human agreement (gold, macro-F1): 0.712\n"
        "- Rules-vs-human (gold, macro-F1): 0.462\n"
        "- Rules-vs-Fable (silver, macro-F1): 0.560\n"
        "- **Extrapolated Fable cost for 40,000 PDFs: $250** "
        "(synthetic placeholder; real number comes from score.py).\n"
    )


def test_dashboard_artifacts_exist_and_nonempty():
    _write_synthetic_fixture()

    r = subprocess.run(
        ["Rscript", str(ROOT / "scripts/validation/make_dashboard.R")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, f"make_dashboard.R failed:\nstdout={r.stdout}\nstderr={r.stderr}"

    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validation/build_dashboard.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert p.returncode == 0, f"build_dashboard.py failed:\nstdout={p.stdout}\nstderr={p.stderr}"

    for f in ["figures/per_column_pr.png", "figures/improvement.png", "dashboard.html"]:
        fp = OUT / f
        assert fp.exists() and fp.stat().st_size > 1000, f"missing/empty: {f}"
