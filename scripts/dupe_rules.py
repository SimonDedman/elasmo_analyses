#!/usr/bin/env python3
"""Duplicate detection rules (v7). Shared by review_duplicates and feedback_loop."""
import subprocess, re
from pathlib import Path

def is_corrupted(pdf_path):
    try:
        info = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True, timeout=10)
        if info.returncode != 0: return True
        pm = re.search(r"Pages:\s+(\d+)", info.stdout)
        if not pm: return True
        if int(pm.group(1)) == 0: return True
        import pikepdf
        try:
            with pikepdf.open(pdf_path) as pdf:
                _ = len(pdf.pages)
            return False
        except: return True
    except: return True

def get_info(p):
    try:
        r = subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True, timeout=30)
        full = r.stdout; pages = full.split("\f")
        info = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, timeout=10)
        m = re.search(r"Pages:\s+(\d+)", info.stdout)
        pc = int(m.group(1)) if m else len(pages)
        return pages, pc, len(full.split()), full.lower(), full
    except: return [], 0, 0, "", ""

def extract_title(pages):
    if not pages: return ""
    text = pages[0][:1500]
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3]
    skip = [r"^(?:vol\.?|volume|issue|no\.|\d{4})\s", r"^(?:received|accepted|published|doi:?)",
            r"journal\s+of|proceedings|bulletin|annals|copyright|©",
            r"https?:|doi\.org|www\.", r"nii.*electronic|library\s+service",
            r"^[\d\s\-:/,.]+$", r"^\d+\s*$", r"^page\s+\d+\s+of\s+\d+"]
    parts = []
    for line in lines[:20]:
        if re.match(r"^\d+\s*$", line): continue
        if len(line) < 40 and line == line.upper() and not re.search(r"[A-Z][a-z]", line): continue
        if any(re.search(p, line.lower()) for p in skip):
            if parts: break
            continue
        if re.search(r"[A-Za-z]", line) and len(line) > 10:
            parts.append(line)
            if len(" ".join(parts)) > 80: break
    return " ".join(parts).strip()

def tsim(t1, t2):
    w1 = set(re.findall(r"[a-z]{4,}", t1.lower()))
    w2 = set(re.findall(r"[a-z]{4,}", t2.lower()))
    if not w1 or not w2: return 0
    stops = {"the","and","for","with","from","that","this","study","new"}
    w1 -= stops; w2 -= stops
    if not w1 or not w2: return 0
    return len(w1 & w2) / max(len(w1), len(w2))

def is_cr(pages):
    if not pages: return False
    t = pages[0].lower()
    if re.search(r"^[^\n]*\b(?:comment\s+on|reply\s+to|response\s+to|rejoinder|written\s+discussion)\b", t): return True
    if re.search(r"written\s+discussion\s+to\s+paper|i\s+would\s+like\s+to\s+comment\s+on|letter\s+to\s+the\s+editor|in\s+response\s+to\s+the\s+paper", t[:800]): return True
    return False

def is_abs(pc, wc, tl):
    if pc > 4 or wc > 1500: return False
    hm = bool(re.search(r"\b(?:methods?|materials\s+and\s+methods)\b", tl))
    hr = bool(re.search(r"\b(?:results?)\b", tl))
    href = bool(re.search(r"\b(?:references|bibliography|literature\s+cited)\b", tl))
    n = sum([hm, hr, href])
    return (pc <= 3 and n <= 1) or (wc < 600 and n == 0)

def is_prov(tl):
    return bool(re.search(r"provisional\s+(?:version|pdf|acceptance|file)|draft\s+(?:manuscript|version)", tl[:3000]))

def is_ap(tl):
    return bool(re.search(r"author[\-\s]?produced\s+pdf|please\s+note\s+that\s+this\s+is\s+an?\s+author|definitive\s+publisher[\-\s]?authenticated\s+version|author[\'\u2019]?s?\s+post[\-\s]?print", tl))

