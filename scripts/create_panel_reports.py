#!/usr/bin/env python3
"""
Generate Expert Panel Reports
Creates comprehensive markdown reports for each discipline panel with:
- Technique analysis and trends
- Cross-discipline insights
- Discussion prompts for panelists
- Embedded figure references
"""

import pandas as pd
from pathlib import Path
import datetime

# Configuration
DISCIPLINES = {
    'BEH': 'Behaviour',
    'BIO': 'Biology',
    'CON': 'Conservation',
    'DATA': 'Data Science',
    'FISH': 'Fisheries',
    'GEN': 'Genetics',
    'MOV': 'Movement',
    'TRO': 'Trophic Ecology'
}

OUTPUT_DIR = Path('outputs/panel_reports')
OUTPUT_DIR.mkdir(exist_ok=True)

def load_data():
    """Load all necessary data files"""
    print("Loading data files...")

    data = {}

    # Load technique data
    data['techniques'] = pd.read_csv('outputs/analysis/techniques_per_discipline.csv')
    data['emerging'] = pd.read_csv('outputs/analysis/all_emerging_techniques.csv')
    data['trends'] = pd.read_csv('outputs/analysis/technique_trends_analysis.csv')

    # Load summaries per discipline
    data['summaries'] = {}
    for disc in DISCIPLINES.keys():
        summary_file = f'outputs/analysis/technique_summary_{disc}.txt'
        if Path(summary_file).exists():
            with open(summary_file) as f:
                data['summaries'][disc] = f.read()

    print(f"✓ Loaded {len(data['techniques'])} technique records")
    print(f"✓ Loaded {len(data['emerging'])} emerging techniques")

    return data

def analyze_cross_discipline(data):
    """Identify cross-discipline techniques"""
    print("\nAnalyzing cross-discipline patterns...")

    # Count how many disciplines each technique appears in
    technique_disc = data['techniques'].groupby('technique').agg({
        'discipline': lambda x: list(set(x)),
        'paper_count': 'sum'
    }).reset_index()

    technique_disc['n_disciplines'] = technique_disc['discipline'].apply(len)

    cross_disc = technique_disc[technique_disc['n_disciplines'] >= 2].copy()
    cross_disc = cross_disc.sort_values(['n_disciplines', 'paper_count'], ascending=[False, False])

    print(f"✓ Found {len(cross_disc)} cross-discipline techniques")
    print(f"  - Used in 2 disciplines: {sum(cross_disc['n_disciplines'] == 2)}")
    print(f"  - Used in 3+ disciplines: {sum(cross_disc['n_disciplines'] >= 3)}")

    return cross_disc

