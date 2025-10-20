---
editor_options:
  markdown:
    wrap: 72
---

# Shark-References Species Database Extraction Guide

**Project:** EEA 2025 Data Panel - Species Database Construction
**Date Created:** 2025-10-13
**Purpose:** Document extraction workflow for comprehensive shark species data from Shark-References
**Status:** Planning Phase - Awaiting Weigmann Response

---

## Executive Summary

**Recommendation:** Use Shark-References as the primary source for the species database, with Weigmann's updated list as validation/supplementation.

**Why Shark-References?**
- ✅ **Comprehensive:** Covers all valid recent chondrichthyan species
- ✅ **Structured:** Consistent data fields across all species
- ✅ **Current:** Actively maintained and updated
- ✅ **Rich metadata:** Includes common names, distribution, taxonomy, habitat, size, biology
- ✅ **Well-organized:** Alphabetical listing with clear URLs
- ✅ **Open access:** All species information publicly available

**Current Database Requirements:**
- ~1,200 chondrichthyan species (sharks, rays, skates, chimaeras)
- Binomial nomenclature (genus + species)
- Common names (multiple per species)
- Taxonomic hierarchy (Class → Subclass → Superorder → Order → Family → Genus → Species)
- Geographic distribution
- Depth range
- Size/age data
- Habitat information

---

## 1. Shark-References Species Data Structure

### 1.1 Species List Pages

**URL Pattern:** `https://shark-references.com/species/listValidRecent/{LETTER}`

**Available Letters:** A-Z (26 pages total)

**Page Structure:**
- Alphabetical navigation at top
- List of species with brief information
- Three types of links per species:
  1. 📄 Literature link: `/literature/listBySpecies/{Genus-species}`
  2. ℹ️ Description link: Links to original description
  3. 🏠 Species page: `/species/view/{Genus-species}`

**Sample Species Entry:**
```
Acroteriobatus andysabini (Last, Séret & Naylor, 2016)
└── Literature: https://shark-references.com/literature/listBySpecies/Acroteriobatus-andysabini
└── Species page: https://shark-references.com/species/view/Acroteriobatus-andysabini
```

---

### 1.2 Species Page Fields

**URL Pattern:** `https://shark-references.com/species/view/{Genus-species}`

**Available Fields:**

#### Core Taxonomy
- **Binomial name** (e.g., *Carcharodon carcharias*)
- **Author citation** (e.g., (Linnaeus, 1758))
- **Classification hierarchy:**
  - Class (e.g., Chondrichthyes)
  - Subclass (e.g., Elasmobranchii)
  - Superorder (e.g., Selachimorpha, Batoidea, or Holocephali)
  - Order (e.g., Lamniformes)
  - Family (e.g., Lamnidae)
  - Genus (e.g., *Carcharodon*)
  - Species (e.g., *carcharias*)

#### Nomenclature
- **Reference of original description** (bibliographic citation)
- **Image of original description** (PDF/image links)
- **Synonyms / new combinations and misspellings** (historical names)
- **Types** (holotype, paratype information)
- **Citation format** (how to cite the species)

#### Common Names
- **Common names by language:**
  - 🇩🇪 German (deu)
  - 🇬🇧 English (eng)
  - 🇪🇸 Spanish (spa)
  - 🇫🇷 French (fra)
  - 🇮🇹 Italian (ita)
  - 🇵🇹 Portuguese (por)
  - Other languages as available

**Example (Carcharodon carcharias):**
- English: Great white shark, White pointer, White shark, Man-eater
- German: Weißer Hai, Weißhai, Menschenhai
- Spanish: Tiburón blanco, Jaquetón blanco
- French: Grand requin blanc, Requin blanc
- (50+ common names total)

#### Biology & Ecology
- **Short Description** (species overview)
- **Distribution** (geographic range by ocean basin)
- **Habitat** (depth range, habitat type)
- **Size / Weight / Age** (maximum size, weight, age)
- **Biology** (reproductive mode, diet, behavior)
- **Human uses** (fisheries, conservation status)

#### Additional Information
- **Remarks** (taxonomic notes, special information)
- **Parasites** (curated parasite list)
- **Image gallery** (photos of species)

---

