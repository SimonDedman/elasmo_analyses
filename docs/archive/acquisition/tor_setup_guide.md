# Tor Setup Guide for Sci-Hub Downloads

**Purpose:** Route Sci-Hub downloads through Tor network to bypass IP blocking
**Expected Gain:** +8,000 PDFs (bringing total from 5,414 to ~13,400)
**Time Required:** 30 minutes setup + 2-3 days download time

---

## Prerequisites

- Linux system with sudo access
- Python 3.6+
- Internet connection

---

## Step 1: Install Tor

```bash
# Update package list
sudo apt-get update

# Install Tor
sudo apt-get install -y tor

# Verify installation
tor --version
```

**Expected output:**
```
Tor version 0.4.x.x
```

---

## Step 2: Install Python Dependencies

```bash
# Navigate to project directory
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Install required Python packages (using existing venv)
./venv/bin/pip install PySocks stem
# Note: requests, beautifulsoup4, pandas, tqdm already installed in venv
```

**Packages:**
- `PySocks` - SOCKS proxy support for routing through Tor ✅ Installing
- `stem` - Tor controller library (for identity rotation) ✅ Installing
- `requests` - HTTP requests ✅ Already installed
- `beautifulsoup4` - HTML parsing ✅ Already installed
- `pandas` - Data handling ✅ Already installed
- `tqdm` - Progress bars ✅ Already installed

---

## Step 3: Start Tor Service

```bash
# Start Tor as a background service
sudo systemctl start tor

# Check status
sudo systemctl status tor

# Enable Tor to start on boot (optional)
sudo systemctl enable tor
```

**Expected output:**
```
● tor.service - Anonymizing overlay network for TCP
   Loaded: loaded (/lib/systemd/system/tor.service; enabled)
   Active: active (running)
```

**Verify Tor is listening on port 9050:**
```bash
sudo netstat -tulpn | grep 9050
```

**Expected output:**
```
tcp  0  0  127.0.0.1:9050  0.0.0.0:*  LISTEN  1234/tor
```

---

## Step 4: Test Tor Connection

```bash
# Test if Tor is working
./venv/bin/python << 'EOF'
import socks
import socket
import requests

# Configure SOCKS proxy
socks.set_default_proxy(socks.SOCKS5, "localhost", 9050)
socket.socket = socks.socksocket

# Test connection - get current IP via Tor
response = requests.get("https://api.ipify.org?format=json", timeout=30)
print(f"Your IP via Tor: {response.json()['ip']}")

# Test Sci-Hub via Tor
test_url = "https://sci-hub.se"
response = requests.get(test_url, timeout=30)
print(f"Sci-Hub status via Tor: {response.status_code}")
print(f"Response length: {len(response.text)} bytes")
EOF
```

**Expected output:**
```
Your IP via Tor: 185.220.xxx.xxx  (should be different from your real IP)
Sci-Hub status via Tor: 200
Response length: >1000 bytes  (not just "ERROR")
```

**If you get "ERROR" response:**
- Tor may not be routing properly
- Try restarting Tor: `sudo systemctl restart tor`
- Check Tor logs: `sudo journalctl -u tor -n 50`

---

## Step 5: Run Tor-Enabled Sci-Hub Downloader

The script `scripts/download_via_scihub_tor.py` has been created for you.

### Test with 10 Papers First

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Test with 10 random papers
./venv/bin/python scripts/download_via_scihub_tor.py --max-papers 10 --test-mode
```

**What to look for:**
- Success rate should be >60% (ideally 70-85%)
- No "ERROR" responses
- Actual PDF files being saved
- Progress bar showing downloads

**If success rate is <50%:**
- Check if Tor is running: `sudo systemctl status tor`
- Verify IP is changing: Run test script above again
- Try different Sci-Hub mirror (edit script to change mirror)
- Increase delays between requests

### Run Full Download (11,858 Papers)

**Only proceed if test shows >60% success!**

```bash
# Run full download (will take ~10-20 hours)
nohup ./venv/bin/python scripts/download_via_scihub_tor.py > logs/scihub_tor_full_download.log 2>&1 &

