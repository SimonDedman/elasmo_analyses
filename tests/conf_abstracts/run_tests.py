#!/usr/bin/env python3
"""Minimal pytest-free test runner. Discovers test_* functions in the
tests/conf_abstracts/test_*.py modules and runs them, printing PASS/FAIL.

Usage: ./venv/bin/python tests/conf_abstracts/run_tests.py
"""
import importlib.util
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "scripts"))  # make `conf_abstracts` importable


def load_module(py: Path):
    spec = importlib.util.spec_from_file_location(py.stem, py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    files = sorted(HERE.glob("test_*.py"))
    passed = failed = 0
    for py in files:
        mod = load_module(py)
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            try:
                fn()
                passed += 1
                print(f"PASS {py.name}::{name}")
            except Exception as e:
                failed += 1
                print(f"FAIL {py.name}::{name}: {e}")
                traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
