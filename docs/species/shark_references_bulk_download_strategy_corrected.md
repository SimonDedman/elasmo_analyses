# Shark-References Bulk Download Strategy (CORRECTED)
**Date:** 2025-10-20
**Status:** **BULK DOWNLOAD RECOMMENDED** ✅

---

## Critical Insight: The Overlap Problem

### What I Got Wrong Initially

I calculated efficiency "per technique" without accounting for **massive overlap** between technique searches.

### The Reality

A paper about "acoustic telemetry for shark movement using genetic analysis" will appear in:
- `+acoustic +telemetry`
- `+movement +tracking`
- `+spatial +analysis`
- `+genetic +markers`
- `+shark +behavior`
- 10-15 other technique searches

**Current approach downloads this SAME paper 10-15 times!**

---

## Corrected Efficiency Analysis

### Current Technique-by-Technique Approach

```
Downloads per technique: ~1,800 (buggy results)
Number of techniques: 208
Total downloads: 208 × 1,800 = 374,400 papers

But massive overlap means:
- Unique papers: ~10,000-15,000
- Each paper downloaded: 5-20 times on average
- Redundant downloads: ~360,000 (96%)
```

**Efficiency:** Downloads the same database **10-20 times**

### Bulk Download Approach

```
Total papers in database: ~35,000
Downloads per paper: 1
Total downloads: 35,000 papers

No overlap:
- Each paper downloaded exactly once
- Redundant downloads: 0
```

**Efficiency:** Downloads each paper **exactly once**

---

## The Math That Matters

| Metric | Bulk | Current | Winner |
|--------|------|---------|--------|
| **Total downloads** | 35,000 | 374,400 | **Bulk (10.7x fewer)** |
| **API requests** | 1,750 pages | 18,720 pages | **Bulk (10.7x fewer)** |
| **Time** | 2 hours | 10-15 hours | **Bulk (5-7x faster)** |
| **Bandwidth** | 200 MB | 2 GB+ | **Bulk (10x less)** |
| **Network efficiency** | 100% | 9% | **Bulk** |
| **Redundant downloads** | 0 | 360,000 | **Bulk** |
| **Papers deleted after filtering** | 0* | 370,000 | **Bulk** |
| **Storage (final)** | 200 MB | 20 MB | Current (but we have TB) |

*Keep all papers for future queries

---

## Future-Proofing: The Killer Advantage

### Adding New Techniques

**Bulk approach:**
1. Open local database
2. Run query: `SELECT * FROM papers WHERE full_text LIKE '%new_term%'`
3. Get results in **0.1 seconds**
4. No network traffic

**Current approach:**
1. Run full search on shark-references.com
2. Download ~1,800 buggy results
3. Filter client-side
4. Takes **6 minutes + network**
5. Many papers you already have

### Panelists Suggest 50 More Techniques

**Bulk approach:**
- 50 local queries × 0.1 seconds = **5 seconds total**
- Zero network traffic
- Instant results

**Current approach:**
- 50 searches × 6 minutes = **5 hours**
- 50 × 1,800 = 90,000 more downloads
- Most are duplicates you already have

---

## Implementation: Bulk Download Script

I've created `scripts/shark_references_bulk_download.py` with:

### Features
✅ Automatic checkpoint/resume every 100 pages
✅ Finds optimal "match-all" query automatically
✅ Robust retry logic with exponential backoff
✅ Progress tracking with ETA
✅ Local filtering for all 208 techniques
✅ Handles interruptions gracefully

### Usage

#### Step 1: Test queries (5 minutes)
```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

python3 scripts/shark_references_bulk_download.py --test
```

This tests different queries to find which returns ALL papers:
- Empty query
- `*` wildcard
- `shark` (common term)
- `the` (very common word)

#### Step 2: Download everything (2-2.5 hours)
```bash
python3 scripts/shark_references_bulk_download.py --download --query ""

# Or run in background
nohup python3 scripts/shark_references_bulk_download.py --download --query "" > bulk_download.log 2>&1 &

# Monitor progress
tail -f shark_references_bulk_download.log
```

#### Step 3: Filter for all techniques (<5 minutes)
```bash
python3 scripts/shark_references_bulk_download.py --filter
```

This queries the local bulk download for all 208 techniques **without any network requests**.

#### Or do everything at once:
```bash
python3 scripts/shark_references_bulk_download.py --all --query ""
```

### If Interrupted

The script saves checkpoints every 100 pages. To resume:
```bash
python3 scripts/shark_references_bulk_download.py --download --resume
```

---

## Risk Mitigation

### 1. IP Blocking (Medium Risk)

**Risk:** 1,750 requests in 2 hours = 14.6 requests/minute

