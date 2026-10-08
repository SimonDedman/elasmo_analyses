// Research profile for the selected author (fields come from build_author_atlas.R):
// dt/tt/st/bs = top [label, n] pairs (disciplines, techniques, species, ocean basins),
// fs/ls = first/last-author share, nc = coauthors, dc = papers per decade.
const VALIDATE_BASE = 'https://simondedman.github.io/elasmo_analyses/validate/';

const pairs = (arr, italic) => (arr ?? []).map(([l, n], i) => (
  <span key={l}>{i > 0 && ', '}{italic ? <i>{l}</i> : l} <span className="muted">({n})</span></span>
));

function Row({ title, children }) {
  return <div className="pc-row"><div className="pc-t">{title}</div><div>{children}</div></div>;
}

export default function ProfileCard({ author: p, palette, onClose }) {
  const col = palette?.[p.disc_main] ?? [150, 150, 150];
  const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`);
  return (
    <div className="profile-card">
      <button className="pc-close" onClick={onClose} aria-label="Close profile">×</button>
      <div className="pc-name">{p.name}</div>
      <div className="muted">{[p.institution, p.country].filter(Boolean).join(', ') || '—'}</div>
      <div className="pc-main">
        <span className="pc-dot" style={{ background: `rgb(${col[0]},${col[1]},${col[2]})` }} />
        Main discipline: <strong>{p.disc_main ?? 'Unclassified'}</strong>
      </div>
      <Row title="Papers">
        {p.papers}{p.year_min ? ` · active ${p.year_min}–${p.year_max}` : ''}
        {p.nc != null ? ` · ${p.nc} coauthors` : ''}
      </Row>
      {p.dt?.length > 0 && <Row title="Disciplines">{pairs(p.dt)}</Row>}
      {p.tt?.length > 0 && <Row title="Techniques">{pairs(p.tt)}</Row>}
      {p.st?.length > 0 && <Row title="Species">{pairs(p.st, true)}</Row>}
      {p.bs?.length > 0 && <Row title="Ocean basins">{pairs(p.bs)}</Row>}
      {p.sc?.length > 0 && <Row title="Study countries">{pairs(p.sc)}</Row>}
      <Row title="Authorship">First author {pct(p.fs)} · last author {pct(p.ls)}</Row>
      <div className="pc-link">
        <a href={`${VALIDATE_BASE}${p.id}.html`} target="_blank" rel="noreferrer">Validation page</a>
      </div>
    </div>
  );
}
