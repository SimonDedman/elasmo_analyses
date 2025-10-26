# Tor Implementation Summary

**Date:** 2025-10-23
**Purpose:** Bypass Sci-Hub IP blocking to acquire ~8,000 missing PDFs
**Status:** ✅ Ready for implementation

---

## What Was Created

### 1. Main Tor-Enabled Downloader
**File:** `scripts/download_via_scihub_tor.py`

**Features:**
- Routes all requests through Tor SOCKS proxy (port 9050)
- Automatic Tor identity rotation every 100 successful downloads
- User-Agent rotation to appear more human-like
- Retries failed papers from previous Sci-Hub run
- Robust error handling and logging
- Resume capability (skips already processed papers)
- Progress saving every 50 papers

**Key Improvements over original:**
- ✅ IP blocking bypass via Tor
- ✅ Identity rotation to avoid cumulative blocking
- ✅ Targets only previously failed papers (not re-downloading successes)
- ✅ More conservative delays (5 seconds vs 3 seconds)
- ✅ Better error detection and recovery

---

### 2. Single DOI Test Script
**File:** `scripts/test_single_doi_tor.py`

**Purpose:** Quick verification that Tor + Sci-Hub is working

**Usage:**
```bash
python3 scripts/test_single_doi_tor.py 10.1242/jeb.059667
```

**Tests:**
1. Tor proxy configuration
2. Tor connection (checks IP)
3. Sci-Hub access via Tor
4. PDF extraction from multiple mirrors
5. Provides recommendations for best mirror

---

### 3. Documentation

#### Complete Setup Guide
**File:** `docs/database/tor_setup_guide.md` (1,300+ lines)

**Contents:**
- Step-by-step installation instructions
- Tor configuration and testing
- Troubleshooting for common issues
- Monitoring commands
- Success criteria
- Advanced identity rotation
- Cleanup instructions

#### Quick Start Guide
**File:** `docs/database/tor_quick_start.md` (150+ lines)

**Contents:**
- 5-command quick setup
- Essential commands only
- Quick troubleshooting
- Progress monitoring
- Success metrics

---

## Implementation Steps

### Phase 1: Setup (10-15 minutes)

```bash
# 1. Install Tor
sudo apt-get update && sudo apt-get install -y tor

# 2. Install Python dependencies
pip install PySocks stem requests beautifulsoup4 pandas tqdm

# 3. Start Tor service
sudo systemctl start tor

# 4. Verify Tor is running
sudo systemctl status tor
sudo netstat -tulpn | grep 9050  # Should show Tor listening
```

---

### Phase 2: Testing (5-10 minutes)

```bash
# Navigate to project
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Test 1: Single DOI
python3 scripts/test_single_doi_tor.py 10.1242/jeb.059667

# Expected: Success with one of the mirrors
# If all fail: sudo systemctl restart tor, wait 30s, try again

# Test 2: 10-paper sample
python3 scripts/download_via_scihub_tor.py --test-mode

# Expected: 70-85% success rate
# If <60%: Try different mirror or troubleshoot
```

---

### Phase 3: Full Download (10-20 hours)

```bash
# Run in background
nohup python3 scripts/download_via_scihub_tor.py > logs/scihub_tor_full_download.log 2>&1 &

# Save process ID
echo $! > logs/scihub_tor_pid.txt

# Monitor initial progress (first 5-10 minutes)
tail -f logs/scihub_tor_full_download.log

# Check success rate after 100 papers
python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/scihub_tor_download_log.csv")
success = (log['status'] == 'success').sum()
print(f"Processed: {len(log):,}")
print(f"Success: {success:,} ({success/len(log)*100:.1f}%)")
EOF

# If success rate is good (>60%), let it run overnight
```

---

### Phase 4: Monitoring (periodic checks)

```bash
# Quick status check
tail -30 logs/scihub_tor_full_download.log

# Detailed progress
wc -l logs/scihub_tor_download_log.csv
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" | wc -l

# Success rate
python3 -c "import pandas as pd; log=pd.read_csv('logs/scihub_tor_download_log.csv'); s=(log['status']=='success').sum(); print(f'{s}/{len(log)} ({s/len(log)*100:.1f}%)')"
```

---

## Technical Details