## 2. Database Schema Requirements

### 2.1 Required Fields (from Database_Schema_Design.md)

Based on the project's database schema design (line 382-448), we need:

```sql
-- Species columns (prefix: sp_)
-- Format: sp_{genus}_{species} (lowercase, underscores)
sp_carcharodon_carcharias BOOLEAN DEFAULT FALSE  -- White shark
sp_prionace_glauca BOOLEAN DEFAULT FALSE         -- Blue shark
sp_rhincodon_typus BOOLEAN DEFAULT FALSE         -- Whale shark
-- ... (~1,200 species total)
```

**Column naming convention:**
- All lowercase
- Genus + species separated by underscore
- No special characters
- Prefix: `sp_`

**Example transformations:**
- *Carcharodon carcharias* → `sp_carcharodon_carcharias`
- *Prionace glauca* → `sp_prionace_glauca`
- *Acroteriobatus andysabini* → `sp_acroteriobatus_andysabini`

### 2.2 Lookup Tables Required

#### Species Taxonomy Lookup
```sql
CREATE TABLE species_taxonomy (
    species_binomial VARCHAR(100) PRIMARY KEY,
    genus VARCHAR(50),
    family VARCHAR(50),
    order_name VARCHAR(50),
    superorder VARCHAR(50),  -- Selachimorpha, Batoidea, Holocephali
    subclass VARCHAR(50),
    class VARCHAR(50),
    author_citation VARCHAR(255),
    common_name_primary VARCHAR(100),  -- Most common English name
    common_names_all TEXT,  -- All common names (comma-separated)
    distribution TEXT,
    depth_min INTEGER,
    depth_max INTEGER,
    max_length_cm INTEGER,
    max_weight_kg REAL,
    max_age_years INTEGER,
    habitat TEXT,
    biology TEXT,
    shark_refs_url VARCHAR(255),
    date_extracted DATE
);
```

#### Common Names Lookup (for searching)
```sql
CREATE TABLE species_common_names (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species_binomial VARCHAR(100) REFERENCES species_taxonomy(species_binomial),
    common_name VARCHAR(100),
    language_code VARCHAR(3),  -- ISO 639-3 (eng, spa, fra, deu, etc.)
    language_flag VARCHAR(50)   -- For display purposes
);
```

---

## 3. Extraction Workflow Options

### Option A: Automated Web Scraping (RECOMMENDED)

**Advantages:**
- ✅ Complete data extraction (all fields)
- ✅ Consistent data structure
- ✅ Reproducible and updatable
- ✅ Can extract all 1,200+ species efficiently
- ✅ Captures common names in multiple languages

**Disadvantages:**
- ⚠️ Requires permission from Shark-References maintainers
- ⚠️ Needs rate limiting (10-15 sec between requests)
- ⚠️ HTML parsing can break if site structure changes

**Implementation:**

#### Step 1: Extract Species List (26 pages)

```python
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_species_list(letter):
    """
    Extract all species starting with given letter

    Args:
        letter: A-Z

    Returns:
        List of dicts with species name and URL
    """
    url = f"https://shark-references.com/species/listValidRecent/{letter}"

    print(f"Fetching species list for letter: {letter}")
    response = requests.get(url)

    if response.status_code != 200:
        print(f"ERROR: Failed to fetch {url}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all species links (pattern: /species/view/Genus-species)
    species_links = soup.find_all('a', href=lambda x: x and '/species/view/' in x)

    species_list = []
    for link in species_links:
        href = link['href']
        # Extract binomial from URL: /species/view/Genus-species
        binomial = href.split('/species/view/')[-1]

        # Convert URL format to proper binomial
        # Genus-species → Genus species
        genus, species = binomial.split('-', 1)
        proper_binomial = f"{genus} {species}"

        species_list.append({
            'binomial': proper_binomial,
            'binomial_url': binomial,
            'url': f"https://shark-references.com{href}",
            'genus': genus,
            'species': species
        })

    # Rate limiting
    time.sleep(10)

    return species_list

# Extract all species
all_species = []
for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    species = get_species_list(letter)
    all_species.extend(species)
    print(f"Letter {letter}: {len(species)} species")

# Save species list
species_df = pd.DataFrame(all_species)
species_df.to_csv('data/shark_references_species_list.csv', index=False)
print(f"\nTotal species extracted: {len(all_species)}")
```

