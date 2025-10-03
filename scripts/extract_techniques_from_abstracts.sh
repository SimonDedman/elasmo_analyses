#!/bin/bash
# ==============================================================================
# Extract Analytical Techniques from Abstracts
# ==============================================================================
# Approach: Extract method-rich sections from abstracts (DOCX + PDF)
# Output: Detailed technique mentions with context
# ==============================================================================

ABSTRACTS_DIR="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/abstracts"
OUTPUT_FILE="/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/outputs/techniques_from_abstracts_raw.txt"
TEMP_DIR="/tmp/abstract_techniques_$$"

mkdir -p "$TEMP_DIR"
> "$OUTPUT_FILE"

echo "=== Extracting Techniques from Abstracts ==="
echo

# ==============================================================================
# Define technique keywords to search for
# ==============================================================================

# Comprehensive list of analytical technique keywords
TECHNIQUES=(
    # Biology & Life History
    "age.*growth"
    "von.*bertalanffy"
    "vertebra.*section"
    "validated.*age"
    "histolog"
    "reproduct.*cycle"
    "maturity.*ogive"
    "fecundity"
    "gestation"

    # Behaviour
    "acceleromet"
    "video.*analysis"
    "behavioural.*observation"
    "time.*budget"
    "social.*network"

    # Trophic Ecology
    "stable.*isotope"
    "δ13c|δ15n|d13c|d15n"
    "fatty.*acid"
    "stomach.*content"
    "metabarcod"
    "compound.*specific.*isotope"

    # Genetics & Genomics
    "microsatellite"
    "single.*nucleotide.*polymorphism|snp"
    "whole.*genome.*sequenc"
    "rad.*seq|ddrad"
    "environmental.*dna|edna"
    "population.*genetic.*structure"

    # Movement & Space Use
    "acoustic.*telemetry"
    "satellite.*tag|psat"
    "hidden.*markov.*model|hmm"
    "state.*space.*model|ssm"
    "kernel.*density"
    "brownian.*bridge"
    "species.*distribution.*model|sdm"
    "maxent|boosted.*regression.*tree|random.*forest"
    "generalized.*additive.*model|gam"

    # Fisheries & Stock Assessment
    "surplus.*production"
    "catch.*per.*unit.*effort|cpue"
    "generalized.*linear.*model|glm"
    "delta.*lognormal"
    "age.*structured.*model"
    "length.*based.*indicator|lbi"
    "data.*poor.*stock.*assessment|dbsra"

    # Conservation
    "iucn.*red.*list"
    "extinction.*risk.*assessment"
    "participatory.*monitoring"
    "questionnaire.*survey"
    "semi.*structured.*interview"

    # Data Science
    "machine.*learning"
    "neural.*network"
    "bayesian.*inference"
    "mcmc|stan|jags"
    "random.*forest"
    "gradient.*boosting"
    "principal.*component.*analysis|pca"
    "cluster.*analysis"
    "meta.*analysis"
)

echo "Searching for ${#TECHNIQUES[@]} technique patterns..."
echo

# ==============================================================================
# Function to extract text and search for techniques
# ==============================================================================

search_abstract() {
    local file="$1"
    local filename=$(basename "$file")
    local filetype="${file##*.}"

    # Extract text based on file type
    if [ "$filetype" = "pdf" ]; then
        text=$(pdftotext "$file" - 2>/dev/null)
    elif [ "$filetype" = "docx" ]; then
        # Extract using unzip
        unzip -q -o -d "$TEMP_DIR" "$file" "word/document.xml" 2>/dev/null
        if [ -f "$TEMP_DIR/word/document.xml" ]; then
            text=$(sed 's/<[^>]*>//g' "$TEMP_DIR/word/document.xml" | tr '\n' ' ')
            rm -f "$TEMP_DIR/word/document.xml"
        else
            return
        fi
    else
        return
    fi

    # Skip if no text extracted
    [ -z "$text" ] && return

    # Search for each technique pattern
    for pattern in "${TECHNIQUES[@]}"; do
        # Case-insensitive grep
        if echo "$text" | grep -iq "$pattern"; then
            # Extract context around match
            context=$(echo "$text" | grep -io ".{0,100}${pattern}.{0,100}" | head -1)

            # Clean up context (remove extra whitespace)
            context=$(echo "$context" | tr -s ' ' | sed 's/^ *//;s/ *$//')

            # Output: filename | pattern | context
            echo "$filename|$pattern|$context" >> "$OUTPUT_FILE"
        fi
    done
}

# ==============================================================================
# Process all abstracts
# ==============================================================================

echo "Processing DOCX files..."
docx_count=0
for file in "$ABSTRACTS_DIR"/*.docx; do
    [ -f "$file" ] || continue
    search_abstract "$file"
    docx_count=$((docx_count + 1))
done
echo "  Processed $docx_count DOCX files"

echo "Processing PDF files..."
pdf_count=0
for file in "$ABSTRACTS_DIR"/*.pdf; do
    [ -f "$file" ] || continue
    search_abstract "$file"
    pdf_count=$((pdf_count + 1))
done
echo "  Processed $pdf_count PDF files"

# ==============================================================================
# Generate summary statistics
# ==============================================================================

echo
echo "=== Extraction Summary ==="
echo

total_files=$((docx_count + pdf_count))
matches=$(wc -l < "$OUTPUT_FILE")
unique_files=$(cut -d'|' -f1 "$OUTPUT_FILE" | sort -u | wc -l)
unique_patterns=$(cut -d'|' -f2 "$OUTPUT_FILE" | sort -u | wc -l)

echo "Total files processed: $total_files"
echo "Total technique matches: $matches"
echo "Files with techniques: $unique_files"
echo "Unique patterns found: $unique_patterns"
echo
echo "✓ Saved: $OUTPUT_FILE"

# ==============================================================================
# Top 10 most common techniques
# ==============================================================================

echo
echo "Top 10 most common techniques:"
cut -d'|' -f2 "$OUTPUT_FILE" | sort | uniq -c | sort -rn | head -10

# Cleanup
rm -rf "$TEMP_DIR"

echo
echo "✓ Abstract extraction complete"
echo
echo "Next: Run parse_techniques_from_abstracts.R to structure this data"
