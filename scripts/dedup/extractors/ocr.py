"""OCR fallback for scanned PDFs via ocrmypdf subprocess."""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
from typing import Optional

import fitz


def run_ocr(pdf_path: pathlib.Path, timeout_sec: int = 300) -> Optional[str]:
    """Run OCR on a PDF via ocrmypdf, return extracted text or None.

    Uses --skip-text so pages that already have text are left alone
    (we only OCR pages that are scan-only). Returns None on any failure
    (timeout, ocrmypdf not installed, unreadable PDF).
    """
    if shutil.which("ocrmypdf") is None:
        return None

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            proc = subprocess.run(
                [
                    "ocrmypdf",
                    "--skip-text",
                    "--output-type=pdf",
                    "--quiet",
                    str(pdf_path),
                    tmp_path,
                ],
                timeout=timeout_sec,
                capture_output=True,
            )
        except subprocess.TimeoutExpired:
            return None

        if proc.returncode != 0:
            return None

        try:
            doc = fitz.open(tmp_path)
        except Exception:
            return None
        try:
            parts = []
            for i in range(doc.page_count):
                try:
                    parts.append(doc.load_page(i).get_text("text"))
                except Exception:
                    parts.append("")
            return "\n\f\n".join(parts)
        finally:
            try:
                doc.close()
            except Exception:
                pass
    except Exception:
        return None
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