#### Step 2: Extract Detailed Species Information

```python
def extract_species_details(species_url, binomial):
    """
    Extract all fields from species page

    Args:
        species_url: Full URL to species page
        binomial: Species binomial name

    Returns:
        Dictionary with all extracted fields
    """
    print(f"Extracting details for: {binomial}")

    response = requests.get(species_url)
    if response.status_code != 200:
        print(f"ERROR: Failed to fetch {species_url}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Initialize data dictionary
    data = {
        'binomial': binomial,
        'url': species_url
    }

    # Extract classification (taxonomy hierarchy)
    classification = soup.find('span', class_='label', string='Classification: ')
    if classification:
        # Parse taxonomy from following elements
        # (implementation depends on exact HTML structure)
        pass

    # Extract author citation
    # Usually in the species title or citation section

    # Extract common names
    common_names_section = soup.find('span', class_='label', string='Common names')
    if common_names_section:
        # Parse common names with language flags
        # Format: <img src="/images/flags/gb.gif" alt="eng" /> Great white shark
        common_names = []
        names_div = common_names_section.find_next('br').next_sibling

        # Extract all <img> flag + name pairs
        # (implementation depends on exact HTML structure)

        data['common_names'] = common_names

    # Extract distribution
    distribution_section = soup.find('span', class_='label', string='Distribution')
    if distribution_section:
        data['distribution'] = distribution_section.find_next('div').text.strip()

    # Extract size/weight/age
    size_section = soup.find('span', class_='label', string='Size / Weight / Age')
    if size_section:
        data['size_weight_age'] = size_section.find_next('div').text.strip()

    # Extract habitat
    habitat_section = soup.find('span', class_='label', string='Habitat')
    if habitat_section:
        data['habitat'] = habitat_section.find_next('div').text.strip()

    # Extract biology
    biology_section = soup.find('span', class_='label', string='Biology')
    if biology_section:
        data['biology'] = biology_section.find_next('div').text.strip()

    # Rate limiting (10-15 seconds)
    time.sleep(12)

    return data

# Process all species
species_df = pd.read_csv('data/shark_references_species_list.csv')

detailed_data = []
for idx, row in species_df.iterrows():
    details = extract_species_details(row['url'], row['binomial'])
    if details:
        detailed_data.append(details)

    # Progress logging
    if (idx + 1) % 10 == 0:
        print(f"Processed {idx + 1}/{len(species_df)} species")
        # Save intermediate results
        temp_df = pd.DataFrame(detailed_data)
        temp_df.to_csv('data/shark_species_detailed_temp.csv', index=False)

# Save final results
final_df = pd.DataFrame(detailed_data)
final_df.to_csv('data/shark_species_detailed_complete.csv', index=False)
```

#### Step 3: Parse and Clean Data