def is_pp(pages, tl, ft):
    if not pages: return False
    h = tl[:1500]
    if re.search(r"(?:this\s+is\s+(?:a|an)\s+)?(?:preprint|pre-print)|accepted\s+manuscript|uncorrected\s+proof|not\s+(?:yet\s+)?peer[\s-]?reviewed|proof\s+only|accepted\s+article|this\s+article\s+has\s+been\s+accepted", h): return True
    if re.search(r"\bxxx\s*\(xxxx\)|\(xxx\)\s*xxx[-–]xxx|\bvol\.?\s+xxx\b", tl[:2000]): return True
    if re.search(r"arxiv\.org|biorxiv\.org|medrxiv\.org|ssrn\.com|researchsquare\.com|preprints\.org", tl): return True
    if re.search(r"ACCEPTED\s+MANUSCRIPT|PREPRINT\b|NOT\s+FOR\s+DISTRIBUTION", ft): return True
    lines = pages[0].split("\n")
    nums = [int(l.strip()) for l in lines if re.match(r"^\s*\d{1,3}\s*$", l.strip())]
    if len(nums) >= 8:
        sn = sorted(nums)
        seq = sum(1 for i in range(1, len(sn)) if sn[i] == sn[i-1] + 1)
        if seq >= 5 and not re.search(r"doi\s*:?\s*10\.\d{4}|journal\s+of\s+\w+|proceedings\s+of", pages[0].lower()[:500]):
            return True
    return False

def has_cover(p1, p2):
    if len(p1) < 2 or len(p2) < 2: return None
    def ws(t): return set(re.findall(r"[a-z]{4,}", t.lower()))
    def j(a, b): return len(a & b) / len(a | b) if a and b else 0
    if j(ws(p1[0]), ws(p2[0])) > 0.5: return None
    d1, d2 = j(ws(p1[1]), ws(p2[0])), j(ws(p2[1]), ws(p1[0]))
    if d1 > 0.5 and d1 > d2 + 0.1: return 1
    if d2 > 0.5 and d2 > d1 + 0.1: return 2
    return None

def csim(p1, p2, min_words=50):
    w1 = set(re.findall(r"[a-z]{5,}", " ".join(p1).lower()))
    w2 = set(re.findall(r"[a-z]{5,}", " ".join(p2).lower()))
    if len(w1) < min_words or len(w2) < min_words: return None
    return len(w1 & w2) / max(len(w1), len(w2))

