# Temporal Analysis SQL Queries - Parachute Research

**Purpose**: Analyze parachute research trends over time (1990-2024)
**Database**: `database/technique_taxonomy.db`
**Tables**: `paper_geography`, `extraction_log`

---

## Quick Access Queries

### 1. Global North/South Parachute Research Trends Over Time

```sql
SELECT e.year,
       p.first_author_region,
       COUNT(*) as total_papers,
       SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) as parachute_papers,
       ROUND(100.0 * SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as parachute_pct
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_study_location = 1
  AND e.year >= 1990
GROUP BY e.year, p.first_author_region
ORDER BY e.year, p.first_author_region;
```

**Expected output**:
```
year | first_author_region | total_papers | parachute_papers | parachute_pct
-----|---------------------|--------------|------------------|---------------
1990 | Global North        | 45           | 18               | 40.0
1990 | Global South        | 3            | 1                | 33.3
1991 | Global North        | 52           | 22               | 42.3
...
```

**Use case**: Track if parachute research rate has changed over time. Expected pattern: may decrease in recent years due to more local capacity building.

---

### 2. Top 10 Countries - Parachute Research Over Time

```sql
SELECT e.year,
       p.first_author_country,
       COUNT(*) as parachute_papers
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.is_parachute_research = 1
  AND e.year >= 1990
  AND p.first_author_country IN (
      'USA', 'Australia', 'UK', 'Canada', 'Germany',
      'Japan', 'France', 'Spain', 'Italy', 'Netherlands'
  )
GROUP BY e.year, p.first_author_country
ORDER BY e.year, p.first_author_country;
```

**Use case**: Identify which countries have increased or decreased parachute research activity over time.

---

### 3. North → South Parachute Research Patterns

```sql
SELECT p.first_author_country,
       p.study_country,
       COUNT(*) as papers,
       MIN(e.year) as first_year,
       MAX(e.year) as latest_year,
       ROUND(AVG(e.year), 1) as avg_year
FROM paper_geography p
JOIN extraction_log e ON p.paper_id = e.paper_id
WHERE p.is_parachute_research = 1
  AND p.first_author_region = 'Global North'
  AND p.study_country IN (
      -- Global South countries with shark research
      SELECT DISTINCT first_author_country
      FROM paper_geography
      WHERE first_author_region = 'Global South'
  )
GROUP BY p.first_author_country, p.study_country
HAVING COUNT(*) >= 5
ORDER BY papers DESC;
```

**Expected patterns**:
- USA → Mexico (high count, recent years)
- USA → Ecuador (high count, focus on Galapagos)
- Australia → Indonesia (moderate count)
- UK → South Africa (moderate count)

**Use case**: Identify most common "parachute research corridors" from Global North to Global South.

---

### 4. Domestic vs Parachute Research Over Time

```sql
SELECT e.year,
       COUNT(CASE WHEN p.is_parachute_research = 0 THEN 1 END) as domestic_papers,
       COUNT(CASE WHEN p.is_parachute_research = 1 THEN 1 END) as parachute_papers,
       ROUND(100.0 * COUNT(CASE WHEN p.is_parachute_research = 1 THEN 1 END) / COUNT(*), 1) as parachute_pct
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_study_location = 1
  AND e.year >= 1990
GROUP BY e.year
ORDER BY e.year;
```

**Use case**: Overall trend analysis - is parachute research increasing or decreasing?

---

### 5. Top 5 Studied Countries (Sinks) Over Time

```sql
WITH sink_countries AS (
    SELECT study_country
    FROM paper_geography
    WHERE is_parachute_research = 1
    GROUP BY study_country
    ORDER BY COUNT(*) DESC
    LIMIT 5
)
SELECT e.year,
       p.study_country,
       COUNT(*) as foreign_studies
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.is_parachute_research = 1
  AND p.study_country IN (SELECT study_country FROM sink_countries)
  AND e.year >= 1990
GROUP BY e.year, p.study_country
ORDER BY e.year, p.study_country;
```

**Use case**: Track if major "sink" countries (e.g., Mexico, Ecuador, Bahamas) are still being heavily studied by foreign researchers, or if local capacity is growing.

---

### 6. Specific Country Pair Analysis (USA → Mexico Example)

```sql
SELECT e.year,
       COUNT(*) as papers,
       GROUP_CONCAT(p.paper_id, '; ') as paper_ids
FROM paper_geography p
JOIN extraction_log e ON p.paper_id = p.paper_id
WHERE p.first_author_country = 'USA'
  AND p.study_country = 'Mexico'
  AND e.year >= 1990
GROUP BY e.year
ORDER BY e.year;
```