```python
import re

def parse_size_data(size_text):
    """
    Extract numerical size/weight/age data from text

    Example input: "Maximum total length at least 600 cm. Maximum weight 1900 kg. Maximum age 70 years."

    Returns:
        dict with max_length_cm, max_weight_kg, max_age_years
    """
    data = {
        'max_length_cm': None,
        'max_weight_kg': None,
        'max_age_years': None
    }

    # Extract length (cm or m)
    length_match = re.search(r'(\d+\.?\d*)\s*(cm|m)\b', size_text, re.IGNORECASE)
    if length_match:
        value = float(length_match.group(1))
        unit = length_match.group(2).lower()
        if unit == 'm':
            value *= 100  # Convert to cm
        data['max_length_cm'] = int(value)

    # Extract weight (kg or g)
    weight_match = re.search(r'(\d+\.?\d*)\s*(kg|g)\b', size_text, re.IGNORECASE)
    if weight_match:
        value = float(weight_match.group(1))
        unit = weight_match.group(2).lower()
        if unit == 'g':
            value /= 1000  # Convert to kg
        data['max_weight_kg'] = value

    # Extract age (years)
    age_match = re.search(r'(\d+\.?\d*)\s*years?\b', size_text, re.IGNORECASE)
    if age_match:
        data['max_age_years'] = int(float(age_match.group(1)))

    return data

def parse_depth_data(habitat_text):
    """
    Extract depth range from habitat text

    Example: "Depth range 0-1280 m"

    Returns:
        dict with depth_min, depth_max
    """
    data = {
        'depth_min': None,
        'depth_max': None
    }

    # Pattern: 0-1280 m or 0 to 1280 m
    depth_match = re.search(r'(\d+)\s*[-–to]\s*(\d+)\s*m', habitat_text, re.IGNORECASE)
    if depth_match:
        data['depth_min'] = int(depth_match.group(1))
        data['depth_max'] = int(depth_match.group(2))

    return data

def parse_common_names(common_names_html):
    """
    Extract common names with language codes

    Returns:
        List of dicts with {language_code, language_flag, common_name}
    """
    soup = BeautifulSoup(common_names_html, 'html.parser')

    names = []

    # Find all flag images
    flags = soup.find_all('img', src=lambda x: x and '/images/flags/' in x)

    for flag in flags:
        language_code = flag['alt']  # e.g., "eng", "spa", "deu (T)"
        language_code = language_code.split()[0]  # Remove " (T)" if present

        # Get text following this flag until next flag or end
        name_text = ''
        for sibling in flag.next_siblings:
            if sibling.name == 'img':
                break  # Next flag found
            if isinstance(sibling, str):
                name_text += sibling

        name_text = name_text.strip(' ,')

        if name_text:
            names.append({
                'language_code': language_code,
                'common_name': name_text
            })

    return names

# Process and clean all data
species_df = pd.read_csv('data/shark_species_detailed_complete.csv')

# Parse size/weight/age
if 'size_weight_age' in species_df.columns:
    size_data = species_df['size_weight_age'].apply(parse_size_data)
    species_df['max_length_cm'] = size_data.apply(lambda x: x['max_length_cm'])
    species_df['max_weight_kg'] = size_data.apply(lambda x: x['max_weight_kg'])
    species_df['max_age_years'] = size_data.apply(lambda x: x['max_age_years'])

# Parse depth range
if 'habitat' in species_df.columns:
    depth_data = species_df['habitat'].apply(parse_depth_data)
    species_df['depth_min'] = depth_data.apply(lambda x: x['depth_min'])
    species_df['depth_max'] = depth_data.apply(lambda x: x['depth_max'])

# Save cleaned data
species_df.to_csv('data/shark_species_cleaned.csv', index=False)
```

---

### Option B: Semi-Automated (Hybrid Approach)

**Best for:** If full automation is not permitted or feasible

**Workflow:**
1. Use automated script to extract species list only (26 pages)
2. Manual review of sample species pages to refine parsing
3. Automated extraction of common fields (name, taxonomy)
4. Manual extraction of complex fields (common names, biology)
5. Combine with existing `species_common_lookup.csv` (1,030 species)

**Implementation:**

```python
# Extract species list only
species_list = []
for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    species = get_species_list(letter)
    species_list.extend(species)

species_df = pd.DataFrame(species_list)
species_df.to_csv('data/shark_references_species_urls.csv', index=False)

# Load existing common names
existing_names = pd.read_csv('data/species_common_lookup_cleaned.csv')

# Merge and identify gaps
merged = species_df.merge(
    existing_names,
    left_on='binomial',
    right_on='Species',
    how='left',
    indicator=True
)

# Species with common names already (no need to scrape)
already_have = merged[merged['_merge'] == 'both']
print(f"Already have common names for: {len(already_have)} species")

# Species missing common names (need to scrape)
need_to_scrape = merged[merged['_merge'] == 'left_only']
print(f"Need to scrape: {len(need_to_scrape)} species")

need_to_scrape.to_csv('data/species_to_scrape.csv', index=False)
```

---

### Option C: Manual Extraction + CSV Import

**Best for:** Small-scale or if automation not permitted

**Workflow:**
1. Open each letter page in browser
2. Copy species list to spreadsheet
3. Manually visit key species pages
4. Copy/paste relevant fields
5. Clean and format in Excel/LibreOffice

**Time estimate:** ~40-60 hours for 1,200 species

---

## 4. Data Integration Workflow

