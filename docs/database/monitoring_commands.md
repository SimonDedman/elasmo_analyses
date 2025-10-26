# Download Monitoring Commands

## Quick Status Check (All Downloads)

```bash
# Show all running downloads
ps aux | grep python3 | grep -E "(scihub|semantic|iucn)" | grep -v grep

# Count PDFs downloaded so far
find "/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers/" -name "*.pdf" | wc -l
```

---

## Sci-Hub Download

**Progress:**
```bash
tail -30 logs/scihub_full_download.log
```

**Statistics:**
```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
./venv/bin/python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/scihub_download_log.csv")
total = len(log)
success = (log['status']=='success').sum()
print(f"Processed: {total:,} / 11,858")
print(f"Success: {success:,} ({success/total*100:.1f}%)")
print(f"Progress: {total/11858*100:.1f}%")
EOF
```

---

## Semantic Scholar Download

**Progress:**
```bash
tail -30 logs/semantic_scholar_full.log
```

**Statistics:**
```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
./venv/bin/python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/semantic_scholar_log.csv")
total = len(log)
found = (log['semantic_scholar_id'].notna()).sum()
pdfs = (log['pdf_status']=='success').sum()
print(f"Processed: {total:,} / 13,890")
print(f"Found in database: {found:,} ({found/total*100:.1f}%)")
print(f"PDFs downloaded: {pdfs:,} ({pdfs/total*100:.1f}%)")
print(f"Progress: {total/13890*100:.1f}%")
EOF
```

---

## IUCN Red List Download

**Progress:**
```bash
tail -30 logs/iucn_full_download.log
```

**Statistics:**
```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
./venv/bin/python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/iucn_download_log.csv")
total = len(log)
found = (log['taxon_id'].notna()).sum()
print(f"Processed: {total:,} / 1,082")
print(f"Found in IUCN: {found:,} ({found/total*100:.1f}%)")
print(f"Progress: {total/1082*100:.1f}%")
EOF
```

---

## Thesis Download

**Progress:**
```bash
tail -30 logs/thesis_download_log.csv
```

**Statistics:**
```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
./venv/bin/python3 << 'EOF'
import pandas as pd
log = pd.read_csv("logs/thesis_download_log.csv")
total = len(log)
found = (log['source'] != 'none').sum()
pdfs = (log['pdf_status']=='success').sum()
print(f"Processed: {total:,} / 325")
print(f"Found online: {found:,} ({found/total*100:.1f}%)")
print(f"PDFs downloaded: {pdfs:,} ({pdfs/total*100:.1f}%)")
print(f"Progress: {total/325*100:.1f}%")

# Show breakdown by source
print("\nBreakdown by source:")
for source in log['source'].value_counts().items():
    print(f"  {source[0]:20s}: {source[1]:>4,}")
EOF
```

---

## Combined Summary

```bash
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
./venv/bin/python3 << 'EOF'
import pandas as pd
from pathlib import Path

print("="*60)
print("DOWNLOAD PROGRESS SUMMARY")
print("="*60)

# Count PDFs
pdf_dir = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
total_pdfs = len(list(pdf_dir.rglob("*.pdf")))
print(f"\n📥 Total PDFs acquired: {total_pdfs:,}")

# Sci-Hub
try:
    scihub = pd.read_csv("logs/scihub_download_log.csv")
    scihub_done = len(scihub)
    scihub_success = (scihub['status']=='success').sum()
    print(f"\n🔬 Sci-Hub: {scihub_done:,}/11,858 ({scihub_done/11858*100:.1f}%)")
    print(f"   Success: {scihub_success:,} ({scihub_success/scihub_done*100:.1f}%)")
except:
    print(f"\n🔬 Sci-Hub: Running...")

# Semantic Scholar
try:
    semantic = pd.read_csv("logs/semantic_scholar_log.csv")
    sem_done = len(semantic)
    sem_pdfs = (semantic['pdf_status']=='success').sum()
    print(f"\n📚 Semantic Scholar: {sem_done:,}/13,890 ({sem_done/13890*100:.1f}%)")
    print(f"   PDFs: {sem_pdfs:,} ({sem_pdfs/sem_done*100:.1f}%)")
except:
    print(f"\n📚 Semantic Scholar: Running...")

# IUCN
try:
    iucn = pd.read_csv("logs/iucn_download_log.csv")
    iucn_done = len(iucn)
    iucn_found = (iucn['taxon_id'].notna()).sum()
    print(f"\n🦈 IUCN Red List: {iucn_done:,}/1,082 ({iucn_done/1082*100:.1f}%)")
    print(f"   Found: {iucn_found:,} ({iucn_found/iucn_done*100:.1f}%)")
except:
    print(f"\n🦈 IUCN Red List: Running...")

# Theses
try:
    thesis = pd.read_csv("logs/thesis_download_log.csv")
    thesis_done = len(thesis)
    thesis_found = (thesis['source'] != 'none').sum()
    thesis_pdfs = (thesis['pdf_status']=='success').sum()
    print(f"\n🎓 Theses: {thesis_done:,}/325 ({thesis_done/325*100:.1f}%)")
    print(f"   Found: {thesis_found:,}, PDFs: {thesis_pdfs:,}")
except:
    print(f"\n🎓 Theses: Running...")

print("\n" + "="*60)
EOF
```