**Use case**: Detailed analysis of a specific parachute research corridor.

---

### 7. Parachute Research by Ocean Basin Over Time

```sql
SELECT e.year,
       p.study_ocean_basin,
       COUNT(*) as parachute_papers
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.is_parachute_research = 1
  AND p.study_ocean_basin IS NOT NULL
  AND e.year >= 1990
GROUP BY e.year, p.study_ocean_basin
ORDER BY e.year, p.study_ocean_basin;
```

**Use case**: Identify which ocean basins have more parachute research activity.

---

### 8. Decadal Analysis (1990-2024)

```sql
SELECT CASE
           WHEN e.year BETWEEN 1990 AND 1999 THEN '1990-1999'
           WHEN e.year BETWEEN 2000 AND 2009 THEN '2000-2009'
           WHEN e.year BETWEEN 2010 AND 2019 THEN '2010-2019'
           WHEN e.year BETWEEN 2020 AND 2029 THEN '2020-2024'
       END as decade,
       p.first_author_region,
       COUNT(*) as total_papers,
       SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) as parachute_papers,
       ROUND(100.0 * SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as parachute_pct
FROM extraction_log e
JOIN paper_geography p ON e.paper_id = p.paper_id
WHERE p.has_study_location = 1
  AND e.year >= 1990
GROUP BY decade, p.first_author_region
ORDER BY decade, p.first_author_region;
```

**Use case**: High-level decadal trends for presentation.

---

## Python Script to Execute Queries

```python
#!/usr/bin/env python3
import sqlite3
import csv
from pathlib import Path

DB_PATH = Path("database/technique_taxonomy.db")
OUTPUT_DIR = Path("outputs/temporal_analysis")
OUTPUT_DIR.mkdir(exist_ok=True)

def run_query(query_name, sql_query, output_filename):
    """Execute SQL query and save results to CSV."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(sql_query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    # Save to CSV
    output_path = OUTPUT_DIR / output_filename
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(results)

    conn.close()
    print(f"✓ {query_name}: {len(results):,} rows → {output_path}")

# Run all queries
run_query(
    "Global North/South Trends",
    """SELECT e.year, p.first_author_region, COUNT(*) as total_papers,
       SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) as parachute_papers,
       ROUND(100.0 * SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as parachute_pct
       FROM extraction_log e
       JOIN paper_geography p ON e.paper_id = p.paper_id
       WHERE p.has_study_location = 1 AND e.year >= 1990
       GROUP BY e.year, p.first_author_region
       ORDER BY e.year, p.first_author_region;""",
    "temporal_global_north_south.csv"
)

run_query(
    "Top 10 Countries Over Time",
    """SELECT e.year, p.first_author_country, COUNT(*) as parachute_papers
       FROM extraction_log e
       JOIN paper_geography p ON e.paper_id = p.paper_id
       WHERE p.is_parachute_research = 1 AND e.year >= 1990
       AND p.first_author_country IN ('USA', 'Australia', 'UK', 'Canada', 'Germany',
                                       'Japan', 'France', 'Spain', 'Italy', 'Netherlands')
       GROUP BY e.year, p.first_author_country
       ORDER BY e.year, p.first_author_country;""",
    "temporal_top10_countries.csv"
)

run_query(
    "North → South Patterns",
    """SELECT p.first_author_country, p.study_country, COUNT(*) as papers,
       MIN(e.year) as first_year, MAX(e.year) as latest_year, ROUND(AVG(e.year), 1) as avg_year
       FROM paper_geography p
       JOIN extraction_log e ON p.paper_id = e.paper_id
       WHERE p.is_parachute_research = 1
       AND p.first_author_region = 'Global North'
       AND p.study_country IN (SELECT DISTINCT first_author_country FROM paper_geography WHERE first_author_region = 'Global South')
       GROUP BY p.first_author_country, p.study_country
       HAVING COUNT(*) >= 5
       ORDER BY papers DESC;""",
    "north_to_south_patterns.csv"
)

run_query(
    "Domestic vs Parachute Over Time",
    """SELECT e.year,
       COUNT(CASE WHEN p.is_parachute_research = 0 THEN 1 END) as domestic_papers,
       COUNT(CASE WHEN p.is_parachute_research = 1 THEN 1 END) as parachute_papers,
       ROUND(100.0 * COUNT(CASE WHEN p.is_parachute_research = 1 THEN 1 END) / COUNT(*), 1) as parachute_pct
       FROM extraction_log e
       JOIN paper_geography p ON e.paper_id = p.paper_id
       WHERE p.has_study_location = 1 AND e.year >= 1990
       GROUP BY e.year ORDER BY e.year;""",
    "temporal_domestic_vs_parachute.csv"
)

run_query(
    "Decadal Analysis",
    """SELECT CASE
           WHEN e.year BETWEEN 1990 AND 1999 THEN '1990-1999'
           WHEN e.year BETWEEN 2000 AND 2009 THEN '2000-2009'
           WHEN e.year BETWEEN 2010 AND 2019 THEN '2010-2019'
           WHEN e.year BETWEEN 2020 AND 2029 THEN '2020-2024'
       END as decade,
       p.first_author_region,
       COUNT(*) as total_papers,
       SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) as parachute_papers,
       ROUND(100.0 * SUM(CASE WHEN p.is_parachute_research = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as parachute_pct
       FROM extraction_log e
       JOIN paper_geography p ON e.paper_id = p.paper_id
       WHERE p.has_study_location = 1 AND e.year >= 1990
       GROUP BY decade, p.first_author_region
       ORDER BY decade, p.first_author_region;""",
    "decadal_analysis.csv"
)

print("\n✓ All temporal analyses complete!")
print(f"Results saved to: {OUTPUT_DIR}/")
```