### 4.1 Compare with Existing Data

```python
import pandas as pd

# Load Shark-References extracted data
shark_refs = pd.read_csv('data/shark_species_cleaned.csv')

# Load existing species_common_lookup (1,030 species)
existing = pd.read_csv('data/species_common_lookup_cleaned.csv')

# Load Weigmann species list (when received)
# weigmann = pd.read_csv('data/weigmann_2016_species_checklist_cleaned.csv')

# Compare species lists
shark_refs['binomial_clean'] = shark_refs['binomial'].str.lower().str.replace(' ', '_')
existing['binomial_clean'] = existing['Species'].str.lower().str.replace(' ', '_')

# Find species in Shark-Refs but not in existing list
new_species = shark_refs[~shark_refs['binomial_clean'].isin(existing['binomial_clean'])]
print(f"New species from Shark-References: {len(new_species)}")

# Find species in existing list but not in Shark-Refs
missing_species = existing[~existing['binomial_clean'].isin(shark_refs['binomial_clean'])]
print(f"Species in existing list but not Shark-Refs: {len(missing_species)}")

# Save comparison results
new_species.to_csv('data/species_new_from_sharkrefs.csv', index=False)
missing_species.to_csv('data/species_missing_from_sharkrefs.csv', index=False)
```

### 4.2 Create Master Species Database

```python
# Merge all sources
master_species = shark_refs.merge(
    existing,
    left_on='binomial_clean',
    right_on='binomial_clean',
    how='outer',
    suffixes=('_sharkrefs', '_existing')
)

# Prioritize Shark-Refs data where available, fall back to existing
master_species['binomial_final'] = master_species['binomial_sharkrefs'].fillna(
    master_species['Species']
)

# Select best common name (English)
# Prioritize Shark-Refs English common name
master_species['common_name_primary'] = master_species.apply(
    lambda row: extract_english_name(row['common_names'])
                if pd.notna(row['common_names'])
                else row['Common'],
    axis=1
)

# Save master database
master_species.to_csv('data/species_master_database.csv', index=False)
```

### 4.3 Generate SQL Species Columns

```python
# Generate SQL ALTER statements for database schema
master = pd.read_csv('data/species_master_database.csv')

# Create column names: sp_{genus}_{species}
master['column_name'] = master['binomial_final'].str.lower().str.replace(' ', '_')
master['column_name'] = 'sp_' + master['column_name']

# Generate SQL
sql_statements = []
for idx, row in master.iterrows():
    sql = f"ALTER TABLE literature_review ADD COLUMN IF NOT EXISTS {row['column_name']} BOOLEAN DEFAULT FALSE; -- {row['binomial_final']} ({row['common_name_primary']})"
    sql_statements.append(sql)

# Write to file
with open('sql/06_add_species_columns.sql', 'w') as f:
    f.write("-- Species columns for literature_review table\n")
    f.write(f"-- Generated: {pd.Timestamp.now()}\n")
    f.write(f"-- Total species: {len(sql_statements)}\n\n")
    f.write('\n'.join(sql_statements))

print(f"Generated SQL for {len(sql_statements)} species")
```

---

## 5. Implementation Recommendations

### 5.1 Recommended Approach (Hybrid)

**Phase 1: Quick Start (Today)**
1. ✅ Use existing `species_common_lookup_cleaned.csv` (1,030 species)
2. ✅ Generate SQL species columns with current data
3. ✅ This unblocks database setup (Task I1.11)

**Phase 2: Shark-References Integration (This Week)**
1. Contact Shark-References maintainers for permission
   - Email: info@shark-references.com
   - Explain project scope (academic research, not commercial)
   - Request permission for automated species list extraction
   - Propose conservative rate limiting (10-15 sec delays)
2. Extract species list from 26 alphabetical pages
3. Compare with existing 1,030 species
4. Identify ~170-200 missing species

**Phase 3: Gap Filling (Next Week)**
1. Wait for Weigmann's response (ETA: any day)
2. Cross-reference three sources:
   - Shark-References species list
   - Existing species_common_lookup (1,030)
   - Weigmann updated list
3. For missing species:
   - Extract from Shark-References (automated)
   - OR add manually from Weigmann list
   - OR use FishBase as fallback

