import { useState } from 'react';

// Searchable multi-select: type to narrow the list, click to add, click a chip to remove.
// options = [[label, count], ...] (already sorted); italic renders labels in italics (species).
export default function MultiSelect({ label, options, selected, onChange, italic = false, placeholder }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const sel = new Set(selected);
  const ql = q.trim().toLowerCase();
  const matches = options
    .filter(([l]) => !sel.has(l) && (!ql || l.toLowerCase().includes(ql)))
    .slice(0, 40);
  const style = italic ? { fontStyle: 'italic' } : undefined;
  return (
    <div className="multisel">
      <label>{label}{selected.length > 0 && <span className="muted"> · {selected.length} selected</span>}</label>
      {selected.length > 0 && (
        <div className="chips">
          {selected.map(l => (
            <span key={l} className="chip" style={style} title="Click to remove"
                  onClick={() => onChange(selected.filter(x => x !== l))}>{l} ×</span>
          ))}
        </div>
      )}
      <input
        type="text" value={q} placeholder={placeholder ?? 'Type to search…'}
        onChange={e => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && matches.length > 0 && (
        <div className="ms-list">
          {matches.map(([l, n]) => (
            <div key={l} className="ms-opt"
                 onMouseDown={e => { e.preventDefault(); onChange([...selected, l]); setQ(''); setOpen(false); }}>
              <span style={style}>{l}</span> <span className="muted">({n.toLocaleString()})</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