def create_discipline_report(disc, disc_name, data, cross_disc):
    """Create markdown report for one discipline"""

    print(f"\nGenerating report for {disc_name}...")

    # Filter data for this discipline
    disc_techniques = data['techniques'][data['techniques']['discipline'] == disc].copy()
    disc_techniques = disc_techniques.sort_values('paper_count', ascending=False)

    disc_emerging = data['emerging'][data['emerging']['discipline'] == disc].copy()

    # Get cross-discipline techniques relevant to this discipline
    relevant_cross = cross_disc[cross_disc['discipline'].apply(lambda x: disc in x)]

    # Start report
    report = []
    report.append(f"# Expert Panel Report: {disc_name}")
    report.append(f"\n**Discipline Code**: {disc}")
    report.append(f"**Generated**: {datetime.date.today()}")
    report.append(f"**Total Techniques**: {len(disc_techniques)}")
    report.append(f"**Total Papers**: {disc_techniques['paper_count'].sum():,}")

    report.append("\n---\n")

    # Table of Contents
    report.append("## Table of Contents")
    report.append("\n1. [Overview & Key Statistics](#overview)")
    report.append("2. [Technique Analysis](#technique-analysis)")
    report.append("3. [Cross-Discipline Connections](#cross-discipline)")
    report.append("4. [Emerging Techniques](#emerging)")
    report.append("5. [Discussion Prompts for Panel](#discussion)")
    report.append("6. [Figures](#figures)")

    report.append("\n---\n")

    # Section 1: Overview
    report.append("<a name='overview'></a>")
    report.append("## 1. Overview & Key Statistics\n")

    if disc in data['summaries']:
        report.append("### Technique Summary\n")
        report.append("```")
        report.append(data['summaries'][disc])
        report.append("```\n")

    report.append("### Top 10 Most Used Techniques\n")
    top_10 = disc_techniques.head(10)
    report.append("| Rank | Technique | Papers | % of Discipline |")
    report.append("|------|-----------|--------|-----------------|")
    total_papers = disc_techniques['paper_count'].sum()
    for idx, row in top_10.iterrows():
        pct = (row['paper_count'] / total_papers * 100)
        report.append(f"| {top_10.index.get_loc(idx)+1} | {row['technique']} | {row['paper_count']:,} | {pct:.1f}% |")

    report.append("\n---\n")

    # Section 2: Technique Analysis
    report.append("<a name='technique-analysis'></a>")
    report.append("## 2. Technique Analysis\n")

    # Classify by usage
    low_usage = disc_techniques[disc_techniques['paper_count'] <= 5]
    medium_usage = disc_techniques[(disc_techniques['paper_count'] > 5) & (disc_techniques['paper_count'] <= 20)]
    high_usage = disc_techniques[disc_techniques['paper_count'] > 20]

    report.append(f"### Usage Distribution\n")
    report.append(f"- **High usage** (>20 papers): {len(high_usage)} techniques")
    report.append(f"- **Medium usage** (6-20 papers): {len(medium_usage)} techniques")
    report.append(f"- **Low usage** (≤5 papers): {len(low_usage)} techniques\n")

    if len(low_usage) > 0:
        report.append("### Low Usage Techniques - Candidates for Expert Review\n")
        report.append("\n**Question for Panel**: Are these techniques truly rare, or are they:")
        report.append("- Under-reported in the literature?")
        report.append("- Niche but important methodologies?")
        report.append("- Potentially redundant with other techniques?")
        report.append("- Emerging methods that need more visibility?\n")

        report.append("| Technique | Papers | Notes |")
        report.append("|-----------|--------|-------|")
        for _, row in low_usage.head(15).iterrows():
            report.append(f"| {row['technique']} | {row['paper_count']} | _Panel input needed_ |")

    report.append("\n---\n")

    # Section 3: Cross-Discipline
    report.append("<a name='cross-discipline'></a>")
    report.append("## 3. Cross-Discipline Connections\n")

    if len(relevant_cross) > 0:
        report.append(f"### Techniques Shared with Other Disciplines ({len(relevant_cross)})\n")
        report.append("\nThese techniques are used across multiple disciplines. ")
        report.append("**Discussion topics**: How are they applied differently? ")
        report.append("Are there opportunities for collaboration or standardization?\n")

        report.append("| Technique | Used In | Total Papers | Discussion Points |")
        report.append("|-----------|---------|--------------|-------------------|")
        for _, row in relevant_cross.head(20).iterrows():
            discs = ', '.join(row['discipline'])
            report.append(f"| {row['technique']} | {discs} | {row['paper_count']:,} | How does {disc_name} use this vs. other fields? |")

        # Highlight DATA discipline crossover
        data_cross = relevant_cross[relevant_cross['discipline'].apply(lambda x: 'DATA' in x)]
        if len(data_cross) > 0 and disc != 'DATA':
            report.append(f"\n### Data Science Techniques in {disc_name}\n")
            report.append("\n**Key Question**: How well have modern data science methods penetrated your field?\n")
            report.append("| Technique | Papers in Your Field | Total Papers Across Fields |")
            report.append("|-----------|---------------------|----------------------------|")
            for _, row in data_cross.head(10).iterrows():
                disc_count = disc_techniques[disc_techniques['technique'] == row['technique']]['paper_count'].values
                disc_count = disc_count[0] if len(disc_count) > 0 else 0
                report.append(f"| {row['technique']} | {disc_count} | {row['paper_count']:,} |")
    else:
        report.append("No cross-discipline techniques identified for this field.")
        report.append("\n**Question for Panel**: Is this discipline highly specialized, or are there ")
        report.append("techniques from other fields that could be beneficial?\n")

    report.append("\n---\n")

    # Section 4: Emerging Techniques
    report.append("<a name='emerging'></a>")
    report.append("## 4. Emerging Techniques\n")

    if len(disc_emerging) > 0:
        report.append(f"### Recently Adopted Methods ({len(disc_emerging)})\n")
        report.append("\nThese techniques show growing adoption. **Questions for panel**:")
        report.append("- Which are most promising?")
        report.append("- Which need more validation?")
        report.append("- Are there barriers to adoption?\n")

        report.append("| Technique | Papers | Classification | Pros & Cons |")
        report.append("|-----------|--------|----------------|-------------|")
        for _, row in disc_emerging.iterrows():
            report.append(f"| {row['technique']} | {row['paper_count']} | {row['classification']} | _Panel input needed_ |")
    else:
        report.append("No emerging techniques identified in automated analysis.")
        report.append("\n**Question for Panel**: Are there new methods in your field that should be tracked?\n")

    report.append("\n---\n")

    # Section 5: Discussion Prompts
    report.append("<a name='discussion'></a>")
    report.append("## 5. Discussion Prompts for Panel\n")

    report.append("### General Questions\n")
    report.append("1. **Technique Completeness**: Are there major techniques missing from this list?")
    report.append("2. **Redundancy**: Are any techniques listed separately that should be combined?")
    report.append("3. **Terminology**: Are technique names clear and standard, or do they need clarification?")
    report.append("4. **Trends**: Which techniques are becoming more/less important?")
    report.append("5. **Gaps**: What techniques from other fields could benefit this discipline?\n")

    report.append("### Specific Technique Questions\n")
    report.append("\nFor low-usage techniques:")
    report.append("- Why might these be underrepresented?")
    report.append("- Should they be promoted or deprecated?\n")

    report.append("\nFor cross-discipline techniques:")
    report.append("- How does your field use these differently?")
    report.append("- Are there collaboration opportunities?\n")

    report.append("\nFor emerging techniques:")
    report.append("- What are the practical barriers to adoption?")
    report.append("- What training/resources would help?")
    report.append("- Should any be prioritized for community adoption?\n")

    report.append("\n---\n")

    # Section 6: Figures
    report.append("<a name='figures'></a>")
    report.append("## 6. Figures\n")
    report.append(f"\n### Figure 1: Technique Usage - {disc_name}")
    report.append(f"\n![Technique Usage](../../figures/technique_counts_stacked_{disc}.png)")
    report.append("\n*Stacked bar chart showing technique usage frequency*\n")

    if disc == 'DATA':
        report.append("\n### Figure 2: Data Science Adoption Across Disciplines")
        report.append("\n*See cross-discipline analysis for DATA technique penetration*\n")

    report.append("\n---\n")

    # Footer
    report.append("## Notes for Panel Review\n")
    report.append("- Please annotate this document with your expertise")
    report.append("- Focus on techniques marked '_Panel input needed_'")
    report.append("- Suggest additions, combinations, or removals")
    report.append("- Identify priority areas for community attention\n")

    report.append(f"\n**Generated**: {datetime.date.today()}")
    report.append(f"\n**Data source**: {len(disc_techniques)} techniques from {disc_techniques['paper_count'].sum():,} papers")

    return '\n'.join(report)

