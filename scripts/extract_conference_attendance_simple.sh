#!/bin/bash
# ==============================================================================
# Extract Conference Attendance - Simple Version Using pdftotext
# ==============================================================================

CONF_DIR="/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/EEA History"
OUTPUT_DIR="/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs/conference_texts"

mkdir -p "$OUTPUT_DIR"

echo "=== Extracting Conference Program Texts ==="
echo

# Extract PDFs
echo "Extracting EEA 2013..."
pdftotext "$CONF_DIR/EEA 2013 Plymouth/2013.11.01 EEA 17 Plymouth Abstract Book.pdf" "$OUTPUT_DIR/EEA2013.txt" 2>/dev/null && echo "✓ EEA 2013" || echo "✗ EEA 2013 failed"

echo "Extracting EEA 2017..."
pdftotext "$CONF_DIR/EEA2017_program_provisional.pdf" "$OUTPUT_DIR/EEA2017.txt" 2>/dev/null && echo "✓ EEA 2017" || echo "✗ EEA 2017 failed"

echo "Extracting EEA 2021..."
pdftotext "$CONF_DIR/EEA2021-program.pdf" "$OUTPUT_DIR/EEA2021.txt" 2>/dev/null && echo "✓ EEA 2021" || echo "✗ EEA 2021 failed"

echo "Extracting EEA 2023..."
pdftotext "$CONF_DIR/eea2023programme.pdf" "$OUTPUT_DIR/EEA2023.txt" 2>/dev/null && echo "✓ EEA 2023" || echo "✗ EEA 2023 failed"

echo "Extracting AES 2015 Oral..."
pdftotext "$CONF_DIR/AES 2015 Reno/Oral Presentations_5 June 2015.pdf" "$OUTPUT_DIR/AES2015_oral.txt" 2>/dev/null && echo "✓ AES 2015 Oral" || echo "✗ AES 2015 Oral failed"

echo "Extracting AES 2015 Posters..."
pdftotext "$CONF_DIR/AES 2015 Reno/Poster Presentations_5 June 2015.pdf" "$OUTPUT_DIR/AES2015_poster.txt" 2>/dev/null && echo "✓ AES 2015 Poster" || echo "✗ AES 2015 Poster failed"

echo
echo "✓ PDF extraction complete"
echo "Output directory: $OUTPUT_DIR"
echo

# Show file sizes
ls -lh "$OUTPUT_DIR"/*.txt 2>/dev/null | awk '{print $9, "(" $5 ")"}'

echo
echo "Next: Run R script to parse names from text files"
