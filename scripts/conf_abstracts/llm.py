"""Thin Ollama HTTP wrapper for structured field extraction / society inference.

User-local Ollama on 127.0.0.1:11435, model qwen2.5:3b-instruct. Stdlib only.
"""
import json
import urllib.request

from conf_abstracts.config import OLLAMA_HOST, OLLAMA_MODEL


def available(timeout=3) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_HOST + "/api/tags", timeout=timeout) as r:
            data = json.load(r)
        return any(m.get("name") == OLLAMA_MODEL for m in data.get("models", []))
    except Exception:
        return False


def ollama_json(prompt: str, timeout=120) -> dict:
    """Ask Ollama for a JSON object. Returns {} on any failure."""
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(OLLAMA_HOST + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.load(r)
        return json.loads(out.get("response", "{}"))
    except Exception:
        return {}


SOCIETY_PROMPT = """You are classifying a conference abstract from the Joint \
Meeting of Ichthyologists and Herpetologists (JMIH). Its constituent societies \
map to taxa:
- AES = American Elasmobranch Society: sharks, rays, skates, chimaeras (elasmobranchs/chondrichthyans)
- ASIH / NIA = bony fishes / ichthyology
- HL / SSAR = amphibians and reptiles (herpetology)

Given the title and abstract, output JSON: {{"society": "<AES|ASIH|HL|SSAR|NIA>", \
"is_elasmo": true|false, "confidence": 0.0-1.0}}. is_elasmo is true only if the \
work is about sharks/rays/skates/chimaeras.

TITLE: {title}
ABSTRACT: {abstract}
"""


def infer_society(title: str, abstract: str) -> dict:
    """Return {society, is_elasmo, confidence} or {} if LLM unavailable."""
    prompt = SOCIETY_PROMPT.format(title=title or "", abstract=(abstract or "")[:3000])
    out = ollama_json(prompt)
    if not out:
        return {}
    soc = str(out.get("society", "")).upper().strip() or None
    return dict(society=soc,
                is_elasmo=bool(out.get("is_elasmo")),
                confidence=float(out.get("confidence", 0.0) or 0.0))
