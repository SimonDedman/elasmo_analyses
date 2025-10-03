#!/usr/bin/env python3
"""
==============================================================================
Extract and Process Weigmann 2016 Species Checklist
==============================================================================

Purpose: Extract Table II from Weigmann (2016) PDF and convert to CSV

Input: Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf
Output: weigmann_2016_species_checklist.csv

Processing steps:
1. Extract table from PDF using tabula-py
2. Fill down hierarchical columns (Subclass, Order, Family)
3. Clean Family column (remove numbers)
4. Split "Depth distribution (m)" into min_depth_m and max_depth_m
5. Convert column names to lowercase with underscores
6. Pivot geographic distribution to binary columns (WIO, EIO, etc.)

Author: Assistant
Date: 2025-10-02

Requirements:
    pip install tabula-py pandas openpyxl

==============================================================================
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path

# Try importing tabula
try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    print("WARNING: tabula-py not installed. Install with: pip install tabula-py")

# ==============================================================================
# Configuration
# ==============================================================================

DATA_DIR = Path(__file__).parent.parent / "data"
PDF_PATH = DATA_DIR / "Weigmann_2016_Annotated_global_checklist_of_ChondrichthyesTable_II_rotated.pdf"
OUTPUT_CSV = DATA_DIR / "weigmann_2016_species_checklist.csv"
OUTPUT_WIDE_CSV = DATA_DIR / "weigmann_2016_species_checklist_wide.csv"
GEO_LOOKUP_CSV = DATA_DIR / "lookup_geographic_distribution.csv"
RAW_CSV = DATA_DIR / "weigmann_2016_table2_raw.csv"

# Geographic distribution codes
GEO_CODES = ["WIO", "EIO", "SWP", "NWP", "NEP", "SEP", "SWA", "NWA", "NEA", "SEA"]

# ==============================================================================
# STEP 1: Extract Table from PDF
# ==============================================================================

def extract_table_from_pdf():
    """
    Extract Table II from PDF using tabula-py.

    Returns:
        pd.DataFrame: Extracted table data
    """
    if not TABULA_AVAILABLE:
        print("ERROR: tabula-py not available")
        print("Install with: pip install tabula-py")
        print("\nAlternatively, use Tabula GUI:")
        print("1. Download: https://tabula.technology/")
        print("2. Extract Table II manually")
        print(f"3. Save as: {RAW_CSV}")
        return None

    print("Extracting table from PDF using tabula...")

    # Try to extract all tables (Table II spans many pages)
    # This may require multiple attempts with different page ranges

    try:
        # Extract from all pages (may take time)
        tables = tabula.read_pdf(
            str(PDF_PATH),
            pages="all",
            lattice=True,  # Use lattice mode for tables with lines
            multiple_tables=True
        )

        print(f"Extracted {len(tables)} tables from PDF")

        # Find table with expected columns
        # Table II should have: Subclass, Order, Family #, Scientific name, etc.
        expected_cols = ["Subclass", "Order", "Family", "Scientific name"]

        for i, table in enumerate(tables):
            print(f"\nTable {i+1} columns:", list(table.columns))
            if any(col in str(table.columns) for col in expected_cols):
                print(f"Found Table II candidate at index {i}")
                return table

        print("\nWARNING: Could not automatically identify Table II")
        print("Saving all extracted tables for manual review...")

        for i, table in enumerate(tables):
            output_path = DATA_DIR / f"weigmann_table_{i+1}.csv"
            table.to_csv(output_path, index=False)
            print(f"Saved: {output_path}")

        return tables[0] if tables else None

    except Exception as e:
        print(f"ERROR during PDF extraction: {e}")
        return None

# ==============================================================================
# STEP 2: Load and Process Data
# ==============================================================================

def load_raw_csv():
    """Load raw CSV (either from tabula extraction or manual export)"""

    if RAW_CSV.exists():
        print(f"Loading existing raw CSV: {RAW_CSV}")
        return pd.read_csv(RAW_CSV)
    else:
        print("Raw CSV not found. Attempting PDF extraction...")
        df = extract_table_from_pdf()

        if df is not None:
            df.to_csv(RAW_CSV, index=False)
            print(f"Saved raw extraction to: {RAW_CSV}")

        return df

# ==============================================================================
# STEP 3: Fill Down Hierarchical Columns
# ==============================================================================

def fill_down_hierarchical_columns(df):
    """
    Fill down Subclass, Order, and Family columns.

    Args:
        df (pd.DataFrame): Raw species data

    Returns:
        pd.DataFrame: Processed data with filled hierarchical columns
    """
    print("\nFilling down hierarchical columns...")

    # Columns to fill down
    hierarchical_cols = ["Subclass", "Order", "Family #"]

    for col in hierarchical_cols:
        if col in df.columns:
            df[col] = df[col].fillna(method='ffill')
        else:
            print(f"WARNING: Column '{col}' not found")

    return df

# ==============================================================================
# STEP 4: Clean Family Column
# ==============================================================================

def clean_family_column(df):
    """
    Remove numbers from Family column.
    E.g., "Heterodontidae 1" → "Heterodontidae"

    Args:
        df (pd.DataFrame): Species data

    Returns:
        pd.DataFrame: Data with cleaned Family column
    """
    print("Cleaning Family column...")

    if "Family #" in df.columns:
        # Extract family name only (remove trailing numbers)
        df["Family"] = df["Family #"].str.replace(r"\s+\d+$", "", regex=True)
        df = df.drop(columns=["Family #"])

        # Fill down family names
        df["Family"] = df["Family"].fillna(method='ffill')

    return df

# ==============================================================================
# STEP 5: Split Depth Distribution Column
# ==============================================================================

def parse_depth_range(depth_str):
    """
    Parse depth range string into min and max values.

    Examples:
        "0-590" → (0, 590)
        "3->100" → (3, 100)
        ">1000" → (1000, None)
        "Inshore" → (0, 50)

    Args:
        depth_str (str): Depth range string

    Returns:
        tuple: (min_depth, max_depth)
    """
    if pd.isna(depth_str):
        return (None, None)

    depth_str = str(depth_str).strip()

    # Handle "Inshore"
    if "Inshore" in depth_str or "inshore" in depth_str:
        return (0, 50)

    # Handle ">1000" format
    if depth_str.startswith(">"):
        min_depth = int(re.search(r"\d+", depth_str).group())
        return (min_depth, None)

    # Handle "3->100" format
    if "->" in depth_str:
        parts = depth_str.split("->")
        min_depth = int(re.search(r"\d+", parts[0]).group())
        max_depth = int(re.search(r"\d+", parts[1]).group())
        return (min_depth, max_depth)

    # Handle "0-590" format
    if "-" in depth_str:
        parts = depth_str.split("-")
        try:
            min_depth = int(parts[0])
            max_depth = int(parts[1])
            return (min_depth, max_depth)
        except ValueError:
            return (None, None)

    # Single number
    try:
        depth = int(re.search(r"\d+", depth_str).group())
        return (depth, depth)
    except (AttributeError, ValueError):
        return (None, None)

def split_depth_column(df):
    """
    Split 'Depth distribution (m)' into min_depth_m and max_depth_m.

    Args:
        df (pd.DataFrame): Species data

    Returns:
        pd.DataFrame: Data with split depth columns
    """
    print("Splitting depth distribution column...")

    depth_col = "Depth distribution (m)"

    if depth_col in df.columns:
        # Parse depth ranges
        df[["min_depth_m", "max_depth_m"]] = df[depth_col].apply(
            lambda x: pd.Series(parse_depth_range(x))
        )

        # Keep original for reference
        df = df.rename(columns={depth_col: "depth_raw"})

    return df

# ==============================================================================
# STEP 6: Convert Column Names to Lowercase with Underscores
# ==============================================================================

def clean_column_names(df):
    """
    Convert column names to lowercase with underscores.

    Args:
        df (pd.DataFrame): Species data

    Returns:
        pd.DataFrame: Data with cleaned column names
    """
    print("Converting column names to lowercase...")

    df.columns = (
        df.columns
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[()]", "", regex=True)
    )

    return df

# ==============================================================================
# STEP 7: Process Geographic Distribution
# ==============================================================================

def add_geographic_binary_columns(df):
    """
    Add binary columns for each geographic distribution code.

    Args:
        df (pd.DataFrame): Species data

    Returns:
        pd.DataFrame: Data with binary geographic columns
    """
    print("Adding binary geographic distribution columns...")

    geo_col = "geographic_distribution"

    if geo_col in df.columns:
        for code in GEO_CODES:
            col_name = f"geo_{code.lower()}"
            df[col_name] = df[geo_col].str.contains(code, na=False)

    return df

# ==============================================================================
# STEP 8: Main Processing Pipeline
# ==============================================================================

def process_species_data():
    """Main processing pipeline"""

    print("=" * 80)
    print("WEIGMANN 2016 SPECIES CHECKLIST EXTRACTION")
    print("=" * 80)

    # Load raw data
    df = load_raw_csv()

    if df is None:
        print("\nERROR: Could not load data")
        print("\nMANUAL EXTRACTION REQUIRED:")
        print("1. Download Tabula: https://tabula.technology/")
        print("2. Open PDF and extract Table II")
        print(f"3. Save as: {RAW_CSV}")
        return

    print(f"\nRaw data: {len(df)} rows, {len(df.columns)} columns")
    print("Columns:", list(df.columns))

    # Process data
    df = fill_down_hierarchical_columns(df)
    df = clean_family_column(df)
    df = split_depth_column(df)
    df = clean_column_names(df)
    df = add_geographic_binary_columns(df)

    # Reorder columns
    cols_ordered = [
        "subclass",
        "order",
        "family",
        "scientific_name",
        "species_authorship",
        "common_name",
        "maximum_size_mm",
        "min_depth_m",
        "max_depth_m",
    ]

    # Add geographic columns
    geo_cols = [f"geo_{code.lower()}" for code in GEO_CODES]
    cols_ordered.extend(geo_cols)

    # Add remaining columns
    remaining_cols = [c for c in df.columns if c not in cols_ordered]
    cols_ordered.extend(remaining_cols)

    # Select available columns
    cols_final = [c for c in cols_ordered if c in df.columns]
    df = df[cols_final]

    # Save processed data
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved processed data: {OUTPUT_CSV}")
    print(f"  - Rows: {len(df)}")
    print(f"  - Columns: {len(df.columns)}")

    # Save wide format (same as long for now)
    df.to_csv(OUTPUT_WIDE_CSV, index=False)
    print(f"Saved wide format: {OUTPUT_WIDE_CSV}")

    # Print summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    print(f"\nTotal species: {len(df)}")

    if "subclass" in df.columns:
        print("\nSpecies by subclass:")
        print(df["subclass"].value_counts())

    if "family" in df.columns:
        print("\nTop 10 families:")
        print(df["family"].value_counts().head(10))

    if any(f"geo_{code.lower()}" in df.columns for code in GEO_CODES):
        print("\nGeographic distribution:")
        geo_summary = {
            code: df[f"geo_{code.lower()}"].sum()
            for code in GEO_CODES
            if f"geo_{code.lower()}" in df.columns
        }
        for code, count in sorted(geo_summary.items(), key=lambda x: x[1], reverse=True):
            print(f"  {code}: {count} species")

    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)

# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    process_species_data()
