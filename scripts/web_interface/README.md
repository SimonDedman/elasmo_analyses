# Paper Download Web Interface

A Flask-based web interface for managing and tracking paper downloads for the EEA Data Panel project.

## Overview

This tool helps you efficiently download the remaining scientific papers needed for the analytical methods review. It provides:

- **Dashboard** with progress statistics and quick actions
- **Paper browser** with filtering by year, priority, status, and DOI availability
- **Direct download links** to DOI resolver, Sci-Hub, Unpaywall, and Google Scholar
- **Status tracking** to mark papers as downloaded, unavailable, or skipped
- **Batch operations** for bulk status updates and export

## Quick Start

```bash
# From the Data Panel directory
cd scripts/web_interface
./run.sh

# Or directly with Python
../../venv/bin/python app.py
```

Then open **http://localhost:5000** in your browser.

## Features

### Dashboard (`/`)
- Overview statistics: total papers, downloaded, pending, unavailable
- Progress bar showing completion percentage
- Papers organized by year and priority group
- Quick action buttons for common workflows

### Paper Browser (`/papers`)
- Filter papers by:
  - Year
  - Priority group (P1-P4)
  - Download status
  - DOI availability
  - Search by title/author/journal
- Direct download links for each paper
- Quick status buttons to mark papers
- Bulk selection and status updates
- Pagination for large result sets

### Paper Detail (`/paper/<id>`)
- Full paper metadata
- All available download links
- Status update buttons
- Notes field for tracking issues

### Batch Download (`/export/batch`)
- Grid view of papers ready for download
- "Open All in Sci-Hub" button (opens 10 at a time)
- Quick status marking after downloading
- CSV export option

### Statistics (`/stats`)
- Progress by year
- Progress by priority group
- Top journals with pending papers
- Recent activity log

## Priority Groups

Papers are organized into priority groups based on acquisition strategy:

| Priority | Description | Strategy |
|----------|-------------|----------|
| **P1** | Recent papers (2020+) with DOI | Highest value - most relevant to current research |
| **P2** | 2000s papers with DOI | Important for trend analysis |
| **P3** | Key journals regardless of year | Journal-specific bulk downloads |
| **P4** | Papers without DOI | Require manual search |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `D` | Go to Dashboard |
| `P` | Go to Papers list |
| `S` | Go to Statistics |

## Download Workflow

### Recommended approach:

1. **Start with P1 papers** (recent with DOI) - highest value
2. Use the **Batch Download** page to open Sci-Hub links in batches
3. Download PDFs and mark papers as "Downloaded"
4. For unavailable papers, mark as "Unavailable" and try alternative sources
5. Move to P2, P3, then P4

### Download sources (in order of reliability):

1. **DOI** - Official publisher page (may require subscription)
2. **Sci-Hub** - Direct PDF access for papers with DOI
3. **Unpaywall** - Legal open access versions
4. **Google Scholar** - May find preprints or author copies

## Data Storage

### Database
- Located at: `database/download_tracker.db`
- SQLite database tracking paper metadata and download status
- Automatically created on first run

### Source Data
Papers are loaded from:
- `outputs/acquisition_priority_1_recent_with_doi.csv`
- `outputs/acquisition_priority_2_2000s_with_doi.csv`
- `outputs/acquisition_priority_3_key_journals.csv`
- `outputs/acquisition_priority_4_no_doi_complete_metadata.csv`

## API Endpoints

### `POST /api/update_status`
Update status for a single paper.

```json
{
  "paper_id": 123,
  "status": "downloaded",
  "source": "scihub",
  "notes": "Downloaded successfully"
}
```

### `POST /api/batch_update`
Update status for multiple papers.

```json
{
  "paper_ids": [123, 456, 789],
  "status": "downloaded"
}
```

### `GET /export/batch`
Export papers as HTML or CSV.

Query parameters:
- `format`: `html` or `csv`
- `status`: Filter by status (default: `pending`)
- `limit`: Number of papers to export (default: 100)

## Troubleshooting

### "No papers found"
- Check if the CSV files exist in `outputs/`
- Click "Reload Data" in the navbar to re-import papers

### Slow loading
- The first load may be slow as it indexes ~14,000 papers
- Subsequent loads use the SQLite database

### Sci-Hub blocked
- Sci-Hub domain may change; current default is `sci-hub.se`
- Try alternative domains if blocked in your region

## File Structure

```
scripts/web_interface/
├── app.py              # Main Flask application
├── run.sh              # Startup script
├── README.md           # This file
├── templates/          # HTML templates
│   ├── base.html       # Base template with navigation
│   ├── index.html      # Dashboard
│   ├── papers.html     # Paper browser
│   ├── paper_detail.html
│   ├── batch_download.html
│   └── stats.html      # Statistics page
└── static/             # Static assets (if needed)
```

## Requirements

- Python 3.8+
- Flask
- pandas
- SQLite3 (built into Python)

All dependencies should already be available in the project's virtual environment.