**Phase 4: Full Extraction (Optional - Long-term)**
1. If Shark-Refs approves automation:
   - Extract detailed data for all species
   - Create comprehensive species taxonomy table
   - Add to database as lookup tables
2. If not approved:
   - Use current 1,030 species + Weigmann additions
   - Manually add critical missing species
   - Defer comprehensive extraction to future work

### 5.2 Prioritization Strategy

**Critical (Must Have):**
- ✅ Binomial names (genus + species)
- ✅ Primary common name (English)
- ✅ Taxonomic hierarchy (Superorder → Order → Family)

**Important (Should Have):**
- Common names in multiple languages
- Geographic distribution
- Depth range

**Nice to Have:**
- Size/weight/age data
- Detailed biology text
- Habitat descriptions
- Original description references

### 5.3 Timeline Estimate

**Automated extraction (if approved):**
- Species list extraction: 30 min (26 pages × 10 sec)
- Detailed extraction: 4-5 hours (1,200 species × 12 sec)
- Data parsing/cleaning: 2-3 hours
- **Total: 6-8 hours**

**Semi-automated extraction:**
- Species list: 30 min
- Sample species testing: 1 hour
- Targeted extraction (200 missing): 1 hour
- Manual additions: 2-3 hours
- **Total: 4-5 hours**

**Manual extraction:**
- 1,200 species × 2 min = 40 hours
- **Not recommended**

---

## 6. Integration with Existing Project Structure

### 6.1 Files to Create

```
data/
├── shark_references_species_list.csv          # Species list (26 pages)
├── shark_references_species_detailed.csv      # Full extraction (if approved)
├── species_master_database.csv                # Merged from all sources
└── species_taxonomy_lookup.csv                # Final taxonomy table

sql/
└── 06_add_species_columns.sql                 # Generated SQL (updated)

scripts/
├── extract_shark_references_species.py        # Python extraction script
├── extract_shark_references_species.R         # R alternative script
└── merge_species_sources.R                    # Merge Shark-Refs + existing + Weigmann

docs/
└── Shark_References_Species_Database_Extraction.md  # This document
```

### 6.2 Updated TODO.md Tasks

**Update Task I1.3:**
```markdown
| I1.3 | Extract species list from Shark-References | Assistant | 🔄 | 🔴 | I2.1 |
Primary source, supplement with Weigmann when received |
```

**Add new tasks:**
```markdown
| I1.13 | Contact Shark-References for species extraction permission | SD | ⏳ | 🔴 | - |
Email info@shark-references.com |

| I1.14 | Compare Shark-Refs species with existing 1,030 species | Assistant | ⏳ | 🟡 | I1.13 |
Identify ~170-200 gaps |

| I1.15 | Extract missing species from Shark-References | Assistant | ⏳ | 🟡 | I1.14 |
Automated or semi-automated |
```

### 6.3 Updated Database Schema

Add to `species_taxonomy` table:
```sql
ALTER TABLE species_taxonomy ADD COLUMN shark_refs_url VARCHAR(255);
ALTER TABLE species_taxonomy ADD COLUMN shark_refs_id VARCHAR(50);
ALTER TABLE species_taxonomy ADD COLUMN data_source VARCHAR(50);  -- 'SharkRefs', 'Weigmann', 'FishBase', 'Manual'
ALTER TABLE species_taxonomy ADD COLUMN date_extracted DATE;
ALTER TABLE species_taxonomy ADD COLUMN extraction_method VARCHAR(50);  -- 'automated', 'semi-automated', 'manual'
```

---

## 7. Risk Assessment & Mitigation

### 7.1 Potential Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Shark-Refs denies automation permission | Low | Medium | Use semi-automated for species list only, manual for gaps |
| Website structure changes during extraction | Low | Medium | Save intermediate results, implement error handling |
| Missing species not in Shark-References | Medium | Low | Cross-reference with Weigmann + FishBase |
| Common names inconsistent across sources | High | Low | Prioritize Shark-Refs, document conflicts |
| Extraction takes longer than expected | Medium | Low | Start with species list only, defer full extraction |

### 7.2 Contingency Plans

