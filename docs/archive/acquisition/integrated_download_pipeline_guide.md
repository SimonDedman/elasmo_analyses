# Integrated Download Pipeline Guide

**Created:** 2025-10-24
**Purpose:** Simultaneously run Sci-Hub downloads and DOI hunting with shared queue

---

## Overview

The integrated download pipeline runs two processes in parallel:

1. **DOI Hunter** - Searches for missing DOIs (2010+ papers) and adds them to queue
2. **Sci-Hub Downloader** - Downloads PDFs from queue via Sci-Hub + Tor

Both processes share a SQLite queue database, allowing DOI hunting results to feed directly into Sci-Hub downloads without needing to run Sci-Hub twice.

---

## Architecture

```
┌─────────────────────┐
│  Shark-References   │
│  CSV (30,523)       │
└──────────┬──────────┘
           │
           ├──────────────────────────────────────────┐
           │                                          │
           ▼                                          ▼
┌─────────────────────┐                    ┌─────────────────────┐
│   DOI Hunter        │                    │  Download Queue DB  │
│   (3,290 papers)    │───────adds to──────▶   (SQLite)         │
│   2010+ only        │                    │                     │
└─────────────────────┘                    └──────────┬──────────┘
                                                      │
                                                      │ reads from
                                                      │
                                           ┌──────────▼──────────┐
                                           │  Sci-Hub Downloader │
                                           │  (via Tor)          │
                                           └──────────┬──────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────────┐
                                           │  PDF Storage        │
                                           │  (by year)          │
                                           └─────────────────────┘
```

---

## Quick Start

### 1. Start the Pipeline

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"