def evaluate(row, pdf_base, lang_map):
    p1 = pdf_base / str(int(row["year_1"])) / row["file_1"]
    p2 = pdf_base / str(int(row["year_2"])) / row["file_2"]
    if not p1.exists() or not p2.exists():
        return {"decision": "file_missing", "reason": "missing", "rule": None}
    c1 = is_corrupted(p1); c2 = is_corrupted(p2)
    if c1 and not c2: return {"decision": "keep_2", "reason": "f1 corrupted", "rule": "R-1_corrupted"}
    if c2 and not c1: return {"decision": "keep_1", "reason": "f2 corrupted", "rule": "R-1_corrupted"}
    if c1 and c2: return {"decision": "manual", "reason": "both corrupted", "rule": "R-1_corrupted"}
    s1, s2 = p1.stat().st_size, p2.stat().st_size
    pages1, pc1, wc1, tl1, ft1 = get_info(p1)
    pages2, pc2, wc2, tl2, ft2 = get_info(p2)
    mns, mxs = min(s1, s2), max(s1, s2)
    ratio = mxs / max(mns, 1)
    if pc1 > 100 and pc2 > 100 and ratio < 1.05:
        return {"decision": "is_book", "reason": f"both books ({pc1}pp/{pc2}pp)", "rule": "R0f_book"}
    l1, l2 = lang_map.get(row["file_1"]), lang_map.get(row["file_2"])
    if l1 and l2 and l1 != l2:
        return {"decision": "distinct", "reason": f"diff lang ({l1} vs {l2})", "rule": "R0a_diff_lang"}
    cr1, cr2 = is_cr(pages1), is_cr(pages2)
    if cr1 != cr2:
        return {"decision": "distinct", "reason": f"file_{1 if cr1 else 2} is comment/reply", "rule": "R0c_comment"}
    title1 = extract_title(pages1); title2 = extract_title(pages2)
    if len(title1) > 20 and len(title2) > 20:
        ts = tsim(title1, title2)
        if ts < 0.3:
            return {"decision": "distinct", "reason": f"titles differ (tsim={ts:.2f})", "rule": "R0d_title_mismatch"}
    if wc1 < 50 and wc2 < 50 and int(row["year_1"]) != int(row["year_2"]):
        return {"decision": "distinct", "reason": "both no text, years differ", "rule": "R0e_notext_diffyear"}
    if mxs > 2 * mns:
        smaller = pages1 if s1 < s2 else pages2
        st = " ".join(smaller[:2]).lower()
        if re.search(r"supplementary\s+(material|information|data|table|figure|s\d)|supporting\s+information\b|appendix\s+[a-z]\b", st):
            return {"decision": "rename_SM", "reason": "smaller has SM keywords", "rule": "R5_SM"}
    if ratio > 3:
        swc = wc1 if s1 < s2 else wc2
        lwc = wc2 if s1 < s2 else wc1
        if swc < 20 and lwc > 500:
            return {"decision": "rename_SM", "reason": "smaller no text (likely SM)", "rule": "R5b_implicit_SM"}
    pp1, pp2 = is_pp(pages1, tl1, ft1), is_pp(pages2, tl2, ft2)
    if pp1 and not pp2: return {"decision": "keep_2", "reason": "f1 preprint", "rule": "R3_preprint"}
    if pp2 and not pp1: return {"decision": "keep_1", "reason": "f2 preprint", "rule": "R3_preprint"}
    if (mns < 200_000 and mxs > mns * 3) or (min(pc1, pc2) <= 1 and max(pc1, pc2) > 3):
        return {"decision": f"keep_{1 if s1 > s2 else 2}", "reason": "other tiny", "rule": "R1_tiny"}
    a1, a2 = is_abs(pc1, wc1, tl1), is_abs(pc2, wc2, tl2)
    if a1 and not a2: return {"decision": "keep_2", "reason": "f1 abstract", "rule": "R9_abstract"}
    if a2 and not a1: return {"decision": "keep_1", "reason": "f2 abstract", "rule": "R9_abstract"}
    if mxs > 2 * mns:
        smaller = pages1 if s1 < s2 else pages2
        if re.search(r"\b(correction|corrigendum|erratum)\b", " ".join(smaller[:1]).lower()):
            return {"decision": f"keep_{1 if s1 > s2 else 2}", "reason": "smaller is corrig", "rule": "R6_corrig"}
    if is_prov(tl1) and not is_prov(tl2): return {"decision": "keep_2", "reason": "f1 provisional", "rule": "R10_provisional"}
    if is_prov(tl2) and not is_prov(tl1): return {"decision": "keep_1", "reason": "f2 provisional", "rule": "R10_provisional"}
    if is_ap(tl1) or is_ap(tl2):
        return {"decision": f"keep_{1 if s1 < s2 else 2}", "reason": "author-produced kept smaller", "rule": "R2_author_produced"}
    if abs(pc1 - pc2) == 1:
        c = has_cover(pages1, pages2)
        if c == 1: return {"decision": "keep_2", "reason": "f1 cover letter", "rule": "R4_cover_letter"}
        if c == 2: return {"decision": "keep_1", "reason": "f2 cover letter", "rule": "R4_cover_letter"}
    sim = csim(pages1, pages2)
    if sim is not None and sim > 0.85:
        return {"decision": f"keep_{1 if s1 < s2 else 2}", "reason": f"identical (sim={sim:.2f})", "rule": "R11_identical_smaller"}
    if ratio < 1.1:
        return {"decision": f"keep_{1 if s1 < s2 else 2}", "reason": "near-identical size", "rule": "R7_near_identical"}
    if sim is not None and ratio < 1.5 and sim > 0.5:
        return {"decision": f"keep_{1 if s1 < s2 else 2}", "reason": "moderate", "rule": "R8_moderate"}
    if sim is not None and min(pc1, pc2) <= 5 and max(pc1, pc2) > 20 and sim > 0.3:
        return {"decision": f"keep_{1 if pc1 > pc2 else 2}", "reason": "chapter vs intro", "rule": "R12_chapter"}
    return {"decision": "manual", "reason": f"ratio={ratio:.2f}", "rule": None}
