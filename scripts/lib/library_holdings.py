#!/usr/bin/env python3
"""
library_holdings.py — per-institution "does the library hold journal ISSN Y?" recipe.

Built 2026-09-17 for the F2 institution-access track of the download push
(outputs/download_push_2026-09-17/F2_institution_access/). Read
outputs/download_push_2026-09-17/F2_institution_access/recipes.md for the
full writeup of how each surface was found, and coverage.json for which
institutions are actually queryable automatically vs blocked/login-only.

Every institution exposes a `holdings(issn, year=None)` function returning:
    {"held": True|False|None, "coverage": str, "source": url, "note": str}
held=None means "could not determine" (blocked, no public surface found,
or ambiguous), never a guessed False. NEVER conflate "blocked" with "not held".

Public discovery / link-resolver surfaces are used, no credentials. Where a
host blocked us (IP-restricted API, anti-bot challenge, JS SPA with no
discoverable plain API) we say so explicitly rather than guessing at
undocumented endpoints (see ~/.claude/WEB-LOOKUPS.md).

Rate limit: one institution's registry function makes at most a couple of
HTTP requests per call. Callers doing a bulk run MUST sleep >=2s between
calls to the SAME host. This module does not do its own global throttling
across repeated CLI invocations -- a batch runner must add the delay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

USER_AGENT = "elasmo_analyses/1.0 (mailto:simondedman@gmail.com)"
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE_DIR = os.path.join(
    PROJECT_ROOT,
    "outputs",
    "download_push_2026-09-17",
    "F2_institution_access",
    ".cache",
)
os.makedirs(CACHE_DIR, exist_ok=True)


def _norm_issn(issn: str) -> str:
    return re.sub(r"[^0-9Xx]", "", issn or "").upper()


def _cache_path(key: str) -> str:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return os.path.join(CACHE_DIR, f"{h}.json")


def _http_get(url: str, headers: dict | None = None, timeout: int = 20) -> tuple[int, bytes]:
    """GET with an honest UA. Caches ONLY 200 responses (WEB-LOOKUPS rule 3).
    Never raises on HTTP error status; returns (status, body) so callers can
    tell a block (403/404/timeout) apart from a genuine empty result."""
    cache_file = _cache_path(url)
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as fh:
            cached = json.load(fh)
        return 200, cached["body"].encode("utf-8")

    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    try:
        # verify=False equivalent: this sandbox's CA bundle does not chain
        # to several university hosts' certs (curl -k also required, see
        # recipes.md); we still only ever GET public, unauthenticated pages.
        import ssl

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = resp.getcode()
            body = resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b""
    except Exception as e:  # noqa: BLE001 - network errors of many types
        return -1, str(e).encode("utf-8")

    if status == 200:
        try:
            with open(cache_file, "w", encoding="utf-8") as fh:
                json.dump({"url": url, "body": body.decode("utf-8", "replace")}, fh)
        except Exception:
            pass
    return status, body


def _primo_ve_journal_holding(host: str, vid: str, inst: str, issn: str) -> dict:
    """Shared recipe for any Primo VE (New UI) instance: query the public
    primaws pnxs API with scope=MyInstitution, filtered to journal-level
    records, for an exact ISSN match (dashes stripped -- Primo indexes
    ISSNs without the hyphen). No login required; this is the same request
    the browser-based discovery UI makes.

    Coverage years are NOT resolved by this call (Primo's compact response
    omits per-holding date ranges from the aggregated journal record; a
    per-record detail call would be needed and was out of scope for the
    time-boxed trial -- see recipes.md). held=True only tells you the
    institution's OWN catalog has an electronic or print record for that
    ISSN, not which years are covered.
    """
    issn_n = _norm_issn(issn)
    url = (
        f"https://{host}/primaws/rest/pub/pnxs?"
        "blendFacetsSeparately=false&disableCache=false&getMore=0"
        f"&inst={inst}&lang=en&limit=5&mode=advanced&newspapersActive=false"
        "&newspapersSearch=false&offset=0&pcAvailability=false"
        f"&q=issn,exact,{issn_n}&qExclude=&qInclude=facet_rtype,exact,journals"
        "&rapido=false&refEntryActive=false&rtaLinks=true&scope=MyInstitution"
        f"&skipDelivery=Y&sort=rank&tab=Everything&vid={vid}"
    )
    status, body = _http_get(url)
    if status != 200:
        return {
            "held": None,
            "coverage": "",
            "source": url,
            "note": f"HTTP {status} — blocked or unreachable, not a negative result",
        }
    try:
        data = json.loads(body)
    except Exception:
        return {"held": None, "coverage": "", "source": url, "note": "unparseable response"}
    total = data.get("info", {}).get("total", 0)
    if total and total > 0:
        titles = []
        for doc in data.get("docs", [])[:3]:
            t = doc.get("pnx", {}).get("display", {}).get("title")
            if t:
                titles.append(t[0])
        return {
            "held": True,
            "coverage": "held locally (Alma record found); year coverage not resolved by this API call",
            "source": url,
            "note": "; ".join(titles),
        }
    return {"held": False, "coverage": "", "source": url, "note": "0 journal-level records for this ISSN in MyInstitution scope"}


# ---------------------------------------------------------------------------
# Institution registry
# ---------------------------------------------------------------------------


def holdings_fiu(issn: str, year: str | None = None) -> dict:
    """FIU Libraries — Primo VE ("OneSearch"), FALSC (Florida Academic
    Library Services Cooperative) shared instance.
    Host: fiu-flvc.primo.exlibrisgroup.com, vid=01FALSC_FIU:FIU.
    Works without login."""
    return _primo_ve_journal_holding(
        "fiu-flvc.primo.exlibrisgroup.com", "01FALSC_FIU:FIU", "01FALSC_FIU", issn
    )


def holdings_osu(issn: str, year: str | None = None) -> dict:
    """Oregon State University — Primo VE via the Orbis Cascade Alliance
    shared Alma/Primo instance ("1Search").
    Host: search.library.oregonstate.edu, vid=01ALLIANCE_OSU:OSU.
    Works without login."""
    return _primo_ve_journal_holding(
        "search.library.oregonstate.edu", "01ALLIANCE_OSU:OSU", "01ALLIANCE_OSU", issn
    )


def holdings_ucdavis(issn: str, year: str | None = None) -> dict:
    """UC Davis — Primo VE ("UC Library Search", UCD-specific instance).
    Host: search.library.ucdavis.edu, vid=01UCD_INST:UCD.
    Works without login."""
    return _primo_ve_journal_holding(
        "search.library.ucdavis.edu", "01UCD_INST:UCD", "01UCD_INST", issn
    )


def holdings_uv(issn: str, year: str | None = None) -> dict:
    """Universitat de València — Primo VE ("Trobes").
    Host: trobes.uv.es, vid=34CVA_UV:VU1.
    Works without login."""
    return _primo_ve_journal_holding("trobes.uv.es", "34CVA_UV:VU1", "34CVA_UV", issn)


def holdings_asu(issn: str, year: str | None = None) -> dict:
    """Arizona State University (David Shiffman — unconfirmed team member,
    not in the original DO list, checked opportunistically because it's the
    same zero-cost Primo VE recipe as FIU/OSU/UCD/UV).
    Host: search.lib.asu.edu, vid=01ASU_INST:01ASU.
    Works without login."""
    return _primo_ve_journal_holding(
        "search.lib.asu.edu", "01ASU_INST:01ASU", "01ASU_INST", issn
    )


def holdings_csic(issn: str, year: str | None = None) -> dict:
    """CSIC (covers ICM-CSIC/Elena and IEO-CSIC/Lola) — old-style Primo
    Classic ("primo-explore" Angular UI) at
    csic-primo.hosted.exlibrisgroup.com, vid=34CSIC_VU1.

    BLOCKED for this trial: the legacy PrimoWebServices X-Server API
    (/PrimoWebServices/xservice/search/brief) returned
    HTTP 403 "IP address rejected" — an IP allowlist, not a login wall and
    not evidence of absence. The primaws/rest/pub/pnxs endpoint FIU/OSU/UCD/
    UV use returned 404 on this host (older Primo backend, doesn't expose
    it). The human-facing search UI at
    https://csic-primo.hosted.exlibrisgroup.com/primo-explore/search?vid=34CSIC_VU1
    works fine in a real browser without login — it just cannot be queried
    headlessly from here. See recipes.md."""
    return {
        "held": None,
        "coverage": "",
        "source": "https://csic-primo.hosted.exlibrisgroup.com/primo-explore/search?vid=34CSIC_VU1",
        "note": "BLOCKED: X-Server API IP-rejected (403); primaws API 404s on this legacy Primo backend. "
        "Public browser UI works without login — needs browser automation or a manual check by Elena/Lola.",
    }


def holdings_sfu(issn: str, year: str | None = None) -> dict:
    """Simon Fraser University Library.

    BLOCKED at the network layer for this trial: lib.sfu.ca is fronted by
    an Anubis anti-bot proof-of-work challenge (returns a JS PoW page, not
    the library homepage, to any non-browser client). Solving the PoW
    challenge to get past it would cross from "reading a public page" into
    bypassing anti-bot protection, which this task's rules forbid. The
    underlying discovery system (Primo/Summon) was never reached, so it is
    UNKNOWN, not absent. Needs Nick Dulvy/Emily Warren/Chris Mull to paste
    the library's actual search URL, or a real-browser check."""
    return {
        "held": None,
        "coverage": "",
        "source": "https://www.lib.sfu.ca",
        "note": "BLOCKED: Anubis anti-bot proof-of-work challenge on lib.sfu.ca; did not attempt to solve it "
        "(would cross into anti-bot bypass). Discovery system behind it unidentified.",
    }


