"""SHA-256 + TLSH over raw PDF bytes.

Single file read, two streaming hashers.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

try:
    import tlsh  # python-tlsh
    _TLSH_OK = True
except Exception:
    _TLSH_OK = False


_CHUNK = 1 << 20  # 1 MiB


def compute(pdf_path: Path) -> dict:
    sha = hashlib.sha256()
    tl = tlsh.Tlsh() if _TLSH_OK else None
    with open(pdf_path, "rb") as fh:
        while True:
            buf = fh.read(_CHUNK)
            if not buf:
                break
            sha.update(buf)
            if tl is not None:
                tl.update(buf)
    tlsh_hex: Optional[str] = None
    if tl is not None:
        try:
            tl.final()
            h = tl.hexdigest()
            tlsh_hex = h or None  # TLSH returns '' for files < ~50 bytes
        except Exception:
            tlsh_hex = None
    return {"bytes_sha256": sha.hexdigest(), "tlsh_hash": tlsh_hex}