# Get process ID
echo $! > logs/scihub_tor_pid.txt

# Monitor progress
tail -f logs/scihub_tor_full_download.log

# Or check log periodically
tail -30 logs/scihub_tor_full_download.log
```

**Download Statistics:**
- **Papers to download:** 11,858
- **Delay per request:** 5 seconds (slower for safety)
- **Time per paper:** ~8-10 seconds (including Tor overhead)
- **Total time:** 10-20 hours
- **Expected success:** 70-85% → 8,000-10,000 PDFs

### Monitor Progress

```bash
# Check how many papers have been processed
wc -l logs/scihub_tor_download_log.csv

# Check success rate so far
./venv/bin/python << 'EOF'
import pandas as pd
log = pd.read_csv("logs/scihub_tor_download_log.csv")
total = len(log)
success = (log['status'] == 'success').sum()
print(f"Processed: {total:,}")
print(f"Successes: {success:,}")
print(f"Success rate: {success/total*100:.1f}%")
print(f"\nStatus breakdown:")
print(log['status'].value_counts())
EOF

# Count actual PDFs downloaded
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" -mtime -1 | wc -l
```

### Stop Download (If Needed)

```bash
# Get process ID
cat logs/scihub_tor_pid.txt

# Kill process
kill $(cat logs/scihub_tor_pid.txt)

# Or kill all Python processes running the script
pkill -f download_via_scihub_tor.py
```

---

## Step 6: Troubleshooting

### Issue 1: Tor Service Won't Start

```bash
# Check for errors
sudo journalctl -u tor -n 50

# Try manual start
sudo tor

# Check if port 9050 is already in use
sudo lsof -i :9050
```

**Solution:**
- Kill existing Tor process: `sudo pkill tor`
- Restart service: `sudo systemctl restart tor`

---

### Issue 2: Still Getting "ERROR" Responses

**Possible causes:**
1. Sci-Hub has additional blocking (cookies, fingerprinting)
2. Tor exit nodes are blocked by Sci-Hub
3. Need to rotate Tor identity more frequently

**Solutions:**
```bash
# Edit script to increase identity rotation
# Change ROTATE_IDENTITY_EVERY from 100 to 25

# Try different Sci-Hub mirror
# Edit scripts/download_via_scihub_tor.py
# Change SCIHUB_MIRROR to "https://sci-hub.ru" or "https://sci-hub.wf"

# Test again
python3 scripts/download_via_scihub_tor.py --max-papers 10 --test-mode
```

---

### Issue 3: Very Slow Downloads

**Expected speed:** 6-10 papers per minute
**If slower:** Tor overhead or network issues

**Solutions:**
- Check Tor circuit is working: `sudo systemctl status tor`
- Restart Tor for fresh circuits: `sudo systemctl restart tor`
- Reduce delay between requests (risky - may cause blocking)
- Use faster mirror (try sci-hub.wf or sci-hub.ru)

---

### Issue 4: Download Stops/Crashes

**Check logs:**
```bash
tail -100 logs/scihub_tor_full_download.log
```

**Common causes:**
- Network timeout
- Tor circuit failure
- Disk space full
- Memory exhaustion

**Solution - Resume from where it stopped:**
```bash
# Script automatically resumes from last processed paper
python3 scripts/download_via_scihub_tor.py
```

---

## Step 7: Verify Results

### After Download Completes

```bash
# Count new PDFs
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" | wc -l

# Analyze results
python3 << 'EOF'
import pandas as pd

# Load new log
log = pd.read_csv("logs/scihub_tor_download_log.csv")

print("=" * 80)
print("SCI-HUB TOR DOWNLOAD RESULTS")
print("=" * 80)
print(f"\nTotal papers attempted: {len(log):,}")

# Status breakdown
print(f"\nStatus breakdown:")
for status, count in log['status'].value_counts().items():
    print(f"  {status}: {count:,} ({count/len(log)*100:.1f}%)")

