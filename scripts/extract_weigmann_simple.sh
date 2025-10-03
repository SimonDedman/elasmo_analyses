#!/bin/bash
# ==============================================================================
# Simple Weigmann 2016 Table Extraction - No Dependencies
# ==============================================================================

PDF_PATH="/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/data/Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf"
OUTPUT_TXT="/home/simon/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel/data/weigmann_table2_text.txt"

echo "Extracting text from PDF..."
pdftotext -layout "$PDF_PATH" "$OUTPUT_TXT"

echo "Text extracted to: $OUTPUT_TXT"
echo ""
echo "Next steps:"
echo "1. Open the text file and locate Table II (starts around line 850)"
echo "2. Copy the table rows into a spreadsheet (LibreOffice Calc or Excel)"
echo "3. Save as CSV: data/weigmann_2016_table2_raw.csv"
echo ""
echo "Alternatively, use an online PDF-to-CSV converter:"
echo "  - https://pdftables.com/"
echo "  - https://www.adobe.com/acrobat/online/pdf-to-excel.html"
