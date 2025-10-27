#!/usr/bin/env python3
"""
Analyze EEA 2025 Conference Abstracts
Contextualizes each presentation against recent shark research (2020-2025)
Generates productive comments and questions
Links to panel/attendee expertise
"""

import pandas as pd
import duckdb
from pathlib import Path
import re
from docx import Document
import PyPDF2
from collections import defaultdict
import datetime

# Configuration
ABSTRACTS_DIR = Path("abstracts")
OUTPUT_DIR = Path("outputs/abstract_reviews")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

DB_PATH = "outputs/literature_review.duckdb"

# Technique keywords for matching (from our 8 disciplines)
DISCIPLINE_KEYWORDS = {
    'BEH': ['behavior', 'behaviour', 'video analysis', 'BORIS', 'social network',
            'dominance', 'operant', 'learning', 'ethogram', 'focal sampling'],
    'BIO': ['parasit', 'morphometric', 'metabolic', 'body measurement', 'maturity',
            'length-frequency', 'mortality', 'reproductive', 'fecundity', 'telomere'],
    'CON': ['tourism', 'vulnerability', 'IUCN', 'stakeholder', 'MPA', 'valuation',
            'policy', 'socioeconomic', 'education', 'outreach', 'conservation'],
    'DATA': ['time series', 'GLM', 'meta-analysis', 'GAM', 'MCMC', 'cross-validation',
             'machine learning', 'GAMM', 'neural network', 'Bayesian', 'random forest',
             'deep learning', 'CNN', 'SVM', 'INLA', 'data fusion'],
    'FISH': ['stock assessment', 'post-release', 'mortality', 'discard', 'ecosystem model',
             'yield', 'age-structured', 'bycatch', 'CPUE', 'fisher interview', 'catch',
             'VPA', 'distance sampling', 'spawning'],
    'GEN': ['STRUCTURE', 'phylogenetic', 'genomic', 'population genetics', 'DNA barcoding',
            'mtDNA', 'conservation genetics', 'ADMIXTURE', 'SNP', 'eDNA', 'LAMP',
            'metabarcoding', 'comparative genomics', 'relatedness', 'transcriptom',
            'DAPC', 'ancient DNA', 'genome sequencing', 'forensics', 'FST'],
    'MOV': ['connectivity', 'critical habitat', 'network analysis', 'MaxEnt',
            'kernel density', 'state-space', 'hidden Markov', 'MCP', 'MPA design',
            'habitat model', 'species distribution', 'Brownian bridge', 'home range',
            'Marxan', 'movement model', 'ensemble', 'spatial prioritization'],
    'TRO': ['stable isotope', 'foraging', 'stomach content', 'prey selection',
            'niche partitioning', 'diet analysis', 'NMDS', 'food web', 'energy flow',
            'fatty acid', 'optimal foraging', 'SIAR', 'DNA metabarcoding',
            'ecosystem role', 'trophic level', 'IsoSpace']
}

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            full_text = []
            for page in pdf_reader.pages:
                full_text.append(page.extract_text())
            return '\n'.join(full_text)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""

def parse_filename(filename):
    """Extract presentation type, number, and author from filename"""
    # Pattern: O_XX or P_XX for oral/poster
    match = re.match(r'^([OP])_?(\d+)', filename)
    pres_type = None
    pres_num = None

    if match:
        pres_type = 'Oral' if match.group(1) == 'O' else 'Poster'
        pres_num = int(match.group(2))
    elif filename.startswith('P') and filename[1:3].isdigit():
        pres_type = 'Poster'
        pres_num = int(filename[1:3])
    elif filename.startswith('Poster'):
        pres_type = 'Poster'

    # Extract author name (usually after underscores)
    author = None
    parts = filename.replace('.docx', '').replace('.pdf', '').split('_')
    for part in parts:
        if any(name_word in part.lower() for name_word in ['abstract', 'form', 'eea2025', 'presentation', 'poster']):
            continue
        if len(part) > 2 and not part.isdigit():
            author = part.replace('-', ' ')
            break

    return pres_type, pres_num, author

def identify_disciplines(text):
    """Identify which disciplines are relevant to this abstract"""
    text_lower = text.lower()
    disciplines = []

    for disc, keywords in DISCIPLINE_KEYWORDS.items():
        # Count keyword matches
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        if matches > 0:
            disciplines.append((disc, matches))

    # Sort by number of matches
    disciplines.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in disciplines[:3]]  # Top 3 disciplines

