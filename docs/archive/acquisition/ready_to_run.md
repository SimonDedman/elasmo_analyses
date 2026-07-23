# Ready to Run: Tor + Sci-Hub

**Status:** ✅ Python packages installed, ready to install Tor

---

## What's Complete

✅ Python packages installed in venv:
- PySocks ✅
- stem ✅
- requests ✅ (already had)
- beautifulsoup4 ✅ (already had)
- pandas ✅ (already had)
- tqdm ✅ (already had)

✅ Scripts created:
- `scripts/download_via_scihub_tor.py` - Main downloader
- `scripts/test_single_doi_tor.py` - Test script

✅ Documentation created:
- `docs/database/tor_quick_start.md` - Quick start guide
- `docs/database/tor_setup_guide.md` - Complete guide
- `docs/database/tor_implementation_summary.md` - Overview

---

## Next: Install Tor (requires sudo)

```bash
# Install Tor
sudo apt-get update && sudo apt-get install -y tor

# Start Tor
sudo systemctl start tor

# Verify Tor is running
sudo systemctl status tor
```

---

## Then Test (3 minutes)

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Test with single DOI
./venv/bin/python scripts/test_single_doi_tor.py 10.1242/jeb.059667

# If that works, test with 10 papers
./venv/bin/python scripts/download_via_scihub_tor.py --test-mode
```

**Expected:** 70-85% success rate

---

## Then Run Full Download (overnight, ~10-20 hours)

```bash
# Background download
nohup ./venv/bin/python scripts/download_via_scihub_tor.py > logs/scihub_tor_full_download.log 2>&1 &
echo $! > logs/scihub_tor_pid.txt

# Monitor progress
tail -f logs/scihub_tor_full_download.log
```

**Expected gain:** +6,000-8,000 PDFs

---

## Quick Commands

```bash
# Check progress
wc -l logs/scihub_tor_download_log.csv

# Check success rate
./venv/bin/python << 'EOF'
import pandas as pd
log = pd.read_csv("logs/scihub_tor_download_log.csv")
s = (log['status']=='success').sum()
print(f"{s}/{len(log)} ({s/len(log)*100:.1f}%)")
EOF

# Count new PDFs
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" | wc -l

# Stop if needed
kill $(cat logs/scihub_tor_pid.txt)
```

---

**See `docs/database/tor_quick_start.md` for full instructions**
