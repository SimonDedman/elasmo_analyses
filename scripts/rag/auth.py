"""Auth seam (spec component 6): RAG_AUTH_MODE in {open (default), token}.

Token mode reads tokens from RAG_AUTH_TOKENS ("name:secret,name:secret") and
from <RAG_OUT_DIR>/auth_tokens.json ({"name": "secret"}; outputs/ is
git-ignored). Accepts "Authorization: Bearer <secret>" or X-SharkOracle-Token.
Mode and tokens are read per request so changes take effect without restart
of the env-var path; the json file is re-read on each request too.
"""

from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path

from fastapi import HTTPException, Request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402


def auth_mode() -> str:
    return (os.environ.get("RAG_AUTH_MODE") or "open").strip().lower()


def load_tokens() -> dict[str, str]:
    """name -> secret."""
    tokens: dict[str, str] = {}
    f = common.RAG_STATE_DIR / "auth_tokens.json"
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            tokens.update({str(k): str(v) for k, v in data.items()})
        except (OSError, ValueError, AttributeError):
            pass
    for part in (os.environ.get("RAG_AUTH_TOKENS") or "").split(","):
        name, sep, secret = part.strip().partition(":")
        if sep and name and secret:
            tokens[name] = secret
    return tokens


def _presented(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    if h.lower().startswith("bearer "):
        return h[7:].strip() or None
    return (request.headers.get("x-sharkoracle-token") or "").strip() or None


def require_access(request: Request) -> str:
    """Return the client name ('anonymous' in open mode) or raise 401."""
    mode = auth_mode()
    if mode == "open":
        return "anonymous"
    if mode != "token":
        raise HTTPException(status_code=500, detail=f"unknown RAG_AUTH_MODE {mode!r}")
    secret = _presented(request)
    if secret:
        for name, tok in load_tokens().items():
            if hmac.compare_digest(secret.encode(), tok.encode()):
                return name
    raise HTTPException(status_code=401, detail="valid access token required",
                        headers={"WWW-Authenticate": "Bearer"})
