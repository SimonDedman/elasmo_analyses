# Download Scripts Guide

## Overview
Multiple scripts are available for acquiring PDFs from various sources. All scripts support dry-run mode for testing.

## Available Scripts

### 1. **download_pdfs_from_database.py** - Primary Script
**Purpose**: Download papers with DOIs from database

**Usage**:
```bash
./venv/bin/python scripts/download_pdfs_from_database.py
```

**Sources**: Uses DOI resolution → publisher sites
**Status**: ✅ Ready to run
**Output**: PDFs saved to configured directory

---

### 2. **download_oa_papers_only.py** - Open Access Only
**Purpose**: Download only open access papers

**Usage**:
```bash
./venv/bin/python scripts/download_oa_papers_only.py
```

**Benefits**: No paywall issues, faster, ethical
**Status**: ✅ Ready to run

---

### 3. **download_theses_multisource.py** - Grey Literature
**Purpose**: Download theses/dissertations without DOIs

**Sources**:
- Google Scholar
- OATD.org (Open Access Theses & Dissertations)
- Institutional repositories

**Usage**:
```bash
./venv/bin/python scripts/download_theses_multisource.py
```

**Note**: Respectful rate limiting built-in
**Status**: ✅ Ready to run
**See also**: `docs/database/THESIS_DOWNLOADER_SUMMARY.md`

---

### 4. **download_via_scihub.py** / **download_via_scihub_tor.py**
**Purpose**: Download via Sci-Hub (use responsibly)

**WARNING**: Legal/ethical considerations apply
- Only use for papers you have legitimate access to
- Tor version provides anonymity
- See `docs/database/scihub_diagnosis.md`

**Status**: ⚠️ Use with caution

---

### 5. **download_from_academia.py** / **download_from_researchgate.py**
**Purpose**: Download from academic social networks

**Requirements**:
- Valid account credentials
- Cookies exported from browser

**Usage**:
```bash
# First, export cookies using extract_firefox_cookies.py
./venv/bin/python scripts/extract_firefox_cookies.py

# Then run download
./venv/bin/python scripts/download_from_academia.py
```

**Status**: ✅ Ready (requires setup)
**See**: `docs/database/firefox_cookie_export_guide.md`

---

### 6. **download_semantic_dois_via_scihub.py**
**Purpose**: Use Semantic Scholar API to find DOIs, then download

**Benefits**: Finds DOIs for papers missing them
**Status**: ✅ Ready to run

---

### 7. **download_iucn_assessments.py**
**Purpose**: Download IUCN Red List assessments

**Usage**:
```bash
./venv/bin/python scripts/download_iucn_assessments.py
```

**Status**: ✅ Ready to run

---

### 8. **retrieve_papers_multisource.py**
**Purpose**: Orchestrator script - tries multiple sources

**Usage**:
```bash
./venv/bin/python scripts/retrieve_papers_multisource.py
```

**Status**: ✅ Ready to run - Recommended for batch downloads

---

## Download Strategy

### Recommended Order:
1. **Start with OA**: `download_oa_papers_only.py`
2. **Try database**: `download_pdfs_from_database.py`
3. **Grey literature**: `download_theses_multisource.py`
4. **Multisource**: `retrieve_papers_multisource.py`
5. **Social networks**: Academia/ResearchGate (if needed)

### Monitoring Progress:
- Logs saved to `logs/` directory
- Check status: `ls -lh logs/*.csv`
- Monitor commands in: `docs/database/monitoring_commands.md`

## Related Documentation

- **Setup**: `docs/database/MANUAL_DOWNLOAD_GUIDE.md`
- **Strategies**: `docs/database/grey_literature_acquisition_strategy.md`
- **Workarounds**: `docs/database/RATE_LIMITING_WORKAROUNDS.md`
- **Cookies**: `docs/database/firefox_cookie_export_guide.md`
- **Tor Setup**: `docs/database/tor_setup_guide.md`

## Common Issues

### Rate Limiting
**Solution**: Scripts have built-in delays. If blocked:
- Increase delays in script configuration
- Use Tor version
- Space out download sessions

### Missing DOIs
**Solution**: Use `download_theses_multisource.py` or Semantic Scholar script

### Paywalls
**Solutions**:
1. Check if OA version available
2. Use institutional access
3. Try ResearchGate/Academia.edu
4. Request from authors

## Dry Run Testing

All scripts support `--dry-run`:
```bash
./venv/bin/python scripts/download_oa_papers_only.py --dry-run
```

This shows what would be downloaded without actually downloading.

---

*Last Updated: 2025-10-26*
*All scripts located in: `scripts/`*
