#!/usr/bin/env python3
"""
Paper Download Web Interface

A Flask-based web interface for managing and tracking paper downloads
for the EEA Data Panel project.
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from urllib.parse import quote_plus
import json
import csv
from io import StringIO

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "outputs"
PAPERS_DIR = Path("/media/simon/data/Documents/Si Work/Papers & Books/SharkPapers")
DB_PATH = BASE_DIR / "database" / "download_tracker.db"

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = 'eea-data-panel-2025'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the download tracking database."""
    conn = get_db()
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            literature_id TEXT UNIQUE,
            year INTEGER,
            authors TEXT,
            title TEXT,
            journal TEXT,
            volume TEXT,
            issue TEXT,
            pages TEXT,
            doi TEXT,
            citation TEXT,
            priority_group INTEGER DEFAULT 0,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS download_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER,
            status TEXT DEFAULT 'pending',  -- pending, downloaded, unavailable, skipped
            download_date TIMESTAMP,
            source TEXT,  -- doi, scihub, publisher, manual
            notes TEXT,
            attempts INTEGER DEFAULT 0,
            last_attempt TIMESTAMP,
            FOREIGN KEY (paper_id) REFERENCES papers(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS download_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT,
            started TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            papers_targeted INTEGER DEFAULT 0,
            papers_downloaded INTEGER DEFAULT 0,
            notes TEXT
        )
    ''')

    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_journal ON papers(journal)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_paper ON download_status(paper_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_status ON download_status(status)')

    conn.commit()
    conn.close()


def load_papers_from_csv():
    """Load papers from acquisition priority CSVs into database."""
    conn = get_db()
    cursor = conn.cursor()

    # Define priority files
    priority_files = [
        (DATA_DIR / "acquisition_priority_1_recent_with_doi.csv", 1),
        (DATA_DIR / "acquisition_priority_2_2000s_with_doi.csv", 2),
        (DATA_DIR / "acquisition_priority_3_key_journals.csv", 3),
        (DATA_DIR / "acquisition_priority_4_no_doi_complete_metadata.csv", 4),
    ]

    total_added = 0

    for csv_path, priority in priority_files:
        if not csv_path.exists():
            continue

        try:
            df = pd.read_csv(csv_path)

            for _, row in df.iterrows():
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO papers
                        (literature_id, year, authors, title, journal, volume, issue, pages, doi, citation, priority_group)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(row.get('literature_id', '')),
                        int(row.get('year', 0)) if pd.notna(row.get('year')) else None,
                        str(row.get('authors', ''))[:1000],
                        str(row.get('title', ''))[:500],
                        str(row.get('journal', ''))[:255],
                        str(row.get('volume', ''))[:50] if pd.notna(row.get('volume')) else None,
                        str(row.get('issue', ''))[:50] if pd.notna(row.get('issue')) else None,
                        str(row.get('pages', ''))[:50] if pd.notna(row.get('pages')) else None,
                        str(row.get('doi_clean', ''))[:100] if pd.notna(row.get('doi_clean')) else None,
                        str(row.get('citation', ''))[:1000],
                        priority
                    ))
                    if cursor.rowcount > 0:
                        total_added += 1
                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error loading {csv_path}: {e}")

    conn.commit()
    conn.close()
    return total_added


def check_existing_pdf(paper):
    """Check if we already have a PDF for this paper."""
    if not paper['title'] or not PAPERS_DIR.exists():
        return None

    # Check in year folder
    year = paper.get('year')
    if year:
        year_dir = PAPERS_DIR / str(int(year))
        if year_dir.exists():
            # Look for matching filename
            title_clean = ''.join(c for c in paper['title'][:50] if c.isalnum() or c in ' -_').strip()
            for pdf_file in year_dir.glob("*.pdf"):
                if title_clean.lower()[:30] in pdf_file.stem.lower():
                    return str(pdf_file)

    return None


def get_download_links(paper):
    """Generate download links for a paper."""
    links = []

    doi = paper.get('doi') or paper.get('doi_clean')
    if doi and doi.strip():
        doi_clean = doi.strip()
        # DOI resolver
        links.append({
            'name': 'DOI',
            'url': f'https://doi.org/{doi_clean}',
            'icon': 'link'
        })
        # Sci-Hub
        links.append({
            'name': 'Sci-Hub',
            'url': f'https://sci-hub.se/{doi_clean}',
            'icon': 'download'
        })
        # Unpaywall
        links.append({
            'name': 'Unpaywall',
            'url': f'https://api.unpaywall.org/v2/{doi_clean}?email=research@example.com',
            'icon': 'unlock'
        })

    # Google Scholar search
    title = paper.get('title', '')
    if title:
        scholar_query = quote_plus(title[:100])
        links.append({
            'name': 'Scholar',
            'url': f'https://scholar.google.com/scholar?q={scholar_query}',
            'icon': 'search'
        })

    return links


# Routes
@app.route('/')
def index():
    """Main dashboard."""
    conn = get_db()
    cursor = conn.cursor()

    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM papers')
    total_papers = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.status = 'downloaded' OR ds.status IS NULL AND EXISTS (
            SELECT 1 FROM download_status WHERE paper_id = p.id AND status = 'downloaded'
        )
    ''')
    downloaded = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.status = 'unavailable'
    ''')
    unavailable = cursor.fetchone()[0]

    # Get papers by year distribution
    cursor.execute('''
        SELECT year, COUNT(*) as count
        FROM papers
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
        LIMIT 20
    ''')
    year_dist = cursor.fetchall()

    # Get papers by priority
    cursor.execute('''
        SELECT priority_group, COUNT(*) as count
        FROM papers
        GROUP BY priority_group
        ORDER BY priority_group
    ''')
    priority_dist = cursor.fetchall()

    conn.close()

    return render_template('index.html',
                          total_papers=total_papers,
                          downloaded=downloaded,
                          unavailable=unavailable,
                          pending=total_papers - downloaded - unavailable,
                          year_dist=year_dist,
                          priority_dist=priority_dist)


@app.route('/papers')
def papers_list():
    """List papers with filtering."""
    conn = get_db()
    cursor = conn.cursor()

    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    year = request.args.get('year', type=int)
    priority = request.args.get('priority', type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    has_doi = request.args.get('has_doi', '')
    journal = request.args.get('journal', '')

    # Build query
    query = '''
        SELECT p.*,
               COALESCE(ds.status, 'pending') as download_status,
               ds.attempts,
               ds.last_attempt,
               ds.notes as status_notes
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE 1=1
    '''
    params = []

    if year:
        query += ' AND p.year = ?'
        params.append(year)

    if priority:
        query += ' AND p.priority_group = ?'
        params.append(priority)

    if status:
        if status == 'pending':
            query += ' AND (ds.status IS NULL OR ds.status = ?)'
            params.append(status)
        else:
            query += ' AND ds.status = ?'
            params.append(status)

    if search:
        query += ' AND (p.title LIKE ? OR p.authors LIKE ? OR p.journal LIKE ?)'
        search_term = f'%{search}%'
        params.extend([search_term, search_term, search_term])

    if has_doi == 'yes':
        query += ' AND p.doi IS NOT NULL AND p.doi != ""'
    elif has_doi == 'no':
        query += ' AND (p.doi IS NULL OR p.doi = "")'

    if journal:
        query += ' AND p.journal LIKE ?'
        params.append(f'%{journal}%')

    # Get total count
    count_query = query.replace('SELECT p.*,', 'SELECT COUNT(*)')
    count_query = count_query.split('FROM papers')[0] + 'FROM papers' + count_query.split('FROM papers')[1]
    count_query = 'SELECT COUNT(*) FROM papers p LEFT JOIN download_status ds ON p.id = ds.paper_id WHERE 1=1' + query.split('WHERE 1=1')[1]

    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # Add pagination
    query += ' ORDER BY p.year DESC, p.id LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    cursor.execute(query, params)
    papers = cursor.fetchall()

    # Get unique years and journals for filters
    cursor.execute('SELECT DISTINCT year FROM papers WHERE year IS NOT NULL ORDER BY year DESC')
    years = [row[0] for row in cursor.fetchall()]

    cursor.execute('SELECT DISTINCT journal FROM papers WHERE journal IS NOT NULL ORDER BY journal LIMIT 100')
    journals = [row[0] for row in cursor.fetchall()]

    conn.close()

    # Add download links to each paper
    papers_with_links = []
    for paper in papers:
        paper_dict = dict(paper)
        paper_dict['links'] = get_download_links(paper_dict)
        papers_with_links.append(paper_dict)

    total_pages = (total + per_page - 1) // per_page

    return render_template('papers.html',
                          papers=papers_with_links,
                          page=page,
                          per_page=per_page,
                          total=total,
                          total_pages=total_pages,
                          years=years,
                          journals=journals,
                          current_filters={
                              'year': year,
                              'priority': priority,
                              'status': status,
                              'search': search,
                              'has_doi': has_doi,
                              'journal': journal
                          })


@app.route('/paper/<int:paper_id>')
def paper_detail(paper_id):
    """View paper details."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.*,
               COALESCE(ds.status, 'pending') as download_status,
               ds.attempts,
               ds.last_attempt,
               ds.notes as status_notes,
               ds.source,
               ds.download_date
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE p.id = ?
    ''', (paper_id,))

    paper = cursor.fetchone()
    conn.close()

    if not paper:
        return "Paper not found", 404

    paper_dict = dict(paper)
    paper_dict['links'] = get_download_links(paper_dict)
    paper_dict['existing_pdf'] = check_existing_pdf(paper_dict)

    return render_template('paper_detail.html', paper=paper_dict)


