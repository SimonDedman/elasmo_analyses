"""Text-quality gate + on-demand re-OCR for programme PDFs.

Mirrors the carylanne_ocr.sh approach: whole-doc pdftotext quality, and where
it's poor, force-OCR in place (English, pixel-bomb guard off, temp on the
AppArmor-permitted /media scratch, original backed up first).
"""
import re
import shutil
import subprocess
from pathlib import Path

from conf_abstracts.config import ALPHA_MIN, DENSITY_MIN, OCR_SCRATCH

_WORD = re.compile(r"[A-Za-zÀ-ÿ]{3,}")


def extract_text(pdf, timeout=300) -> str:
    try:
        return subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True,
                              timeout=timeout).stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def _classify(alpha: int, density: float) -> str:
    if alpha < ALPHA_MIN:
        return "no_text"
    if density < DENSITY_MIN:
        return "low_quality"
    return "ok"


def text_quality(pdf) -> dict:
    t = extract_text(pdf)
    alpha = sum(c.isalpha() for c in t)
    words = len(_WORD.findall(t))
    toks = max(len(t.split()), 1)
    density = round(words / toks, 3)
    return dict(alpha=alpha, words=words, density=density,
                status=_classify(alpha, density))


def ensure_ocr(pdf, scratch: Path = OCR_SCRATCH, backup_dir: Path = None,
               timeout=21600) -> dict:
    """Re-OCR the PDF in place if its text quality is poor. Returns a dict with
    before/after status and whether it was re-OCR'd."""
    pdf = Path(pdf)
    before = text_quality(pdf)
    if before["status"] == "ok":
        return dict(reocr=False, before=before, after=before)

    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    if backup_dir is None:
        backup_dir = scratch / "conf_abstracts_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    bk = backup_dir / pdf.name
    if not bk.exists():
        shutil.copy2(pdf, bk)

    tmp = pdf.with_suffix(".ocr.tmp.pdf")
    if tmp.exists():
        tmp.unlink()
    env = {"TMPDIR": str(scratch), "TMP": str(scratch), "TEMP": str(scratch)}
    import os
    runenv = {**os.environ, **env}
    rc = subprocess.run(
        ["ocrmypdf", "--force-ocr", "--output-type", "pdf", "--language", "eng",
         "--max-image-mpixels", "0", "--optimize", "0", "--jobs", "6",
         str(pdf), str(tmp)],
        capture_output=True, timeout=timeout, env=runenv).returncode
    if rc == 0 and tmp.exists() and tmp.stat().st_size > 0:
        tmp.replace(pdf)
        after = text_quality(pdf)
        return dict(reocr=True, ok=True, before=before, after=after, backup=str(bk))
    if tmp.exists():
        tmp.unlink()
    return dict(reocr=True, ok=False, before=before, after=before, rc=rc)