# Year distribution of successes
successes = log[log['status'] == 'success']
print(f"\nSuccessful downloads by year:")
year_dist = successes.groupby('year').size().sort_index(ascending=False)
for year, count in year_dist.head(10).items():
    print(f"  {int(year)}: {count:,}")

# Total size
total_size = successes['file_size'].sum()
print(f"\nTotal data downloaded: {total_size / (1024**3):.2f} GB")

print("\n" + "=" * 80)
EOF
```

**Expected results:**
- Success rate: 70-85%
- Successful downloads: 8,000-10,000 PDFs
- Total size: 15-25 GB
- Most successful: Recent papers (2020-2025)

---

## Success Criteria

### ✅ Successful Setup
- [ ] Tor installed and running
- [ ] Test connection shows different IP
- [ ] Sci-Hub accessible via Tor (not "ERROR")
- [ ] Test download shows >60% success rate

### ✅ Successful Full Run
- [ ] 8,000+ PDFs downloaded
- [ ] Success rate >70%
- [ ] No repeated "ERROR" responses
- [ ] PDFs are valid (not HTML files)

---

## Advanced: Identity Rotation

The script automatically rotates Tor identity every 100 successful downloads. You can adjust this:

```python
# In scripts/download_via_scihub_tor.py
ROTATE_IDENTITY_EVERY = 50  # Rotate more frequently

# Or rotate manually if needed
from stem import Signal
from stem.control import Controller

with Controller.from_port(port=9051) as controller:
    controller.authenticate()
    controller.signal(Signal.NEWNYM)
    print("Tor identity rotated")
```

**Note:** Requires Tor ControlPort to be enabled (script handles this automatically)

---

## Cleanup (After Completion)

```bash
# Stop Tor service if no longer needed
sudo systemctl stop tor

# Disable Tor from starting on boot
sudo systemctl disable tor

# Optionally remove Tor
# sudo apt-get remove tor
```

---

## Estimated Timeline

| Phase | Time | Notes |
|-------|------|-------|
| Install Tor | 5 minutes | One-time setup |
| Install Python packages | 2 minutes | One-time setup |
| Test Tor connection | 5 minutes | Verify working |
| Test 10 papers | 5-10 minutes | Verify >60% success |
| **Full download** | **10-20 hours** | **Can run overnight** |
| Verify results | 10 minutes | Check success rate |
| **Total** | **~11-21 hours** | **Mostly automated** |

---

## Next Steps After Successful Download

1. **Compare with previous attempts:**
   ```bash
   # Papers that failed before but succeeded now
   python3 scripts/compare_scihub_results.py
   ```

2. **Update overall acquisition status:**
   ```bash
   # Total PDFs: 5,414 + 8,000 = ~13,400 (45% of 30,000)
   ```

3. **Move to next priority:**
   - IUCN web scraping (+350-500 PDFs)
   - Thesis optimization (+300-400 PDFs)
   - Manual downloads (ongoing)

---

## Support & Troubleshooting

**If you encounter issues:**

1. Check Tor status: `sudo systemctl status tor`
2. Check Tor logs: `sudo journalctl -u tor -n 50`
3. Verify IP changes: Run IP check script above
4. Test with single DOI: `python3 scripts/test_single_doi_tor.py 10.1242/jeb.059667`
5. Check script logs: `tail -100 logs/scihub_tor_full_download.log`

**Common solutions:**
- Restart Tor: `sudo systemctl restart tor`
- Clear Tor data: `sudo rm -rf /var/lib/tor/*` (then restart Tor)
- Change Sci-Hub mirror in script
- Increase delays between requests

---

**Ready to proceed?** Run the commands in order and monitor progress!

**Files created:**
- `scripts/download_via_scihub_tor.py` - Main Tor-enabled downloader
- `scripts/test_single_doi_tor.py` - Test single DOI via Tor
- `docs/database/tor_setup_guide.md` - This guide

**Status:** Ready for installation and testing
