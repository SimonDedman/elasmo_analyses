#!/usr/bin/env python3
"""Detect non-English PDFs in the SharkPapers library.

Scans all PDFs, extracts first-page text via pdftotext, and uses
heuristic language detection (non-ASCII chars, stopword frequency,
language-specific word lists).
"""

import csv
import os
import re
import subprocess
import sys
from collections import Counter
from multiprocessing import Pool, cpu_count
from pathlib import Path

SHARK_PAPERS = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
OUTPUT_CSV = Path("/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs/non_english_papers.csv")

# English stopwords (top ~80)
ENGLISH_STOPS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was",
    "were", "been", "being", "have", "has", "had", "does", "did", "but",
    "not", "you", "all", "can", "her", "his", "its", "our", "they",
    "will", "would", "could", "should", "may", "might", "shall", "which",
    "who", "whom", "what", "when", "where", "how", "why", "each",
    "both", "few", "more", "most", "other", "some", "such", "than",
    "too", "very", "also", "just", "about", "above", "after", "before",
    "between", "into", "through", "during", "without", "again",
    "further", "then", "once", "here", "there", "these", "those",
    "only", "same", "while", "because", "until", "among", "since",
    "however", "although", "whether", "still", "already", "often",
    "much", "many", "well", "even", "over", "under",
}

# Language-specific marker words (common articles, prepositions, conjunctions)
LANG_MARKERS = {
    "French": {"les", "des", "une", "dans", "pour", "avec", "sur", "par",
               "est", "sont", "pas", "qui", "que", "aux", "cette", "ces",
               "ont", "mais", "aussi", "leur", "entre", "nous", "vous",
               "ses", "son", "comme", "fait", "deux", "peut", "plus",
               "chez", "elle", "tout"},
    "German": {"der", "die", "das", "und", "ein", "eine", "ist", "von",
               "den", "dem", "des", "auf", "mit", "sich", "nicht", "auch",
               "als", "wird", "aus", "bei", "nach", "fur", "für", "über",
               "oder", "kann", "sind", "nur", "wie", "noch", "wurde",
               "aber", "vor", "mehr", "durch", "alle", "sehr", "einem",
               "einer", "zeit"},
    "Spanish": {"los", "las", "una", "del", "por", "con", "para", "que",
                "como", "más", "son", "fue", "sus", "han", "sin", "pero",
                "sobre", "entre", "desde", "todos", "esta", "este", "ese",
                "también", "cuando", "muy", "cada", "ser", "hay", "puede",
                "estos", "otras", "otro"},
    "Portuguese": {"uma", "dos", "das", "nos", "com", "por", "para", "que",
                   "como", "mais", "são", "foi", "sua", "seu", "sem", "mas",
                   "sobre", "entre", "desde", "todos", "esta", "este", "esse",
                   "também", "quando", "cada", "ser", "pode", "estas",
                   "outros", "outras", "foram", "pelo", "pela", "aos"},
    "Italian": {"della", "degli", "delle", "nella", "nello", "nelle", "sono",
                "con", "per", "che", "una", "dal", "dall", "dai", "dai",
                "tra", "fra", "come", "più", "anche", "stato", "questo",
                "questa", "questi", "queste", "ogni", "tutto", "può",
                "essere", "suoi", "sue"},
    "Dutch": {"van", "het", "een", "met", "voor", "zijn", "worden", "naar",
              "ook", "maar", "bij", "uit", "aan", "als", "niet", "werd",
              "deze", "meer", "nog", "wel", "hun", "zij", "door", "heeft",
              "alle", "twee", "toen", "veel", "onder", "andere"},
    "Japanese": set(),  # detected via CJK chars
    "Chinese": set(),   # detected via CJK chars
    "Russian": set(),   # detected via Cyrillic chars
    "Korean": set(),    # detected via Hangul chars
    "Arabic": set(),    # detected via Arabic chars
}