def load_attendee_data():
    """Load attendee list with expertise"""
    df = pd.read_excel('eea_2025_attendee_list.xlsx')

    # Create lookup dictionaries
    attendees = {}
    for _, row in df.iterrows():
        name = f"{row['Name (First)']} {row['Name (Last)']}"
        attendees[name] = {
            'email': row['Email'],
            'organization': row['Organisation / Institute'],
            'discipline_gt': row['Discipline (GT Review)'],
            'discipline_8cat': row['Discipline (8-category)'],
            'presenting': row['presenting'],
            'poster': row['poster'],
            'panel': row['panel']
        }

    return attendees

def query_recent_literature(disciplines, keywords, start_year=2020):
    """Query database for recent papers in relevant disciplines"""
    try:
        con = duckdb.connect(DB_PATH, read_only=True)

        # Build keyword search string
        keyword_str = '|'.join(keywords[:10])  # Top 10 keywords

        query = f"""
        SELECT
            p.title,
            p.authors,
            p.year,
            p.journal,
            p.doi,
            t.technique_name,
            t.primary_discipline
        FROM papers p
        LEFT JOIN paper_techniques t ON p.paper_id = t.paper_id
        WHERE p.year >= {start_year}
        AND (
            LOWER(p.title) LIKE ANY (['%{kw.lower()}%' for kw in keywords[:10]])
            OR t.primary_discipline IN ({','.join(["'" + d + "'" for d in disciplines])})
        )
        ORDER BY p.year DESC, p.title
        LIMIT 50
        """

        results = con.execute(query).fetchdf()
        con.close()
        return results
    except Exception as e:
        print(f"Database query error: {e}")
        return pd.DataFrame()

def find_relevant_attendees(disciplines, attendees):
    """Find attendees with expertise in the relevant disciplines"""
    relevant = []

    for name, info in attendees.items():
        # Check if attendee works in any of the relevant disciplines
        if pd.notna(info['discipline_8cat']):
            attendee_disc = info['discipline_8cat']
            # Match first part before comma
            attendee_disc_short = attendee_disc.split('.')[0].strip()

            # Map 8-category to our codes
            disc_map = {
                '1': 'BIO',
                '2': 'GEN',
                '3': 'MOV',
                '4': 'TRO',
                '5': 'FISH',
                '6': 'CON',
                '7': 'BEH',
                '8': 'DATA'
            }

            mapped_disc = disc_map.get(attendee_disc_short)
            if mapped_disc in disciplines:
                relevant.append({
                    'name': name,
                    'organization': info['organization'],
                    'discipline': attendee_disc,
                    'panel': info['panel'],
                    'presenting': info['presenting']
                })

    return relevant

def generate_discussion_questions(abstract_text, disciplines, recent_papers):
    """Generate productive discussion questions"""
    questions = []

    # Discipline-specific questions
    if 'DATA' in disciplines:
        questions.append("**Data Science Methods**: Which statistical/ML techniques are you using? "
                        "Have you considered cross-validation or ensemble approaches?")

    if 'GEN' in disciplines:
        questions.append("**Genetics**: What sequencing platform/depth are you using? "
                        "Have you considered population structure effects?")

    if 'MOV' in disciplines:
        questions.append("**Movement**: How are you handling detection gaps and autocorrelation? "
                        "What spatial scale are you analyzing?")

    if 'TRO' in disciplines:
        questions.append("**Trophic Ecology**: How are you accounting for isotopic fractionation? "
                        "Have you validated diet estimates?")

    if 'FISH' in disciplines:
        questions.append("**Fisheries**: What stock assessment framework are you using? "
                        "How are you handling data-poor scenarios?")

    if 'CON' in disciplines:
        questions.append("**Conservation**: How are you integrating stakeholder input? "
                        "What management recommendations emerge?")

    if 'BEH' in disciplines:
        questions.append("**Behaviour**: How are you controlling for observer bias? "
                        "What sample size did you achieve?")

    if 'BIO' in disciplines:
        questions.append("**Biology**: What validation methods are you using? "
                        "How do your findings compare to congeners?")

    # General questions
    questions.append("**Broader Context**: How does this work connect to other disciplines "
                    "(e.g., conservation, fisheries management)?")

    if len(recent_papers) > 0:
        questions.append(f"**Recent Developments**: {len(recent_papers)} related papers published "
                        f"since 2020 - how does your work build on or differ from recent findings?")

    return questions

