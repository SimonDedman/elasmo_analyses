#!/usr/bin/env python3
"""
score_techniques_for_removal.py

Score 216 analytical techniques for potential removal based on criteria:
- Upstream (data generators): satellite tags, field sampling
- Midstream (generic software): Excel, R
- Downstream (generic analytics): ggplot, t-test
- Too broad/conceptual

Scoring:
1 = Keep (clearly analytical or adjacent)
2 = Debatable (borderline - could be field/bench OR analytical)
3 = Remove (field/bench technique, too generic, data generation)

Author: Simon Dedman / Claude
Date: 2025-10-22
"""

import pandas as pd
from openpyxl import load_workbook

# Read the Excel file
file_path = "data/Techniques DB for Panel Review.xlsx"
df = pd.read_excel(file_path, sheet_name='Full_List')

print("=" * 80)
print("SCORING TECHNIQUES FOR REMOVAL")
print("=" * 80)
print(f"\nTotal techniques: {len(df)}")

def score_technique(row):
    """
    Score a technique for removal (1-3) with rationale.

    Returns: "score rationale" string
    """
    tech = row['technique_name']
    cat = row['category_name']
    is_data_collection = row['data_collection_technology']
    is_software = row['software']
    is_conceptual = row['conceptual_field']
    is_statistical_model = row['statistical_model']
    is_analytical_algo = row['analytical_algorithm']

    # SCORE 3: Definite removal candidates
    # =====================================

    # Data collection technologies (upstream - generates data, not analytical)
    if is_data_collection:
        field_tech_keywords = [
            'satellite', 'tag', 'telemetry', 'acceleromet', 'camera',
            'drone', 'UAV', 'photo-id', 'captive', 'ultrasound',
            'CT imaging', 'vertebral section', 'blood chemistry',
            'respirometry', 'histology', 'genome assembly', 'RAD-seq', 'RNA-seq',
            'NIRS', 'bomb radiocarbon'
        ]
        if any(keyword.lower() in tech.lower() for keyword in field_tech_keywords):
            return "3 Data collection/field technology - upstream of analysis"

    # Pure conceptual fields without analytical component
    if is_conceptual and not is_analytical_algo and not is_statistical_model:
        conceptual_fields = [
            'physiology', 'morphology', 'reproduction', 'age & growth',
            'health & disease', 'sensory biology', 'cognition',
            'electroreception', 'magnetoreception', 'olfaction', 'vision',
            'osmoregulation', 'thermal biology', 'stress physiology',
            'reproductive endocrinology', 'human dimensions',
            'citizen science', 'co-management', 'predation behavior'
        ]
        if any(field.lower() in tech.lower() or tech.lower() in field.lower()
               for field in conceptual_fields):
            return "3 Conceptual field - too broad, not specific analytical technique"

    # Generic software without specific analytical method
    generic_software = ['Excel', 'R', 'Python', 'MATLAB', 'SPSS', 'SAS']
    if any(sw.lower() == tech.lower() for sw in generic_software):
        return "3 Generic software - too broad, not specific analytical technique"

    # Very generic statistical tests (too downstream/ubiquitous)
    generic_stats = ['t-test', 'ANOVA', 'chi-square', 'correlation', 'regression']
    if any(stat.lower() in tech.lower() for stat in generic_stats):
        if not ('GLM' in tech or 'GAM' in tech or 'mixed' in tech.lower()):
            return "3 Generic statistical test - too broad/fundamental"

    # SCORE 2: Debatable cases
    # =========================

    # Molecular/genetics lab techniques (bench methods vs analytical)
    genetics_bench = [
        'DNA extraction', 'PCR', 'gel electrophoresis', 'primer design',
        'library preparation', 'sequencing', 'qPCR', 'microsatellite',
        'restriction enzyme'
    ]
    if any(keyword.lower() in tech.lower() for keyword in genetics_bench):
        if 'analysis' not in tech.lower() and 'sequencing' not in cat.lower():
            return "2 Molecular lab technique - bench method, not purely analytical"

    # Software that implements specific methods (borderline)
    specific_software = [
        'BORIS', 'CPUE Standardization', 'Distance Sampling',
        'ADMIXTURE', 'STRUCTURE', 'MaxEnt', 'Marxan', 'IsoSpace', 'SIAR',
        'Stock Synthesis'
    ]
    if tech in specific_software:
        if is_software:
            return "2 Specialized software - implements analytical method but tool-specific"

    # Photo-ID and observer-based methods (data collection or analytical?)
    observer_methods = ['Photo-ID', 'Observer Coverage', 'Visual Census']
    if any(method in tech for method in observer_methods):
        return "2 Observer-based method - borderline data collection vs analytical"

    # Telomere analysis (molecular technique with analytical component)
    if 'telomere' in tech.lower():
        return "2 Molecular technique - lab method with analytical component"

    # Some imaging techniques (CT, ultrasound used for morphometrics)
    if any(word in tech.lower() for word in ['imaging', 'ultrasound']) and 'analysis' in tech.lower():
        return "2 Imaging analysis - borderline technology vs analytical method"

    # SCORE 1: Clearly analytical (KEEP)
    # ===================================

    # Statistical models
    if is_statistical_model:
        return "1 Statistical model - core analytical technique"

    # Analytical algorithms
    if is_analytical_algo and not is_conceptual:
        return "1 Analytical algorithm - specific analytical method"

    # Bayesian methods
    if 'bayesian' in tech.lower():
        return "1 Bayesian inference - analytical framework"

    # Population genetics analytical methods
    pop_gen_analytical = [
        'FST', 'heterozygosity', 'allele frequency', 'genetic diversity',
        'population structure', 'assignment test', 'relatedness',
        'effective population size', 'migration rate', 'coalescent',
        'phylogen', 'haplotype network'
    ]
    if any(keyword in tech.lower() for keyword in pop_gen_analytical):
        return "1 Population genetics analysis - analytical method"

    # Movement/spatial analytical methods
    spatial_analytical = [
        'kernel density', 'home range', 'space use', 'habitat selection',
        'resource selection', 'step selection', 'hidden markov',
        'state-space model', 'geolocation', 'habitat model', 'SDM',
        'connectivity', 'network analysis'
    ]
    if any(keyword in tech.lower() for keyword in spatial_analytical):
        return "1 Spatial/movement analysis - analytical method"

    # Demographic/population modeling
    demographic_analytical = [
        'population viability', 'demographic model', 'matrix model',
        'survival analysis', 'mortality estimation', 'abundance estimation',
        'mark-recapture', 'CPUE', 'stock assessment', 'age-structured'
    ]
    if any(keyword in tech.lower() for keyword in demographic_analytical):
        return "1 Demographic/population modeling - analytical method"

    # Stable isotope ANALYSIS (not just the technology)
    if 'stable isotope' in tech.lower():
        if 'analysis' in tech.lower() or 'mixing model' in tech.lower():
            return "1 Stable isotope analysis - analytical method"
        else:
            return "2 Stable isotope technique - analytical adjacent but also bench method"

    # Diet analysis methods
    diet_analytical = ['diet analysis', 'gut content', 'stomach content', 'prey composition']
    if any(keyword in tech.lower() for keyword in diet_analytical):
        if is_analytical_algo:
            return "1 Diet analysis method - analytical technique"
        else:
            return "2 Diet analysis - some analytical, some descriptive"

    # Machine learning / computational methods
    ml_methods = [
        'machine learning', 'neural network', 'random forest',
        'classification', 'cluster', 'ordination', 'PCA', 'discriminant'
    ]
    if any(keyword in tech.lower() for keyword in ml_methods):
        return "1 Machine learning/computational - analytical method"

    # Time series analysis
    if 'time series' in tech.lower() or 'temporal' in tech.lower():
        return "1 Time series analysis - analytical method"

    # Morphometric analyses
    morphometric_analytical = [
        'morphometric', 'geometric morphometric', 'shape analysis',
        'landmark', 'principal component', 'discriminant function'
    ]
    if any(keyword in tech.lower() for keyword in morphometric_analytical):
        if is_analytical_algo:
            return "1 Morphometric analysis - analytical method"

    # Default: if still unclear, use the categorical flags
    if is_analytical_algo:
        return "1 Flagged as analytical algorithm - likely analytical"

    if is_conceptual:
        return "2 Flagged as conceptual - may be too broad"

    # If we get here, it's unclear - default to neutral/keep but flag for review
    return "1 Unclear - defaulting to keep, needs manual review"


