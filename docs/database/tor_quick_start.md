# Tor Quick Start Guide

**Goal:** Download ~8,000 missing PDFs via Sci-Hub through Tor network

---

## Quick Setup (5 commands)

```bash
# 1. Install Tor
sudo apt-get update && sudo apt-get install -y tor

# 2. Install Python packages (using existing venv)
./venv/bin/pip install PySocks stem
# Note: requests, beautifulsoup4, pandas, tqdm already installed

# 3. Start Tor
sudo systemctl start tor

# 4. Test Tor + Sci-Hub (with a known DOI)
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
./venv/bin/python scripts/test_single_doi_tor.py 10.1242/jeb.059667

# 5. If test succeeds, run test with 10 papers
./venv/bin/python scripts/download_via_scihub_tor.py --test-mode
```

---

## What to Expect

### Test with 10 Papers (Step 5)
- **Time:** 1-2 minutes
- **Expected success rate:** 70-85%
- **If <60% success:** Try different mirror or troubleshoot

### Full Download (11,858 papers)
- **Time:** 10-20 hours (can run overnight)
- **Expected:** 8,000-10,000 successful downloads
- **Size:** 15-25 GB

---

## Full Download Command

```bash
# Run in background (continues even if you disconnect)
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
nohup ./venv/bin/python scripts/download_via_scihub_tor.py > logs/scihub_tor_full_download.log 2>&1 &

# Save process ID for later
echo $! > logs/scihub_tor_pid.txt

# Monitor progress
tail -f logs/scihub_tor_full_download.log
```

---

## Monitor Progress

```bash
# Check how many processed
wc -l logs/scihub_tor_download_log.csv

# Check success rate
./venv/bin/python << 'EOF'
import pandas as pd
log = pd.read_csv("logs/scihub_tor_download_log.csv")
success = (log['status'] == 'success').sum()
print(f"Processed: {len(log):,}")
print(f"Success: {success:,} ({success/len(log)*100:.1f}%)")
EOF

# Count new PDFs
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" | wc -l
```

---

## Troubleshooting

### Test fails with "Tor connection test failed"
```bash
# Check Tor status
sudo systemctl status tor

# Restart Tor
sudo systemctl restart tor

# Check if port 9050 is listening
sudo netstat -tulpn | grep 9050
```

### Test fails with "ERROR" response
```bash
# Try different mirror
python3 scripts/test_single_doi_tor.py 10.1242/jeb.059667

# If all mirrors fail, restart Tor
sudo systemctl restart tor

# Wait 30 seconds, try again
sleep 30
python3 scripts/test_single_doi_tor.py 10.1242/jeb.059667
```

### Download is very slow
**Normal:** 6-10 papers per minute via Tor
**If slower:** Check Tor status and network connection

### Stop download
```bash
# Kill the process
kill $(cat logs/scihub_tor_pid.txt)

# Resume later (will skip already downloaded)
python3 scripts/download_via_scihub_tor.py --resume
```

---

## Success Metrics

✅ **Good:**
- Test success rate: >70%
- Download speed: 6-10 papers/minute
- No repeated "ERROR" responses
- PDFs are valid (not HTML)

⚠️ **Needs attention:**
- Test success rate: 40-70% (try different mirror)
- Many "forbidden" errors (restart Tor)
- Many "timeout" errors (increase timeout in script)

❌ **Failed:**
- Test success rate: <40%
- All mirrors return "ERROR"
- No PDFs downloading

---

## Expected Outcome

**Before:** 5,414 PDFs (18% of 30,000)
**After:** ~13,400 PDFs (45% of 30,000)
**Gain:** +8,000 PDFs

---

## Full Documentation

See `docs/database/tor_setup_guide.md` for complete details.

---

## Quick Commands Reference

```bash
# Test Tor connection
./venv/bin/python scripts/test_single_doi_tor.py 10.1242/jeb.059667

# Test with 10 papers
./venv/bin/python scripts/download_via_scihub_tor.py --test-mode

# Full download
./venv/bin/python scripts/download_via_scihub_tor.py

# Full download (background)
nohup ./venv/bin/python scripts/download_via_scihub_tor.py > logs/scihub_tor_full_download.log 2>&1 &

# Monitor progress
tail -f logs/scihub_tor_full_download.log

# Check success rate
python3 -c "import pandas as pd; log=pd.read_csv('logs/scihub_tor_download_log.csv'); print(f\"Success: {(log['status']=='success').sum()}/{len(log)} ({(log['status']=='success').sum()/len(log)*100:.1f}%)\")"

# Stop download
kill $(cat logs/scihub_tor_pid.txt)

# Resume download
./venv/bin/python scripts/download_via_scihub_tor.py --resume
```

---

**Ready?** Start with Step 1 (install Tor) and work through the steps!