def create_abstract_review(filename, text, attendees):
    """Create comprehensive review for one abstract"""

    # Parse filename
    pres_type, pres_num, author = parse_filename(filename)

    # Identify disciplines
    disciplines = identify_disciplines(text)

    # Extract keywords from abstract
    # Simple approach: common technique-related words
    words = re.findall(r'\b\w{4,}\b', text.lower())
    word_freq = defaultdict(int)
    for word in words:
        word_freq[word] += 1
    keywords = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:15]

    # Query recent literature
    recent_papers = query_recent_literature(disciplines, keywords) if disciplines else pd.DataFrame()

    # Find relevant attendees
    relevant_attendees = find_relevant_attendees(disciplines, attendees)

    # Generate questions
    questions = generate_discussion_questions(text, disciplines, recent_papers)

    # Build markdown report
    report = []
    report.append(f"# Abstract Review: {filename}")
    report.append(f"\n**Date**: {datetime.date.today()}")
    report.append(f"**Type**: {pres_type or 'Unknown'}")
    if pres_num:
        report.append(f"**Number**: {pres_num}")
    if author:
        report.append(f"**Author**: {author}")

    report.append("\n---\n")

    # Abstract text
    report.append("## Abstract\n")
    report.append("```")
    report.append(text[:1000] + ("..." if len(text) > 1000 else ""))
    report.append("```\n")

    report.append("---\n")

    # Discipline classification
    report.append("## Discipline Classification\n")
    if disciplines:
        disc_names = {
            'BEH': 'Behaviour', 'BIO': 'Biology', 'CON': 'Conservation',
            'DATA': 'Data Science', 'FISH': 'Fisheries', 'GEN': 'Genetics',
            'MOV': 'Movement', 'TRO': 'Trophic Ecology'
        }
        report.append("**Primary disciplines**: " + ", ".join([disc_names.get(d, d) for d in disciplines]))
    else:
        report.append("**Unable to classify** - no clear discipline keywords detected")

    report.append("\n**Keywords detected**: " + ", ".join(keywords[:10]))

    report.append("\n\n---\n")

    # Recent literature context
    report.append("## Recent Literature Context (2020-2025)\n")
    if len(recent_papers) > 0:
        report.append(f"\n**Found {len(recent_papers)} related papers** from the shark research database:\n")

        # Group by year
        for year in sorted(recent_papers['year'].unique(), reverse=True):
            year_papers = recent_papers[recent_papers['year'] == year]
            report.append(f"\n### {int(year)} ({len(year_papers)} papers)\n")
            for _, paper in year_papers.head(10).iterrows():
                report.append(f"- **{paper['title']}**")
                if pd.notna(paper['authors']):
                    # Truncate author list
                    authors = str(paper['authors'])[:100]
                    report.append(f"  - {authors}{'...' if len(str(paper['authors'])) > 100 else ''}")
                if pd.notna(paper['technique_name']):
                    report.append(f"  - Technique: {paper['technique_name']}")
                if pd.notna(paper['journal']):
                    report.append(f"  - Journal: {paper['journal']}")
                report.append("")
    else:
        report.append("\n*No recent papers found in database for these keywords/disciplines*")
        report.append("\n**Note**: This may indicate:")
        report.append("- Novel research direction")
        report.append("- Keywords not matching database terminology")
        report.append("- Interdisciplinary work bridging multiple fields\n")

    report.append("---\n")

    # Relevant attendees
    report.append("## Relevant Panel Members & Attendees\n")
    if relevant_attendees:
        report.append(f"\n**{len(relevant_attendees)} attendees** with expertise in these disciplines:\n")

        # Panel members first
        panel = [a for a in relevant_attendees if a['panel']]
        if panel:
            report.append("\n### Panel Members\n")
            for att in panel:
                report.append(f"- **{att['name']}** - {att['organization']}")
                report.append(f"  - Discipline: {att['discipline']}")
                report.append("")

        # Other presenters
        presenters = [a for a in relevant_attendees if a['presenting'] and not a['panel']]
        if presenters:
            report.append("\n### Other Presenters in Related Fields\n")
            for att in presenters[:10]:
                report.append(f"- **{att['name']}** - {att['organization']}")
                report.append(f"  - Discipline: {att['discipline']}")
                report.append("")
    else:
        report.append("\n*No direct discipline matches found in attendee list*\n")

    report.append("---\n")

    # Discussion questions
    report.append("## Productive Discussion Questions\n")
    for i, q in enumerate(questions, 1):
        report.append(f"\n{i}. {q}\n")

    report.append("\n---\n")

    # Recommendations
    report.append("## Recommendations for Session\n")
    report.append("### Connections to Highlight\n")

    if 'DATA' in disciplines and len(disciplines) > 1:
        report.append("- **Cross-discipline data science**: Emphasize how modern analytical methods "
                     "are penetrating this field")

    if len(recent_papers) > 0:
        report.append(f"- **Recent developments**: Reference the {len(recent_papers)} related papers "
                     f"published since 2020")

    if len(relevant_attendees) > 5:
        report.append(f"- **Networking opportunity**: {len(relevant_attendees)} attendees working "
                     f"in related areas")

    report.append("\n### Potential Collaborations\n")
    if len(disciplines) > 1:
        report.append(f"- This work bridges {', '.join(disciplines)} - excellent opportunity "
                     "for interdisciplinary discussion")

    report.append("\n### Areas Needing Clarification\n")
    report.append("- _To be filled in during presentation_")

    report.append("\n---\n")
    report.append(f"\n*Review generated: {datetime.date.today()}*")
    report.append(f"\n*Based on {len(recent_papers)} database papers and {len(attendees)} conference attendees*")

    return '\n'.join(report)