# Apply scoring function
print("\nScoring techniques...")
df['remove_reason'] = df.apply(score_technique, axis=1)

# Count scores
scores = df['remove_reason'].str.split(' ', n=1, expand=True)
df['score'] = scores[0].astype(int)

print("\n" + "=" * 80)
print("SCORING RESULTS")
print("=" * 80)
print(f"\nScore distribution:")
print(df['score'].value_counts().sort_index())
print(f"\n  Score 1 (KEEP): {(df['score'] == 1).sum()} techniques")
print(f"  Score 2 (DEBATABLE): {(df['score'] == 2).sum()} techniques")
print(f"  Score 3 (REMOVE): {(df['score'] == 3).sum()} techniques")

# Show examples from each score
print("\n" + "=" * 80)
print("SCORE 3 (REMOVE) - Sample")
print("=" * 80)
remove = df[df['score'] == 3][['technique_name', 'category_name', 'remove_reason']].head(20)
print(remove.to_string())

print("\n" + "=" * 80)
print("SCORE 2 (DEBATABLE) - Sample")
print("=" * 80)
debatable = df[df['score'] == 2][['technique_name', 'category_name', 'remove_reason']].head(20)
print(debatable.to_string())

print("\n" + "=" * 80)
print("SCORE 1 (KEEP) - Sample")
print("=" * 80)
keep = df[df['score'] == 1][['technique_name', 'category_name', 'remove_reason']].head(20)
print(keep.to_string())

# Remove the temporary score column before saving
df = df.drop('score', axis=1)

# Save back to Excel
print("\n\nSaving to Excel...")
with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    df.to_excel(writer, sheet_name='Full_List', index=False)

print(f"✅ Saved to {file_path}")
print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)