**If Shark-References denies automation:**
- Use existing 1,030 species immediately
- Manually add ~170 missing species from Weigmann
- Defer comprehensive extraction to manual future work

**If Weigmann never responds:**
- Proceed with Shark-References + existing data
- Use FishBase R package for validation
- Document species source in database

**If extraction reveals major taxonomy conflicts:**
- Prioritize most recent source (Shark-References likely most current)
- Document conflicts in `species_taxonomy` table remarks field
- Consult taxonomic experts if critical discrepancies found

---

## 8. Next Steps & Action Items

### Immediate Actions (Today)

1. ✅ **Use existing data to unblock project**
   ```bash
   # Generate SQL with current 1,030 species
   Rscript scripts/generate_species_sql.R
   ```

2. **Contact Shark-References**
   ```
   To: info@shark-references.com
   Subject: Permission Request - Academic Species Database Extraction

   Dear Shark-References Team,

   I am working on an academic research project for the European Elasmobranch Association
   (EEA) 2025 conference, conducting a systematic literature review of elasmobranch research
   across 8 scientific disciplines.

   I would like to request permission to extract your comprehensive species list via automated
   script (https://shark-references.com/species/listValidRecent/A-Z). The extraction would:
   - Be limited to species list pages only (26 alphabetical pages)
   - Use conservative rate limiting (10-15 seconds between requests)
   - Run during off-peak hours
   - Be a one-time extraction for project initialization

   The data will be used to create a species lookup table for our literature database,
   properly crediting Shark-References as the source. The project is non-commercial and
   results will be published open-access.

   Would you be willing to grant permission for this extraction? I am happy to adjust the
   approach to meet any requirements or restrictions you may have.

   Thank you for maintaining this invaluable resource!

   Best regards,
   [Your name and affiliation]
   ```

### This Week

3. **Test single-page extraction**
   - Manually verify CSV format from one letter page
   - Test parsing logic on sample species
   - Refine extraction script

4. **Compare sources**
   - Load Shark-Refs species list (when extracted)
   - Compare with existing 1,030 species
   - Identify gaps and discrepancies

### Next Week

5. **Integrate Weigmann data** (when received)
   - Cross-reference all three sources
   - Create master species database
   - Regenerate SQL species columns

6. **Update database schema**
   - Add ~170-200 missing species columns
   - Update species_taxonomy lookup table
   - Run database migration scripts

---

## 9. References & Resources

**Shark-References Website:**
- Main site: https://shark-references.com
- Species list: https://shark-references.com/species/listValidRecent/{A-Z}
- Search manual: https://shark-references.com/images/meine_bilder/downloads/Manual_Advanced_Search_Shark_references_english_version.pdf
- Contact: info@shark-references.com

**Project Documentation:**
- Database Schema: `docs/Database_Schema_Design.md`
- Weigmann Status: `docs/Weigmann_Extraction_Status.md`
- Species Lookup Analysis: `docs/Species_Lookup_Analysis_Summary.md`
- Shark-Refs Automation: `docs/Shark_References_Automation_Workflow.md`

**Alternative Sources:**
- FishBase: https://www.fishbase.org/ (R package: `rfishbase`)
- Sharkipedia: https://www.sharkipedia.org/ (contact pending)
- ITIS (taxonomy validation): https://www.itis.gov/

**Taxonomic Standards:**
- Weigmann 2016: "Annotated checklist of the living sharks, batoids and chimaeras"
- Last et al. (ongoing): Systematic revisions in Zootaxa, Cybium, etc.

---

## 10. Conclusion

**Shark-References provides the ideal source for the species database** due to its comprehensive coverage, structured data, and active maintenance. The site's alphabetical species listing and consistent page structure make it well-suited for automated extraction.

**Recommended immediate action:** Use existing 1,030 species to unblock database setup, then contact Shark-References for permission to extract the complete species list. Cross-reference with Weigmann's updated list (when received) to ensure completeness.

**Expected outcome:** Master species database with 1,200+ chondrichthyan species, including binomial names, common names, taxonomic hierarchy, and basic ecological data—meeting all requirements for the EEA 2025 Data Panel project.

---

*Document created: 2025-10-13*
*Status: Awaiting Shark-References permission + Weigmann response*
*Next review: After receiving responses*