def holdings_mcgill(issn: str, year: str | None = None) -> dict:
    """McGill University Library — WorldCat Discovery (OCLC), with a public
    "atoztitles" journal-holdings widget referenced from mcgill.on.worldcat.org.

    PARTIAL: the atoztitles page is a Cloudflare-fronted React SPA
    (mcgill.on.worldcat.org/atoztitles/search#journal) with no plain-HTTP
    JSON endpoint discovered within the time budget — every path guessed
    (atoztitles/api/entries, /api/search, /lhr/api/atoztitles) either 403'd
    or returned the SPA shell, not data. Guessing further undocumented
    endpoints was stopped per the "do not guess blindly" instruction.
    Needs a real-browser check or David Green to paste a saved A-Z search
    URL."""
    return {
        "held": None,
        "coverage": "",
        "source": "https://mcgill.on.worldcat.org/atoztitles/search#journal",
        "note": "PARTIAL: public UI identified (WorldCat Discovery A-Z titles) but it's a Cloudflare-fronted "
        "SPA with no discoverable plain JSON API in the time available. Needs browser automation.",
    }


def holdings_univpm(issn: str, year: str | None = None) -> dict:
    """Università Politecnica delle Marche (Chiara) — library discovery
    surface NOT located within the time budget: biblioteca.univpm.it did
    not resolve/connect, and www.univpm.it/Entra/Biblioteche 404'd. Needs
    Chiara to paste the SBA (Sistema Bibliotecario di Ateneo) search URL or
    A-Z list link directly."""
    return {
        "held": None,
        "coverage": "",
        "source": "",
        "note": "NOT FOUND: no reachable library discovery page located for UNIVPM in the time budget "
        "(DNS/connection failures). Needs Chiara to supply the SBA UNIVPM search/A-Z URL.",
    }