def create_cross_discipline_report(cross_disc, data):
    """Create overall cross-discipline analysis report"""

    print("\nGenerating cross-discipline summary report...")

    report = []
    report.append("# Cross-Discipline Techniques Analysis")
    report.append(f"\n**Generated**: {datetime.date.today()}")
    report.append(f"\n**Purpose**: Identify commonalities and opportunities for collaboration\n")

    report.append("## Overview\n")
    report.append(f"**Total techniques used in 2+ disciplines**: {len(cross_disc)}\n")

    # By number of disciplines
    for n in sorted(cross_disc['n_disciplines'].unique(), reverse=True):
        count = sum(cross_disc['n_disciplines'] == n)
        report.append(f"- Used in {n} disciplines: {count} techniques")

    report.append("\n## Top 20 Most Widely Used Techniques\n")
    report.append("| Technique | Disciplines | Total Papers | Applications |")
    report.append("|-----------|-------------|--------------|--------------|")
    for _, row in cross_disc.head(20).iterrows():
        discs = ', '.join(row['discipline'])
        report.append(f"| {row['technique']} | {discs} | {row['paper_count']:,} | _Multiple_ |")

    report.append("\n## Data Science Penetration\n")
    data_techniques = data['techniques'][data['techniques']['discipline'] == 'DATA']
    data_total = len(data_techniques)
    data_cross = cross_disc[cross_disc['discipline'].apply(lambda x: 'DATA' in x)]

    report.append(f"- Total DATA techniques: {data_total}")
    report.append(f"- Also used in other disciplines: {len(data_cross)} ({len(data_cross)/data_total*100:.1f}%)")
    report.append(f"- DATA-only techniques: {data_total - len(data_cross)}\n")

    report.append("### Key Discussion Points\n")
    report.append("1. **Standardization**: Should cross-discipline techniques have standardized protocols?")
    report.append("2. **Training**: What techniques need better training resources?")
    report.append("3. **Innovation Transfer**: Which techniques could benefit more disciplines?")
    report.append("4. **Collaboration**: Where are the best opportunities for interdisciplinary work?\n")

    return '\n'.join(report)

def main():
    """Main execution"""
    print("="*80)
    print("GENERATING EXPERT PANEL REPORTS")
    print("="*80)

    # Load data
    data = load_data()

    # Analyze cross-discipline patterns
    cross_disc = analyze_cross_discipline(data)

    # Generate individual discipline reports
    for disc, disc_name in DISCIPLINES.items():
        report = create_discipline_report(disc, disc_name, data, cross_disc)

        # Save markdown
        md_file = OUTPUT_DIR / f"panel_report_{disc}_{disc_name.replace(' ', '_')}.md"
        with open(md_file, 'w') as f:
            f.write(report)
        print(f"✓ Saved: {md_file}")

    # Generate cross-discipline report
    cross_report = create_cross_discipline_report(cross_disc, data)
    cross_file = OUTPUT_DIR / "panel_report_CROSS_DISCIPLINE.md"
    with open(cross_file, 'w') as f:
        f.write(cross_report)
    print(f"✓ Saved: {cross_file}")

    # Save cross-discipline data
    cross_disc_file = OUTPUT_DIR / "cross_discipline_techniques.csv"
    cross_disc.to_csv(cross_disc_file, index=False)
    print(f"✓ Saved: {cross_disc_file}")

    print("\n" + "="*80)
    print("PANEL REPORTS COMPLETE")
    print("="*80)
    print(f"\nGenerated {len(DISCIPLINES)} discipline reports + 1 cross-discipline report")
    print(f"Output directory: {OUTPUT_DIR}")
    print("\nNext step: Convert markdown to HTML using pandoc or similar tool")
    print("="*80)

if __name__ == '__main__':
    main()