### How It Works

1. **Tor Proxy Setup:**
   ```python
   socks.set_default_proxy(socks.SOCKS5, "localhost", 9050)
   socket.socket = socks.socksocket
   ```
   - Routes all requests through Tor SOCKS proxy on port 9050
   - Each request goes through Tor circuit (3 random nodes)
   - Exit node IP appears as requester to Sci-Hub

2. **Identity Rotation:**
   ```python
   with Controller.from_port(port=9051) as controller:
       controller.authenticate()
       controller.signal(Signal.NEWNYM)
   ```
   - Requests new Tor circuit every 100 successful downloads
   - Changes exit node IP to avoid cumulative tracking
   - 5-second wait for new circuit to establish

3. **User-Agent Rotation:**
   - Cycles through 5 realistic browser user agents
   - Makes requests appear more human-like
   - Reduces fingerprinting risk

4. **Smart Retry Logic:**
   - Only retries papers that failed with "error" or "forbidden" status
   - Skips papers that succeeded in original run
   - Skips papers genuinely not in Sci-Hub ("not_in_scihub")
   - Resume capability avoids re-downloading if interrupted

---

## Expected Results

### Papers to Process
- **Original Sci-Hub run:** 11,858 attempts
- **Previously succeeded:** 1,609 (will skip)
- **Failed with error/forbidden:** 10,249
- **Target for Tor download:** 10,249 papers

### Success Rate Projections

| Scenario | Success Rate | PDFs Gained | Total PDFs | % of 30K |
|----------|--------------|-------------|------------|----------|
| Conservative | 60% | +6,149 | 11,563 | 38.5% |
| **Expected** | **75%** | **+7,687** | **13,101** | **43.7%** |
| Optimistic | 85% | +8,712 | 14,126 | 47.1% |

### Time Estimates

- **Papers to download:** 10,249
- **Delay per paper:** 5 seconds
- **Tor overhead:** ~3 seconds per paper
- **Effective time:** ~8-10 seconds per paper
- **Total time:** 23-28 hours
- **With 75% success:** ~20 hours of actual downloading

**Recommendation:** Start in evening, let run overnight and next day.

---

## Monitoring Checkpoints

### After 100 Papers (~15-20 minutes)
- **Check:** Success rate should be >60%
- **If <60%:** Stop, troubleshoot, try different mirror
- **If >70%:** ✅ Continue to next checkpoint

### After 500 Papers (~1-2 hours)
- **Check:** Success rate maintained >60%
- **Check:** PDFs are valid (not HTML files)
- **If good:** Let run overnight

### Morning Check
- **Check:** Process still running
- **Check:** Success rate maintained
- **Check:** No repeated errors in log
- **If good:** Let continue

### Completion (~20 hours total)
- **Verify:** Total PDFs increased by expected amount
- **Analyze:** Success rate breakdown by year, publisher
- **Document:** Results for future reference

---

## Troubleshooting Guide

### Issue: Tor won't start
```bash
sudo systemctl status tor  # Check for errors
sudo journalctl -u tor -n 50  # View logs
sudo pkill tor  # Kill existing process
sudo systemctl restart tor  # Restart
```

### Issue: Test shows "ERROR" for all mirrors
```bash
# Restart Tor
sudo systemctl restart tor
sleep 30

# Test Tor is working
python3 -c "import socks, socket, requests; socks.set_default_proxy(socks.SOCKS5, 'localhost', 9050); socket.socket=socks.socksocket; print(requests.get('https://api.ipify.org').text)"

# Should show Tor exit node IP (not your real IP)

# Try test again
python3 scripts/test_single_doi_tor.py 10.1242/jeb.059667
```

### Issue: Success rate drops during run
```bash
# Check if Tor circuit is stale
sudo systemctl restart tor

# Resume download (will skip already done)
python3 scripts/download_via_scihub_tor.py --resume
```

### Issue: Download crashes
```bash
# Check logs
tail -100 logs/scihub_tor_full_download.log

# Common causes: network timeout, disk full, memory
# Solution: Resume download
python3 scripts/download_via_scihub_tor.py --resume
```

