# DownThemAll Quick Start Guide

**Created:** November 21, 2025
**Status:** ✅ Ready to use - 7 batch files created (560 papers)

---

## What You Have

### 🎯 **Ready-to-Use Batch Files**

**Open Access Papers (NO LOGIN REQUIRED!):**
- **Frontiers:** 4 batches = 343 papers (100+100+100+43)
- **PLOS:** 3 batches = 217 papers (100+100+17)
- **Total:** 7 batch files = **560 papers** ready to download

**Location:** `outputs/downthemall_batches/`

### Expected Results
- **Time:** 1-2 hours for all 560 papers
- **Speed:** ~6-10 papers/minute
- **Success rate:** 95%+ (all are open access)
- **Immediate boost:** 40.5% → 42.3% coverage

---

## Quick Start (3 Steps)

### Step 1: Install DownThemAll (2 minutes)
1. Open Firefox
2. Go to: https://www.downthemall.net/
3. Click "Add to Firefox"
4. Grant permissions when prompted

### Step 2: Configure DownThemAll (1 minute)
1. Click DownThemAll icon in Firefox toolbar
2. Go to **Preferences**
3. Set:
   - **Max concurrent downloads:** 15
   - **Download directory:** `/home/simon/Documents/Si Work/Papers & Books/SharkPapers/`
   - **Delay between downloads:** 2 seconds (for Frontiers/PLOS, they're fast)

### Step 3: Download First Batch (10 minutes)
1. **Open in Firefox:**
   ```
   outputs/downthemall_batches/batch_frontiers_batch1_100papers.html
   ```

2. **Click "Open All 100 Tabs" button**
   - Wait 30-60 seconds for tabs to load

3. **Right-click anywhere** → **DownThemAll!** → **All Tabs**

4. **Filter for PDFs:**
   - Enter: `*.pdf` in filter box
   - Uncheck any non-PDF files

5. **Click "Download"**

6. **Monitor progress** in DTA window
   - Watch for any failures (retry those)

7. **When complete:** Close all tabs (Ctrl+W repeatedly)

8. **Repeat for remaining batches!**

---

## All Batch Files

### Frontiers (343 papers - All FREE)
```
✅ batch_frontiers_batch1_100papers.html    (100 papers)  ← START HERE
✅ batch_frontiers_batch2_100papers.html    (100 papers)
✅ batch_frontiers_batch3_100papers.html    (100 papers)
✅ batch_frontiers_batch4_43papers.html     (43 papers)
```

### PLOS (217 papers - All FREE)
```
✅ batch_plos_batch1_100papers.html         (100 papers)
✅ batch_plos_batch2_100papers.html         (100 papers)
✅ batch_plos_batch3_17papers.html          (17 papers)
```

**Estimated time:**
- 10 minutes per batch (100 papers)
- 5 minutes per small batch
- **Total: ~60-90 minutes for all 560 papers**

---

## What Happens Next?

### After These 7 Batches (560 papers)

You'll have:
- **Current coverage:** 40.5% (12,381 papers)
- **After DTA batches:** ~42.3% (12,941 papers)
- **Remaining:** 17,582 papers (57.7%)

### Then Create More Batches

Use the script to create batches for major publishers:

```bash
# Create batches for institutional access papers
./venv/bin/python scripts/create_downthemall_batches.py --publisher wiley --batch-size 100
./venv/bin/python scripts/create_downthemall_batches.py --publisher elsevier --batch-size 100
./venv/bin/python scripts/create_downthemall_batches.py --publisher springer --batch-size 100

# Or create all at once
./venv/bin/python scripts/create_downthemall_batches.py --publisher all --batch-size 100
```

**Note:** Wiley, Elsevier, Springer require institutional access (VPN/proxy)

---

## Tips for Success

### 🟢 DO:
- ✅ Start with Frontiers/PLOS (no login needed)
- ✅ Wait for all tabs to load before using DTA
- ✅ Close other Firefox windows (save RAM)
- ✅ Use 100 papers per batch (sweet spot)
- ✅ Check download folder after each batch

### 🔴 DON'T:
- ❌ Open too many tabs (>200 on 8GB RAM system)
- ❌ Close window while tabs are opening
- ❌ Skip the PDF filter in DTA (you'll download HTML pages)
- ❌ Set concurrent downloads too high (>20)
- ❌ Rush - let tabs fully load before DTA scan

---

## Troubleshooting

### Problem: Browser freezes when opening tabs
**Solution:** Reduce batch size to 50 papers and try again

### Problem: DTA doesn't find PDFs
**Solution:**
- Wait longer for tabs to fully load (2-3 minutes)
- Check if you're on correct Firefox window
- Some tabs might not have loaded - refresh them

### Problem: Downloads fail or timeout
**Solution:**
- Increase timeout in DTA preferences (60 → 120 seconds)
- Reduce concurrent downloads (15 → 10)
- Check internet connection

### Problem: Downloaded HTML pages instead of PDFs
**Solution:**
- You didn't filter for `*.pdf` in DTA
- Some publishers redirect - check if institutional access needed

---

## Performance Benchmarks

### Expected Performance (Open Access)
- **Opening 100 tabs:** 30-60 seconds
- **DTA scanning:** 20-30 seconds
- **Downloading 100 PDFs:** 6-10 minutes
- **Total per batch:** 10-12 minutes

### Comparison to Other Methods

| Method | Speed | 560 Papers Time |
|--------|-------|-----------------|
| **Manual download** | 1-2 papers/min | 4-9 hours ⏰ |
| **Python script** | 3-5 papers/min | 2-3 hours |
| **DownThemAll multi-tab** | **6-10 papers/min** | **1-2 hours** ⚡ |

**Time saved: 2-7 hours for just these 560 papers!**

---

## After Open Access Papers

### Next Steps (Requires Institutional Access)

Once you've downloaded the 560 OA papers:

1. **Set up institutional VPN/proxy**
2. **Create batches for major publishers:**
   - Wiley: 1,542 papers
   - Elsevier: 1,604 papers
   - Springer Nature: 1,248 papers

3. **Use same DownThemAll workflow**
   - But with VPN connected
   - Slower (3-5 papers/min due to rate limits)
   - Still 3-5x faster than manual!

**See:** `docs/database/DOWNTHEMALL_BULK_DOWNLOAD_GUIDE.md` for full details

---

## File Locations

```
📁 Project Root
├── outputs/
│   └── downthemall_batches/
│       ├── batch_frontiers_batch1_100papers.html    ← START HERE!
│       ├── batch_frontiers_batch2_100papers.html
│       ├── batch_frontiers_batch3_100papers.html
│       ├── batch_frontiers_batch4_43papers.html
│       ├── batch_plos_batch1_100papers.html
│       ├── batch_plos_batch2_100papers.html
│       └── batch_plos_batch3_17papers.html
│
├── scripts/
│   └── create_downthemall_batches.py               ← Generate more batches
│
└── docs/database/
    ├── DOWNTHEMALL_BULK_DOWNLOAD_GUIDE.md          ← Full documentation
    └── INSTITUTIONAL_ACCESS_WORKFLOW.md            ← Next phase

PDFs download to:
/home/simon/Documents/Si Work/Papers & Books/SharkPapers/
```

---

## Summary

### What Was Created
- ✅ **DownThemAll strategy** designed and documented
- ✅ **Batch generator script** created and tested
- ✅ **7 batch files** ready to use (560 papers)
- ✅ **Complete documentation** (5,000+ words)

### What You Can Do Right Now
1. Install DownThemAll (2 min)
2. Open first batch HTML (1 min)
3. Download 100 papers (10 min)
4. Repeat 6 more times
5. **Get 560 papers in 1-2 hours!**

### Impact
- **From:** 40.5% coverage (12,381 papers)
- **To:** 42.3% coverage (12,941 papers)
- **Boost:** +560 papers (+1.8%)
- **Time:** 1-2 hours vs. 4-9 hours manual
- **Savings:** 3-7 hours**

---

## Ready?

**Open this file in Firefox to start:**
```
outputs/downthemall_batches/batch_frontiers_batch1_100papers.html
```

**Click the button, use DownThemAll, and watch the PDFs roll in!** 🚀

---

**Questions? See:** `docs/database/DOWNTHEMALL_BULK_DOWNLOAD_GUIDE.md`
