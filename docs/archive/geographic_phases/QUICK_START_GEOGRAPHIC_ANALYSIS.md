# Geographic Analysis - Quick Start Guide

**Last Updated**: 2025-11-24

---

## Database is Ready to Use! ✅

The `technique_taxonomy.db` database now contains **6,183 papers** (50.5% of corpus) with author institution and country data.

---

## For Your Abstract (November 30)

### Summary Statistics

```
Total papers: 12,240
Papers with geographic data: 6,183 (50.5%)

Top 3 countries:
  USA:       2,137 papers (34.6%)
  Australia:   849 papers (13.7%)
  UK:          708 papers (11.5%)

Regional distribution:
  Global North: 5,485 papers (88.7%)
  Global South:   698 papers (11.3%)
```

### Recommended Abstract Text

> "Geographic analysis of 6,183 papers (50.5% of analyzed corpus) shows that 34.6% were led by institutions in the USA (n = 2,137), 13.7% in Australia (n = 849), and 11.5% in the UK (n = 708). Regional analysis reveals that 88.7% of studies were led by institutions in the Global North (high-income countries in North America, Europe, and Australia/New Zealand), while only 11.3% originated from the Global South."

---

## Quick SQL Queries

### Connect to Database

```bash
# Python
./venv/bin/python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('database/technique_taxonomy.db')
cursor = conn.cursor()

# Your queries here...
EOF
```

### Top 10 Countries

```sql
SELECT first_author_country, COUNT(*) as papers
FROM paper_geography
WHERE first_author_country IS NOT NULL
GROUP BY first_author_country
ORDER BY papers DESC
LIMIT 10;
```

### Global North vs South

```sql
SELECT first_author_region, COUNT(*) as papers,
       ROUND(COUNT(*) * 100.0 / 6183, 1) as percentage
FROM paper_geography
WHERE first_author_region IS NOT NULL
GROUP BY first_author_region;
```

### Export to CSV

```bash
./venv/bin/python3 << 'EOF'
import sqlite3
import csv

conn = sqlite3.connect('database/technique_taxonomy.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT first_author_country, COUNT(*) as papers
    FROM paper_geography
    WHERE first_author_country IS NOT NULL
    GROUP BY first_author_country
    ORDER BY papers DESC
""")

with open('outputs/country_distribution_for_abstract.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['country', 'papers'])
    writer.writerows(cursor.fetchall())

print("✓ Saved: outputs/country_distribution_for_abstract.csv")
EOF
```

---

## Documentation Files

**Essential reading**:
- `docs/DATABASE_QUERY_REFERENCE.md` - SQL query examples
- `docs/GEOGRAPHIC_ANALYSIS_COMPLETE_SUMMARY_2025-11-24.md` - Full summary

**For later (Phase 4)**:
- `docs/PHASE_4_STUDY_LOCATION_GUIDE.md` - Parachute research analysis

---

## Phase 4: Study Locations (Optional - For May 2025)

**Not needed for abstract**, but ready to execute for presentation.

### What Phase 4 Does

Extracts WHERE research was conducted (study location) vs WHERE authors are based (author institution), enabling "parachute research" analysis.

### To Execute Phase 4

```bash
# Test run (100 papers, ~5 minutes)
./venv/bin/python3 scripts/extract_study_locations_phase4.py --test --limit 100

# Full run (6,183 papers, ~2-3 hours)
./venv/bin/python3 scripts/extract_study_locations_phase4.py
```

**Recommendation**: Run AFTER abstract submission (you have time, no rush).

---

## Need Help?

**Query examples**: See `docs/DATABASE_QUERY_REFERENCE.md`

**Validation**: Database validated and matches CSV files exactly

**Questions**: All geographic data is in the `paper_geography` table

---

**Bottom Line**: Database is ready, abstract text is ready, no additional work needed for November 30. 🎉
