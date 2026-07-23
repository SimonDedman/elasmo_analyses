# Database Schema Fixes Applied (2025-10-26)

## Overview
During the full extraction with researcher network data, several database schema mismatches were discovered and fixed to enable complete extraction.

## Schema Issues Fixed

### 1. researcher_disciplines Table
**Issue:** Missing `first_year` and `last_year` columns

**Error:**
```
sqlite3.OperationalError: table researcher_disciplines has no column named first_year
```

**Fix Applied:**
```sql
ALTER TABLE researcher_disciplines ADD COLUMN first_year INTEGER;
ALTER TABLE researcher_disciplines ADD COLUMN last_year INTEGER;
```

**Result:** Allows tracking of temporal range of researcher activity in each discipline

---

### 2. extraction_log Table
**Issue:** Missing `authors_found` column

**Error:**
```
sqlite3.OperationalError: table extraction_log has no column named authors_found
```

**Fix Applied:**
```sql
ALTER TABLE extraction_log ADD COLUMN authors_found INTEGER DEFAULT 0;
```

**Result:** Enables logging of author extraction success rate

---

### 3. paper_authors Table
**Issue:** Missing `is_lead_author` column

**Error:**
```
sqlite3.OperationalError: no such column: is_lead_author
```

**Fix Applied:**
```sql
ALTER TABLE paper_authors ADD COLUMN is_lead_author BOOLEAN DEFAULT 0;
```

**Result:** Allows distinguishing lead authors from co-authors

---

### 4. researcher_techniques Table
**Issue:** Missing `technique_name` and `usage_count` columns

**Error:**
```
sqlite3.OperationalError: no such column: technique_name
```

**Fix Applied:**
```sql
ALTER TABLE researcher_techniques ADD COLUMN technique_name TEXT;
ALTER TABLE researcher_techniques ADD COLUMN usage_count INTEGER DEFAULT 1;
```

**Result:** Enables direct querying of researcher-technique relationships without joins

---

## Complete Updated Schemas

### researcher_disciplines
```sql
CREATE TABLE researcher_disciplines (
    researcher_discipline_id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_id INTEGER NOT NULL,
    discipline_code TEXT NOT NULL,
    discipline_name TEXT,
    paper_count INTEGER DEFAULT 0,
    is_primary_discipline BOOLEAN DEFAULT 0,
    first_year INTEGER,           -- ✅ ADDED
    last_year INTEGER,            -- ✅ ADDED
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id)
);
```

### extraction_log
```sql
CREATE TABLE extraction_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL UNIQUE,
    paper_path TEXT,
    status TEXT,
    techniques_found INTEGER,
    text_extracted_length INTEGER,
    processing_time_sec REAL,
    error_message TEXT,
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    authors_found INTEGER DEFAULT 0  -- ✅ ADDED
);
```

### paper_authors
```sql
CREATE TABLE paper_authors (
    paper_author_id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id TEXT NOT NULL,
    researcher_id INTEGER NOT NULL,
    author_order INTEGER,
    is_lead_author BOOLEAN DEFAULT 0,  -- ✅ ADDED
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id),
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id)
);
```

### researcher_techniques
```sql
CREATE TABLE researcher_techniques (
    researcher_technique_id INTEGER PRIMARY KEY AUTOINCREMENT,
    researcher_id INTEGER NOT NULL,
    technique_id INTEGER NOT NULL,
    technique_name TEXT,           -- ✅ ADDED
    first_used_year INTEGER,
    last_used_year INTEGER,
    usage_count INTEGER DEFAULT 1, -- ✅ ADDED
    FOREIGN KEY (researcher_id) REFERENCES researchers(researcher_id),
    FOREIGN KEY (technique_id) REFERENCES techniques(technique_id)
);
```

---

## Extraction Status After Fixes

**All schema issues resolved** - Full extraction now running successfully.

**Current extraction progress:**
- Processing 12,381 PDFs with 11 CPU cores
- Researcher network data being properly populated
- Expected completion: ~8-10 hours

**Tables being populated:**
- ✅ extraction_log (processing records)
- ✅ researchers (unique researcher records)
- ✅ paper_authors (author-paper links)
- ✅ researcher_disciplines (researcher specializations)
- ⏳ researcher_techniques (to be populated)
- ⏳ collaborations (to be populated)

---

## Prevention for Future

These schema issues occurred because:
1. Database schema designed before extraction script implementation
2. Column names in script didn't match initial database design
3. No schema validation before running extraction

**Recommendation:** Create database schema validation script that checks:
- All expected columns exist
- Column types match script expectations
- Foreign keys are properly defined
- Indexes exist for performance

---

**Document created:** 2025-10-26
**Status:** Schema fixes complete, extraction running successfully