---

## Expected Patterns (Hypotheses)

### Global North vs South

**Hypothesis**: Parachute research rate higher for Global North than Global South

**Expected results**:
- Global North parachute rate: 20-25% (researchers often study abroad)
- Global South parachute rate: 5-10% (researchers often study locally)

### Temporal Trends

**Hypothesis**: Parachute research rate has DECREASED over time (more local capacity)

**Expected results**:
- 1990-1999: ~50-55% parachute research (low local capacity)
- 2000-2009: ~48-52% (capacity building begins)
- 2010-2019: ~42-46% (more local institutions)
- 2020-2024: ~38-42% (increased collaboration)

### Top Parachute Corridors

**Hypothesis**: USA → Latin America and Australia → SE Asia are dominant patterns

**Expected top 5 corridors**:
1. USA → Mexico (Guadalupe Island white sharks)
2. USA → Ecuador (Galapagos hammerheads)
3. Australia → Indonesia (whale sharks)
4. USA → Bahamas (tiger sharks, lemon sharks)
5. UK → South Africa (white shark cage diving)

---

## Visualization Ideas (For May 2025 Presentation)

### 1. Line Plot - Parachute Research Rate Over Time
- X-axis: Year (1990-2024)
- Y-axis: Parachute research percentage
- Lines: Global North (blue) vs Global South (orange)
- **Message**: Has parachute research decreased?

### 2. Stacked Bar Chart - Domestic vs Parachute by Decade
- X-axis: Decade
- Y-axis: Number of papers
- Stacks: Domestic (green) vs Parachute (red)
- **Message**: Growth of local research capacity

### 3. Heatmap - Top Country Pairs Over Time
- Rows: Source countries (USA, UK, Australia, etc.)
- Columns: Sink countries (Mexico, Ecuador, Indonesia, etc.)
- Color intensity: Number of parachute papers
- **Message**: Geographic patterns in parachute research

### 4. Network Diagram - Parachute Research Flows
- Nodes: Countries (size = total papers)
- Edges: Parachute research flows (thickness = number of papers)
- Colors: Global North (blue) vs Global South (orange)
- **Message**: Visualize North → South research dominance

---

## Abstract Text (Add After FIXED Results)

**Current abstract paragraph** (author country data):
> "Geographic analysis of 6,183 papers (50.5% of analyzed corpus) shows that 34.6% were led by institutions in the USA (n = 2,137), 13.7% in Australia (n = 849), and 11.5% in the UK (n = 708). Regional analysis reveals that 88.7% of studies were led by institutions in the Global North (high-income countries in North America, Europe, and Australia/New Zealand), while only 11.3% originated from the Global South."

**Add parachute research paragraph** (after FIXED Phase 4):
> "Analysis of study locations (n = [TOTAL] papers with extractable field sites) identified parachute research patterns in approximately [%] of papers (n = [COUNT]), where author institution country differed from study location country. Major 'sink' countries (study locations with disproportionately low local research capacity) include [TOP 3], while major 'source' countries (researchers predominantly studying abroad) include [TOP 3]. Temporal analysis (1990-2024) reveals [TREND: increasing/decreasing/stable] parachute research rates over time."

---

**Generated**: 2025-11-24
**Status**: Ready to execute after Phase 4 FIXED completion
**Estimated execution time**: <5 minutes (all queries combined)