def main():
    """Main execution"""
    print("="*80)
    print("EEA 2025 ABSTRACT ANALYSIS")
    print("="*80)

    # Load attendee data
    print("\nLoading attendee list...")
    attendees = load_attendee_data()
    print(f"✓ Loaded {len(attendees)} attendees")

    # Find all abstracts
    print("\nScanning abstracts directory...")
    abstract_files = list(ABSTRACTS_DIR.glob("*.docx")) + list(ABSTRACTS_DIR.glob("*.pdf"))
    # Filter out non-abstract files
    abstract_files = [f for f in abstract_files if not f.name.startswith('Abstract-submission')
                     and not f.name.startswith('EEA2025 bursaries')]

    print(f"✓ Found {len(abstract_files)} abstract files")

    # Process each abstract
    print("\nProcessing abstracts...")
    for i, filepath in enumerate(abstract_files, 1):
        print(f"\n[{i}/{len(abstract_files)}] Processing: {filepath.name}")

        # Extract text
        if filepath.suffix == '.docx':
            text = extract_text_from_docx(filepath)
        elif filepath.suffix == '.pdf':
            text = extract_text_from_pdf(filepath)
        else:
            print(f"  ⚠ Skipping unknown file type: {filepath.suffix}")
            continue

        if not text or len(text) < 50:
            print(f"  ⚠ No text extracted or text too short")
            continue

        print(f"  ✓ Extracted {len(text)} characters")

        # Create review
        review = create_abstract_review(filepath.name, text, attendees)

        # Save review
        output_file = OUTPUT_DIR / f"review_{filepath.stem}.md"
        with open(output_file, 'w') as f:
            f.write(review)

        print(f"  ✓ Saved review: {output_file.name}")

    # Create summary report
    print("\n" + "="*80)
    print("CREATING SUMMARY REPORT")
    print("="*80)

    summary = []
    summary.append("# EEA 2025 Abstract Reviews - Summary")
    summary.append(f"\n**Generated**: {datetime.date.today()}")
    summary.append(f"**Total abstracts processed**: {len(abstract_files)}")
    summary.append(f"**Total attendees**: {len(attendees)}\n")

    summary.append("## Individual Reviews\n")
    summary.append("Each abstract has been analyzed and contextualized against:\n")
    summary.append("- Recent shark research literature (2020-2025)")
    summary.append("- Relevant panel members and attendees")
    summary.append("- Applicable research techniques and methods\n")

    summary.append("## Review Files\n")
    for filepath in sorted(OUTPUT_DIR.glob("review_*.md")):
        summary.append(f"- [{filepath.name}]({filepath.name})")

    summary.append("\n## Usage\n")
    summary.append("1. Review each abstract analysis before the session")
    summary.append("2. Note the discussion questions provided")
    summary.append("3. Identify relevant panel members for targeted questions")
    summary.append("4. Reference recent literature during discussions\n")

    summary_file = OUTPUT_DIR / "ABSTRACT_REVIEWS_SUMMARY.md"
    with open(summary_file, 'w') as f:
        f.write('\n'.join(summary))

    print(f"\n✓ Summary saved: {summary_file}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nProcessed {len(abstract_files)} abstracts")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"\nReview files created: {len(list(OUTPUT_DIR.glob('review_*.md')))}")
    print("="*80)

if __name__ == '__main__':
    main()