### Issue: Very slow downloads
- **Normal:** 6-10 papers per minute
- **Tor overhead:** Expected, not a bug
- **If slower than 3 papers/minute:**
  - Check system resources (CPU, memory, network)
  - Restart Tor for fresh circuits

---

## Success Criteria

### ✅ Setup Successful
- [ ] Tor installed and running (`systemctl status tor`)
- [ ] Port 9050 listening (`netstat -tulpn | grep 9050`)
- [ ] IP changes via Tor (test script shows different IP)
- [ ] Sci-Hub accessible (test script succeeds with at least one mirror)

### ✅ Test Run Successful
- [ ] Test mode shows >70% success rate
- [ ] PDFs are actually downloading (not HTML)
- [ ] No repeated "ERROR" responses
- [ ] Found best mirror to use

### ✅ Full Run Successful
- [ ] 100-paper checkpoint: >60% success
- [ ] 500-paper checkpoint: >60% success maintained
- [ ] Final run: >60% success
- [ ] Expected number of new PDFs (~6,000-8,000)
- [ ] PDFs are valid (random sampling)

---

## Next Steps After Completion

### 1. Verify Results
```bash
# Count new PDFs
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" | wc -l

# Should be: 5,414 + 6,000-8,000 = 11,000-13,000

# Analyze by year
python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/scihub_tor_download_log.csv")
success = log[log['status']=='success']
print(success.groupby('year').size().sort_index(ascending=False))
EOF
```

### 2. Update Documentation
- Update `docs/database/acquisition_strategy_review.md` with results
- Document which mirror worked best
- Note any issues encountered

### 3. Move to Next Priority
With ~13,000 PDFs (43% coverage), next priorities:
1. **IUCN web scraping** (+350-500 PDFs) - 3-5 days
2. **Thesis optimization** (+300-400 PDFs) - 2-3 days
3. **NOAA retry** (+120 PDFs) - When sites back online
4. **Manual downloads** (ongoing)

**Goal:** Reach 15,000-17,000 PDFs (50-57% coverage) within 3-4 weeks

---

## Files Summary

### Scripts Created
- ✅ `scripts/download_via_scihub_tor.py` - Main Tor-enabled downloader
- ✅ `scripts/test_single_doi_tor.py` - Single DOI test script

### Documentation Created
- ✅ `docs/database/tor_setup_guide.md` - Complete setup guide
- ✅ `docs/database/tor_quick_start.md` - Quick start reference
- ✅ `docs/database/tor_implementation_summary.md` - This file

### Previous Documentation
- ✅ `docs/database/scihub_diagnosis.md` - Problem analysis
- ✅ `docs/database/acquisition_strategy_review.md` - Overall strategy
- ✅ `docs/database/priorities_1_2_4_investigation_summary.md` - Investigation results

---

## Risk Assessment

### Low Risk
- ✅ Tor is legal and ethical for research
- ✅ Script has resume capability (won't lose progress)
- ✅ Conservative delays respect server load
- ✅ Won't re-download existing papers

### Medium Risk
- ⚠️ Success rate may be lower than expected (60% instead of 75%)
- ⚠️ Some Tor exit nodes may be blocked by Sci-Hub
- ⚠️ Download may take longer than estimated

### Mitigation
- Start with test mode to verify >60% success before full run
- Monitor first 100-500 papers closely
- Stop and adjust if success rate too low
- Resume capability allows trying different mirrors mid-run

---

## Alternative Approaches (If Tor Fails)

If Tor solution doesn't achieve >60% success:

1. **Different Network:** Try from different location (mobile hotspot, VPN)
2. **Browser Automation:** Use Playwright (slower but more reliable)
3. **Alternative Sources:** LibGen, Anna's Archive, Z-Library
4. **Manual Downloads:** Focus on institutional access for high-priority papers
5. **Postpone:** Focus on other priorities (IUCN, theses) and retry later

---

## Conclusion

**Ready for deployment:** All scripts and documentation complete

**Expected timeline:**
- Setup: 15 minutes
- Testing: 10 minutes
- Full download: 10-20 hours (unattended)
- Total: ~11-21 hours

**Expected gain:** +6,000-8,000 PDFs (bringing total to 11,000-13,000)

**Next action:** Begin with `sudo apt-get install tor`

**Status:** ✅ Ready to proceed