@app.route('/api/update_status', methods=['POST'])
def update_status():
    """Update download status for a paper."""
    data = request.json
    paper_id = data.get('paper_id')
    status = data.get('status')
    source = data.get('source', '')
    notes = data.get('notes', '')

    if not paper_id or not status:
        return jsonify({'error': 'Missing paper_id or status'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Check if status record exists
    cursor.execute('SELECT id FROM download_status WHERE paper_id = ?', (paper_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE download_status
            SET status = ?, source = ?, notes = ?,
                attempts = attempts + 1,
                last_attempt = CURRENT_TIMESTAMP,
                download_date = CASE WHEN ? = 'downloaded' THEN CURRENT_TIMESTAMP ELSE download_date END
            WHERE paper_id = ?
        ''', (status, source, notes, status, paper_id))
    else:
        cursor.execute('''
            INSERT INTO download_status (paper_id, status, source, notes, attempts, last_attempt, download_date)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CASE WHEN ? = 'downloaded' THEN CURRENT_TIMESTAMP ELSE NULL END)
        ''', (paper_id, status, source, notes, status))

    conn.commit()
    conn.close()

    return jsonify({'success': True})


@app.route('/api/batch_update', methods=['POST'])
def batch_update():
    """Update status for multiple papers."""
    data = request.json
    paper_ids = data.get('paper_ids', [])
    status = data.get('status')

    if not paper_ids or not status:
        return jsonify({'error': 'Missing paper_ids or status'}), 400

    conn = get_db()
    cursor = conn.cursor()

    for paper_id in paper_ids:
        cursor.execute('SELECT id FROM download_status WHERE paper_id = ?', (paper_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE download_status
                SET status = ?, last_attempt = CURRENT_TIMESTAMP
                WHERE paper_id = ?
            ''', (status, paper_id))
        else:
            cursor.execute('''
                INSERT INTO download_status (paper_id, status)
                VALUES (?, ?)
            ''', (paper_id, status))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'updated': len(paper_ids)})


