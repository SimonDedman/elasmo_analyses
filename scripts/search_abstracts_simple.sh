#!/bin/bash
# ==============================================================================
# Search Abstracts for Missing Names - Simple Approach
# ==============================================================================
# DOCX files are ZIP archives containing XML
# Extract and search the document.xml file
# ==============================================================================

ABSTRACTS_DIR="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/abstracts"
TEMP_DIR="/tmp/abstract_search_$$"

mkdir -p "$TEMP_DIR"

echo "=== Searching Abstracts for Missing Names ==="
echo

# ==============================================================================
# Search for specific names
# ==============================================================================

search_name() {
    local search_term="$1"
    echo "=== Searching for: $search_term ==="
    echo

    found=0

    for file in "$ABSTRACTS_DIR"/*.docx; do
        if [ ! -f "$file" ]; then
            continue
        fi

        filename=$(basename "$file")

        # Extract document.xml from DOCX
        unzip -q -o -d "$TEMP_DIR" "$file" "word/document.xml" 2>/dev/null

        if [ -f "$TEMP_DIR/word/document.xml" ]; then
            # Search in the XML (case insensitive)
            if grep -iq "$search_term" "$TEMP_DIR/word/document.xml"; then
                echo "✓ Found in: $filename"
                # Extract context (strip XML tags)
                context=$(grep -io ".{0,100}$search_term.{0,100}" "$TEMP_DIR/word/document.xml" | sed 's/<[^>]*>//g' | head -1)
                echo "  Context: $context"
                echo
                found=$((found + 1))
            fi

            rm -f "$TEMP_DIR/word/document.xml"
        fi
    done

    if [ $found -eq 0 ]; then
        echo "  No matches found"
        echo
    fi
}

# Search for each target
search_name "renzo"
search_name "wozep"
search_name "shark trust"

# ==============================================================================
# Extract text from Cat Gordon file specifically
# ==============================================================================

echo "=== Extracting Cat Gordon Shark Trust Abstract ==="
echo

CAT_FILE="$ABSTRACTS_DIR/O_28 EEA2025_abstract_form_Cat Gordon Shark Trust.docx"

if [ -f "$CAT_FILE" ]; then
    unzip -q -o -d "$TEMP_DIR" "$CAT_FILE" "word/document.xml" 2>/dev/null

    if [ -f "$TEMP_DIR/word/document.xml" ]; then
        echo "Full text (XML tags removed):"
        sed 's/<[^>]*>//g' "$TEMP_DIR/word/document.xml" | tr '\n' ' ' | sed 's/  */ /g' | head -c 1000
        echo
        echo

        # Extract potential names (capitalized words)
        echo "Potential author names:"
        sed 's/<[^>]*>//g' "$TEMP_DIR/word/document.xml" | grep -oE '\b[A-Z][a-z]+ [A-Z][a-z]+\b' | sort -u
        echo
    fi
else
    echo "⚠️  Cat Gordon file not found"
fi

# ==============================================================================
# Extract text from PDFs
# ==============================================================================

echo "=== Searching PDFs ==="
echo

for file in "$ABSTRACTS_DIR"/*.pdf; do
    if [ ! -f "$file" ]; then
        continue
    fi

    filename=$(basename "$file")
    text=$(pdftotext "$file" - 2>/dev/null)

    if echo "$text" | grep -iq "renzo"; then
        echo "✓ 'Renzo' found in: $filename"
        echo "$text" | grep -io ".{0,100}renzo.{0,100}" | head -1
        echo
    fi

    if echo "$text" | grep -iq "wozep"; then
        echo "✓ 'WOZEP' found in: $filename"
        echo "$text" | grep -io ".{0,100}wozep.{0,100}" | head -1
        echo
    fi

    if echo "$text" | grep -iq "shark trust"; then
        echo "✓ 'Shark Trust' found in: $filename"
        echo "$text" | grep -io ".{0,100}shark trust.{0,100}" | head -1
        echo
    fi
done

# Cleanup
rm -rf "$TEMP_DIR"

echo "✓ Search complete"