def extract_first_pages(pdf_path: str, pages: int = 2) -> str:
    """Extract text from first N pages of PDF using pdftotext."""
    try:
        result = subprocess.run(
            ["pdftotext", "-l", str(pages), pdf_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout
    except Exception:
        return ""


def count_script_chars(text: str):
    """Count characters belonging to various scripts."""
    cyrillic = 0
    cjk = 0
    arabic = 0
    hangul = 0
    latin = 0
    for ch in text:
        cp = ord(ch)
        if 0x0400 <= cp <= 0x04FF or 0x0500 <= cp <= 0x052F:
            cyrillic += 1
        elif (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or
              0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF):
            cjk += 1
        elif 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:
            arabic += 1
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            hangul += 1
        elif 0x0041 <= cp <= 0x024F:  # Basic Latin + Latin Extended
            latin += 1
    return {"cyrillic": cyrillic, "cjk": cjk, "arabic": arabic,
            "hangul": hangul, "latin": latin}


def detect_language(text: str):
    """Detect language of text. Returns (language, confidence)."""
    if not text or len(text.strip()) < 50:
        return None, "low"

    # Step 1: Check for non-Latin scripts
    scripts = count_script_chars(text)
    total_alpha = sum(scripts.values())
    if total_alpha == 0:
        return None, "low"

    if scripts["cyrillic"] > total_alpha * 0.2:
        return "Russian", "high" if scripts["cyrillic"] > total_alpha * 0.5 else "medium"
    if scripts["cjk"] > total_alpha * 0.1:
        # Distinguish Japanese vs Chinese by looking for hiragana/katakana
        jp_chars = sum(1 for ch in text if 0x3040 <= ord(ch) <= 0x30FF)
        if jp_chars > scripts["cjk"] * 0.1:
            return "Japanese", "high" if scripts["cjk"] > total_alpha * 0.3 else "medium"
        return "Chinese", "high" if scripts["cjk"] > total_alpha * 0.3 else "medium"
    if scripts["arabic"] > total_alpha * 0.2:
        return "Arabic", "high" if scripts["arabic"] > total_alpha * 0.5 else "medium"
    if scripts["hangul"] > total_alpha * 0.2:
        return "Korean", "high" if scripts["hangul"] > total_alpha * 0.5 else "medium"

    # Step 2: Word-based analysis for Latin-script languages
    words = re.findall(r"[a-záàâãäéèêëíìîïóòôõöúùûüñçæøåßðþ]{3,}",
                       text.lower())
    if len(words) < 20:
        return None, "low"

    word_counts = Counter(words)
    top50 = [w for w, _ in word_counts.most_common(50)]

    # Check English stopword proportion
    eng_hits = sum(1 for w in top50 if w in ENGLISH_STOPS)
    eng_ratio = eng_hits / len(top50) if top50 else 0

    # Check each language's markers
    lang_scores = {}
    for lang, markers in LANG_MARKERS.items():
        if not markers:
            continue
        hits = sum(1 for w in top50 if w in markers)
        if hits >= 3:
            lang_scores[lang] = hits

    # Decision logic
    if eng_ratio >= 0.10:
        # Likely English
        return None, "low"

    if lang_scores:
        best_lang = max(lang_scores, key=lang_scores.get)
        best_score = lang_scores[best_lang]
        if best_score >= 8:
            confidence = "high"
        elif best_score >= 5:
            confidence = "medium"
        else:
            confidence = "low"
        return best_lang, confidence

    # Low English ratio but no strong signal for another language —
    # leave blank rather than mislabel (many are English with poor text extraction)
    return None, "low"


def process_pdf(pdf_path: str):
    """Process a single PDF and return result if non-English."""
    text = extract_first_pages(pdf_path)
    lang, confidence = detect_language(text)
    if lang is not None:
        return pdf_path, lang, confidence
    return None


def main():
    # Collect all PDFs
    print("Collecting PDF paths...")
    pdf_paths = []
    for year_dir in sorted(SHARK_PAPERS.iterdir()):
        if year_dir.is_dir():
            for pdf in year_dir.glob("*.pdf"):
                pdf_paths.append(str(pdf))

    total = len(pdf_paths)
    print(f"Found {total} PDFs to scan.")

    # Process with multiprocessing
    ncpu = max(1, cpu_count() - 1)
    print(f"Using {ncpu} workers...")

    results = []
    processed = 0

    with Pool(ncpu) as pool:
        for result in pool.imap_unordered(process_pdf, pdf_paths, chunksize=50):
            processed += 1
            if processed % 1000 == 0:
                print(f"  Progress: {processed}/{total} ({processed*100//total}%)")
            if result is not None:
                results.append(result)

    print(f"\nScan complete: {total} PDFs scanned, {len(results)} non-English detected.\n")

    # Sort results
    results.sort(key=lambda x: x[0])

    # Build output rows with year
    rows = []
    for path, lang, conf in results:
        rel = os.path.relpath(path, SHARK_PAPERS)
        parts = rel.split(os.sep)
        year = parts[0] if len(parts) > 1 else ""
        filename = parts[-1]
        rows.append({"year": year, "filename": filename, "detected_language": lang,
                      "confidence": conf})

    # Save CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "filename", "detected_language", "confidence"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Results saved to {OUTPUT_CSV}")

    # Summary
    lang_counts = Counter(r["detected_language"] for r in rows)
    conf_counts = Counter(r["confidence"] for r in rows)

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total PDFs scanned:      {total}")
    print(f"Non-English detected:    {len(results)}")
    print(f"\nBy language:")
    for lang, count in lang_counts.most_common():
        print(f"  {lang:30s} {count:5d}")
    print(f"\nBy confidence:")
    for conf, count in conf_counts.most_common():
        print(f"  {conf:30s} {count:5d}")


if __name__ == "__main__":
    main()