def holdings_kaust(issn: str, year: str | None = None) -> dict:
    """KAUST (Andrew Temple) — library.kaust.edu.sa publishes a LibGuides
    "A-Z Databases" list (library.kaust.edu.sa/az.php, loads without login)
    and references a "1Search" discovery tool, but the 1Search pages found
    were LibGuides help pages about the tool, not the live search endpoint
    itself (no exlibrisgroup.com / API host found in the page source within
    the time budget). PARTIAL: package-membership proxy (A-Z Databases
    list) works; ISSN-level holdings lookup does not yet."""
    return {
        "held": None,
        "coverage": "",
        "source": "https://library.kaust.edu.sa/az.php",
        "note": "PARTIAL: public A-Z Databases list (package-level proxy) works without login; the live "
        "'1Search' discovery search endpoint itself was not located in the time budget.",
    }


def holdings_bfr(issn: str, year: str | None = None) -> dict:
    """BfR Berlin (Ulrich) — Germany's national journal-holdings aggregator
    EZB (Elektronische Zeitschriftenbibliothek, ezb.ur.de) is the right
    class of tool (public, no login, per-library green/yellow/red coverage
    by ISSN) but BfR's EZB library code ("bibid") was not identified within
    the time budget — the institution search page returned no obvious
    bibid in its HTML and this needs interactive browsing of
    https://ezb.ur.de's library-selector UI, or Ulrich supplying BfR's
    EZB bibid directly."""
    return {
        "held": None,
        "coverage": "",
        "source": "https://ezb.ur.de/",
        "note": "PARTIAL: right tool identified (EZB, public ISSN-level German union holdings list) but "
        "BfR's EZB library code (bibid) not resolved in time. Needs Ulrich's bibid or interactive lookup.",
    }


def holdings_niwa(issn: str, year: str | None = None) -> dict:
    """NIWA (Brit Finucci) — no public academic-library discovery layer
    found: niwa.co.nz is a research-institute site, not a university
    library with a public catalog/resolver. NIWA staff most likely reach
    subscribed content via a much smaller internal system or personal
    institutional logins with no public-facing equivalent. Needs Brit to
    say what she actually uses (or this stays "ask member" permanently)."""
    return {
        "held": None,
        "coverage": "",
        "source": "https://niwa.co.nz",
        "note": "NO PUBLIC SURFACE: NIWA is a crown research institute, not a university with a public "
        "library discovery system. Route via 'ask member' (Brit) rather than automation.",
    }


REGISTRY = {
    "fiu": holdings_fiu,
    "osu": holdings_osu,
    "ucdavis": holdings_ucdavis,
    "uv": holdings_uv,
    "asu": holdings_asu,
    "csic": holdings_csic,
    "sfu": holdings_sfu,
    "mcgill": holdings_mcgill,
    "univpm": holdings_univpm,
    "kaust": holdings_kaust,
    "bfr": holdings_bfr,
    "niwa": holdings_niwa,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--institution", required=True, choices=sorted(REGISTRY.keys()))
    ap.add_argument("--issn", required=True)
    ap.add_argument("--year", default=None)
    args = ap.parse_args()

    fn = REGISTRY[args.institution]
    result = fn(args.issn, args.year)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