@app.route('/export/batch')
def export_batch():
    """Export papers as a batch download file."""
    format_type = request.args.get('format', 'html')
    status_filter = request.args.get('status', 'pending')
    limit = request.args.get('limit', 100, type=int)

    conn = get_db()
    cursor = conn.cursor()

    # Get papers with DOIs
    query = '''
        SELECT p.* FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE p.doi IS NOT NULL AND p.doi != ''
    '''

    if status_filter == 'pending':
        query += ' AND (ds.status IS NULL OR ds.status = "pending")'

    query += f' ORDER BY p.priority_group, p.year DESC LIMIT {limit}'

    cursor.execute(query)
    papers = cursor.fetchall()
    conn.close()

    if format_type == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['title', 'authors', 'year', 'journal', 'doi', 'doi_url', 'scihub_url'])

        for paper in papers:
            doi = paper['doi']
            writer.writerow([
                paper['title'],
                paper['authors'],
                paper['year'],
                paper['journal'],
                doi,
                f'https://doi.org/{doi}',
                f'https://sci-hub.se/{doi}'
            ])

        output.seek(0)
        return send_file(
            StringIO(output.getvalue()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'batch_download_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        )

    else:  # HTML format
        return render_template('batch_download.html', papers=papers)


@app.route('/reload')
def reload_data():
    """Reload papers from CSV files."""
    added = load_papers_from_csv()
    return redirect(url_for('index', message=f'Added {added} papers'))


@app.route('/stats')
def statistics():
    """Detailed statistics page."""
    conn = get_db()
    cursor = conn.cursor()

    # Papers by year
    cursor.execute('''
        SELECT year, COUNT(*) as total,
               SUM(CASE WHEN ds.status = 'downloaded' THEN 1 ELSE 0 END) as downloaded,
               SUM(CASE WHEN ds.status = 'unavailable' THEN 1 ELSE 0 END) as unavailable
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
    ''')
    by_year = cursor.fetchall()

    # Papers by priority
    cursor.execute('''
        SELECT priority_group, COUNT(*) as total,
               SUM(CASE WHEN ds.status = 'downloaded' THEN 1 ELSE 0 END) as downloaded
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        GROUP BY priority_group
        ORDER BY priority_group
    ''')
    by_priority = cursor.fetchall()

    # Top journals needing papers
    cursor.execute('''
        SELECT journal, COUNT(*) as pending
        FROM papers p
        LEFT JOIN download_status ds ON p.id = ds.paper_id
        WHERE ds.status IS NULL OR ds.status = 'pending'
        GROUP BY journal
        ORDER BY pending DESC
        LIMIT 20
    ''')
    top_journals = cursor.fetchall()

    # Recent activity
    cursor.execute('''
        SELECT p.title, p.year, ds.status, ds.last_attempt
        FROM download_status ds
        JOIN papers p ON ds.paper_id = p.id
        WHERE ds.last_attempt IS NOT NULL
        ORDER BY ds.last_attempt DESC
        LIMIT 20
    ''')
    recent = cursor.fetchall()

    conn.close()

    return render_template('stats.html',
                          by_year=by_year,
                          by_priority=by_priority,
                          top_journals=top_journals,
                          recent=recent)


# Initialize database on startup
init_db()


if __name__ == '__main__':
    # Load initial data if database is empty
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM papers')
    if cursor.fetchone()[0] == 0:
        print("Loading papers from CSV files...")
        added = load_papers_from_csv()
        print(f"Loaded {added} papers")
    conn.close()

    print("Starting Paper Download Interface...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)