# Start both processes
bash scripts/run_integrated_pipeline.sh
```

This will:
- Start DOI hunter in background
- Start Sci-Hub downloader in background
- Save process IDs to `logs/*.pid`
- Create log files in `logs/`

### 2. Monitor Progress

**Real-time dashboard** (updates every 10 seconds):
```bash
./venv/bin/python scripts/monitor_download_progress.py
```

**Tail log files** (view as they update):
```bash
# DOI hunter log
tail -f logs/doi_hunter_daemon.log

# Sci-Hub downloader log
tail -f logs/scihub_downloader_daemon.log

# Both logs side-by-side
tail -f logs/doi_hunter_daemon.log & tail -f logs/scihub_downloader_daemon.log
```

**Last N lines** of logs:
```bash
# Last 50 lines of DOI hunter
tail -n 50 logs/doi_hunter_daemon.log

# Last 100 lines of Sci-Hub downloader
tail -n 100 logs/scihub_downloader_daemon.log
```

**Watch specific patterns** (grep while tailing):
```bash
# Watch for successful DOI finds
tail -f logs/doi_hunter_daemon.log | grep "✓ Found"

# Watch for successful PDF downloads
tail -f logs/scihub_downloader_daemon.log | grep "✓ Saved"

# Watch for errors
tail -f logs/*.log | grep "✗"
```

### 3. Stop the Pipeline

```bash
# Graceful stop
bash scripts/stop_pipeline.sh

# Force kill (if graceful stop fails)
pkill -f doi_hunter_daemon.py
pkill -f scihub_downloader_daemon.py
```

---

## Terminal Commands Reference

### Monitoring Commands

| Command | Purpose | Update Frequency |
|---------|---------|------------------|
| `./venv/bin/python scripts/monitor_download_progress.py` | Full dashboard | Every 10s |
| `./venv/bin/python scripts/monitor_download_progress.py 5` | Dashboard (faster) | Every 5s |
| `tail -f logs/doi_hunter_daemon.log` | DOI hunter live | Real-time |
| `tail -f logs/scihub_downloader_daemon.log` | Sci-Hub live | Real-time |
| `watch -n 10 'ls -lh logs/'` | Watch log file sizes | Every 10s |

### Useful Log Viewing

```bash
# View last 100 lines of DOI hunter
tail -n 100 logs/doi_hunter_daemon.log

# View last 100 lines of Sci-Hub
tail -n 100 logs/scihub_downloader_daemon.log

# Follow both logs (split screen with tmux)
tmux
# Ctrl+B then " to split horizontally
# Top pane: tail -f logs/doi_hunter_daemon.log
# Bottom pane: tail -f logs/scihub_downloader_daemon.log
# Ctrl+B then arrow keys to navigate

# Search logs for specific patterns
grep "✓ Found" logs/doi_hunter_daemon.log | tail -20
grep "Failed" logs/scihub_downloader_daemon.log | tail -20
```

### Process Management

```bash
# Check if processes are running
ps aux | grep doi_hunter
ps aux | grep scihub_downloader

# Check process IDs from PID files
cat logs/doi_hunter.pid
cat logs/scihub_downloader.pid

# Kill specific process
kill $(cat logs/doi_hunter.pid)
kill $(cat logs/scihub_downloader.pid)

# Force kill if needed
kill -9 $(cat logs/doi_hunter.pid)
```

### Database Queries

```bash
# Quick stats
sqlite3 outputs/download_queue.db "
  SELECT status, COUNT(*)
  FROM download_queue
  GROUP BY status;
"

# Success rate
sqlite3 outputs/download_queue.db "
  SELECT
    COUNT(*) as total,
    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as success,
    ROUND(SUM(CASE WHEN status='success' THEN 1 ELSE 0 END)*100.0/COUNT(*), 2) as rate
  FROM download_queue
  WHERE status IN ('success', 'failed');
"

# Recent activity
sqlite3 outputs/download_queue.db "
  SELECT timestamp, process, action, details
  FROM activity_log
  ORDER BY timestamp DESC
  LIMIT 20;
"

# DOIs from hunt vs existing
sqlite3 outputs/download_queue.db "
  SELECT source, COUNT(*)
  FROM download_queue
  GROUP BY source;
"
```

### File System Monitoring

```bash
# Count PDFs by year
find /media/simon/data/Documents/Si\ Work/Papers\ \&\ Books/SharkPapers/ -name "*.pdf" | wc -l

# Count PDFs added in last hour
find /media/simon/data/Documents/Si\ Work/Papers\ \&\ Books/SharkPapers/ -name "*.pdf" -mmin -60 | wc -l

# Watch PDF count in real-time
watch -n 30 'find /media/simon/data/Documents/Si\ Work/Papers\ \&\ Books/SharkPapers/ -name "*.pdf" | wc -l'

# Disk space usage
du -sh /media/simon/data/Documents/Si\ Work/Papers\ \&\ Books/SharkPapers/
```

---

## Expected Timeline

### DOI Hunter (3,290 papers from 2010+)
- **Duration:** ~2.6 hours
- **Success rate:** ~18%
- **Expected DOIs found:** ~561
- **Rate:** ~21 papers/minute

### Sci-Hub Downloader (16,366 existing + ~561 new = 16,927 total)
- **Duration:** ~14-20 hours (depends on Sci-Hub availability)
- **Success rate:** ~70-85%
- **Expected PDFs:** ~11,800-14,400
- **Rate:** ~14 downloads/minute (with 3s delay)

### Combined
- **Total duration:** ~20-24 hours (mostly Sci-Hub time)
- **Final PDF count:** ~19,000-20,000 (62-65% coverage)

---

## File Locations

### Scripts
- `scripts/create_download_queue.py` - Initialize queue database
- `scripts/doi_hunter_daemon.py` - DOI hunting process
- `scripts/scihub_downloader_daemon.py` - Sci-Hub download process
- `scripts/run_integrated_pipeline.sh` - Start both processes
- `scripts/stop_pipeline.sh` - Stop both processes
- `scripts/monitor_download_progress.py` - Real-time monitoring

### Data
- `outputs/download_queue.db` - Shared queue database (SQLite)
- `outputs/shark_references_bulk/shark_references_complete_2025_to_1950_20251021.csv` - Source data

### Logs
- `logs/doi_hunter_daemon.log` - DOI hunter output
- `logs/scihub_downloader_daemon.log` - Sci-Hub downloader output
- `logs/doi_hunter.pid` - DOI hunter process ID
- `logs/scihub_downloader.pid` - Sci-Hub process ID
- `logs/doi_hunting_progress.csv` - Detailed DOI hunting results

### PDFs
- `/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/YYYY/*.pdf` - Downloaded PDFs by year

---

## Queue Database Schema

### `download_queue` table
```sql
CREATE TABLE download_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    literature_id TEXT,
    doi TEXT UNIQUE NOT NULL,
    year INTEGER,
    authors TEXT,
    title TEXT,
    source TEXT,              -- 'existing' or 'doi_hunt'
    priority INTEGER,         -- Year (more recent = higher priority)
    status TEXT,              -- 'pending', 'downloading', 'success', 'failed', 'skipped'
    added_timestamp TEXT,
    download_timestamp TEXT,
    pdf_path TEXT,
    error_message TEXT
)
```

### Status values
- **pending** - In queue, not yet processed
- **downloading** - Currently being downloaded
- **success** - PDF successfully downloaded
- **failed** - Download failed (check error_message)
- **skipped** - Already exists

---

## Troubleshooting

### Tor Issues

**Problem:** Sci-Hub downloader fails with "Tor proxy error"

**Solution:**
```bash
# Check if Tor is running
sudo systemctl status tor

# Start Tor if not running
sudo systemctl start tor

# Test Tor connection
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org
```

### DOI Hunter Slow

**Problem:** DOI hunter running very slowly

**Check:**
```bash
# View recent activity
tail -f logs/doi_hunter_daemon.log

# Check API delays in code
grep "DELAY_BETWEEN_REQUESTS" scripts/doi_hunter_daemon.py
```

Default is 1 second between API requests (respectful to CrossRef/DataCite).

### Sci-Hub Blocked

**Problem:** Sci-Hub downloads failing consistently

**Solution:**
1. Check if Tor is working (see above)
2. Try different Sci-Hub mirror (edit `SCI_HUB_URLS` in `scripts/scihub_downloader_daemon.py`)
3. Increase delay between downloads (edit `DELAY_BETWEEN_DOWNLOADS`)

### Database Locked

**Problem:** "Database is locked" error

**Solution:**
```bash
# Check if multiple processes are accessing database
ps aux | grep download

# Stop all processes and restart
bash scripts/stop_pipeline.sh
bash scripts/run_integrated_pipeline.sh
```

### Disk Space

**Problem:** Running out of disk space

**Check:**
```bash
# Check available space
df -h /media/simon/data/

# Check PDF directory size
du -sh /media/simon/data/Documents/Si\ Work/Papers\ \&\ Books/SharkPapers/

# Average PDF size and projection
find /media/simon/data/Documents/Si\ Work/Papers\ \&\ Books/SharkPapers/ -name "*.pdf" -exec du -b {} + | awk '{total+=$1} END {print "Average:", total/NR/1024/1024, "MB"}'
```

**Typical:** ~2-3 MB per PDF × 17,000 PDFs = ~35-50 GB needed

---

## Advanced Usage

### Run Only DOI Hunter

```bash
./venv/bin/python scripts/doi_hunter_daemon.py > logs/doi_hunter.log 2>&1 &
```

### Run Only Sci-Hub Downloader

```bash
./venv/bin/python scripts/scihub_downloader_daemon.py > logs/scihub_downloader.log 2>&1 &
```

### Custom Year Range for DOI Hunter

Edit `scripts/doi_hunter_daemon.py`:
```python
MIN_YEAR = 2015  # Change from 2010 to 2015 for only very recent papers
```

### Adjust Download Speed

Edit `scripts/scihub_downloader_daemon.py`:
```python
DELAY_BETWEEN_DOWNLOADS = 5.0  # Slower (more respectful)
DELAY_BETWEEN_DOWNLOADS = 1.0  # Faster (risk of being blocked)
```

### Disable Tor (not recommended)

Edit `scripts/scihub_downloader_daemon.py`:
```python
USE_TOR = False  # Warning: Your IP will be exposed to Sci-Hub
```

---

## Success Metrics

Monitor these to gauge progress:

1. **Queue completion:** Pending / Total ratio decreasing
2. **Success rate:** Success / (Success + Failed) ratio
3. **PDF count:** Total PDFs in storage directory
4. **Coverage:** PDFs / 30,523 total papers
5. **DOI hunt effectiveness:** DOIs from doi_hunt / Total DOIs

Target: **62-65% coverage** (19,000-20,000 PDFs)

---

## What to Work On While Running

The pipeline will run for ~20-24 hours. Good time to:

1. **Review existing PDFs** - OCR, extract metadata, etc.
2. **Panel preparation** - Analyze techniques, species, trends
3. **Database refinement** - Clean up species names, verify data
4. **Documentation** - Write up methodology, results
5. **Other projects** - The pipeline is autonomous

Just monitor occasionally with:
```bash
./venv/bin/python scripts/monitor_download_progress.py
```

---

## When It's Done

After both processes complete:

1. **Check final statistics:**
   ```bash
   ./venv/bin/python scripts/monitor_download_progress.py
   ```

2. **Count final PDFs:**
   ```bash
   find /media/simon/data/Documents/Si\ Work/Papers\ \&\ Books/SharkPapers/ -name "*.pdf" | wc -l
   ```

3. **Review logs for issues:**
   ```bash
   grep "Failed" logs/scihub_downloader_daemon.log | wc -l
   ```

4. **Export results:**
   ```bash
   # Export successful downloads
   sqlite3 -csv outputs/download_queue.db "
     SELECT literature_id, doi, year, title, pdf_path
     FROM download_queue
     WHERE status = 'success'
   " > outputs/successful_downloads.csv

   # Export failed downloads
   sqlite3 -csv outputs/download_queue.db "
     SELECT literature_id, doi, year, title, error_message
     FROM download_queue
     WHERE status = 'failed'
   " > outputs/failed_downloads.csv
   ```

5. **Clean up:**
   ```bash
   # Remove PID files
   rm logs/*.pid

   # Archive logs
   mkdir -p logs/archive
   mv logs/*.log logs/archive/run_$(date +%Y%m%d_%H%M%S)/
   ```

---

## Notes

- Both processes are designed to be **idempotent** - safe to stop and restart
- Queue database persists state - no progress lost if processes crash
- PDFs already downloaded are skipped automatically
- Tor provides anonymity and helps avoid IP blocks
- DOI hunter only searches for papers 2010+ (configurable)
- Sci-Hub downloader prioritizes recent papers (higher year = higher priority)

---

**Last Updated:** 2025-10-24