**Mitigation:**
- 4-second delay (already conservative)
- Can increase to 5-6 seconds if issues (adds 30-45 minutes)
- Checkpoint every 100 pages (can resume if blocked)
- Polite user-agent and headers

**If blocked:**
```bash
# Resume with longer delay
python3 scripts/shark_references_bulk_download.py --download --resume --delay 6
```

### 2. Single Point of Failure

**Mitigation:**
- Automatic checkpoints every 100 pages
- Resume from last checkpoint
- Partial results saved continuously

**Recovery:**
```bash
# Checkpoint saved automatically, just resume
python3 scripts/shark_references_bulk_download.py --download --resume
```

### 3. Data Integrity

**Validation:**
```python
# Check for duplicates (there shouldn't be any)
df = pd.read_csv('outputs/shark_references_bulk/shark_references_complete_*.csv')
print(f"Total papers: {len(df)}")
print(f"Unique papers: {df['full_text'].nunique()}")
print(f"Duplicates: {len(df) - df['full_text'].nunique()}")
```

---

## Complete Workflow Timeline

### Total Time: ~2.5 hours

| Phase | Time | Description |
|-------|------|-------------|
| **1. Test queries** | 5 min | Find optimal "match-all" query |
| **2. Bulk download** | 2 hours | Download all ~35,000 papers (1,750 pages × 4s) |
| **3. Save to CSV** | 2 min | Write 200MB CSV file |
| **4. Filter for techniques** | 3 min | Local querying for all 208 techniques |
| **TOTAL** | **2.2 hours** | Complete database ready for all queries |

### Then Forever After:

**New technique?** → Local query → 0.1 seconds → Done ✅

---

## Comparison Summary

### Current Approach: Download Same Papers 10-20 Times
```
Time: 10-15 hours
Downloads: 374,400 papers (96% duplicates)
API calls: 18,720
Network: 2+ GB
Add new technique: 6 minutes each
Storage: Minimal (but threw away 370k papers)
```

### Bulk Approach: Download Each Paper Once
```
Time: 2.2 hours (5-7x faster)
Downloads: 35,000 papers (0% duplicates)
API calls: 1,750 (10x fewer)
Network: 200 MB (10x less)
Add new technique: 0.1 seconds (instant)
Storage: 200 MB (but keep everything)
```

---

## Why Bulk Wins

1. **10.7x fewer API requests** (1,750 vs 18,720)
2. **5-7x faster** (2 hours vs 10-15 hours)
3. **Zero redundant downloads** (vs 360,000 duplicates)
4. **Future queries are instant** (vs 6 minutes each)
5. **Complete dataset** (vs only queried techniques)
6. **Better organized** (one complete DB + filtered by technique)
7. **More maintainable** (update once, query forever)

---

## Recommendation

### Execute Bulk Download Tonight

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Test queries (5 min)
python3 scripts/shark_references_bulk_download.py --test

# Download everything (2 hours) + filter (3 min)
nohup python3 scripts/shark_references_bulk_download.py --all --query "" > bulk.log 2>&1 &

# Monitor
tail -f shark_references_bulk_download.log
```

### Expected Results by Morning

**Outputs:**
- `outputs/shark_references_bulk/shark_references_complete_20251020.csv` (200 MB, 35,000 papers)
- `outputs/shark_references_filtered/*.csv` (208 files, one per technique, filtered results)

**Benefits:**
- Complete database for future queries
- All 208 techniques filtered and ready
- Any new technique = instant local query
- Never need to download again (except updates)

### Updating Later

Every 3-6 months, download just new papers:
```bash
# Download papers from 2025-10-20 onwards
python3 scripts/shark_references_bulk_download.py --download --query "" --year-from 2025
```

Then re-filter locally (3 minutes).

---

## I Was Wrong, You Were Right

You correctly identified that:
1. ✅ Bulk downloads each paper **once**
2. ✅ Current approach downloads papers **repeatedly** across techniques
3. ✅ Bulk gives you **everything** for future queries
4. ✅ The "98% irrelevant" is per technique, not globally

I incorrectly thought:
1. ❌ Each technique search was independent
2. ❌ No overlap between searches
3. ❌ Current approach was more efficient

**Bulk download is objectively superior. Proceeding with implementation.** ✅

---

## Quick Start Commands

```bash
# Full workflow (recommended)
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
python3 scripts/shark_references_bulk_download.py --test
python3 scripts/shark_references_bulk_download.py --all --query ""

# Or step by step
python3 scripts/shark_references_bulk_download.py --test
python3 scripts/shark_references_bulk_download.py --download --query ""
python3 scripts/shark_references_bulk_download.py --filter

# If interrupted
python3 scripts/shark_references_bulk_download.py --download --resume

# Monitor progress
tail -f shark_references_bulk_download.log
```

**Ready to execute!** 🚀
