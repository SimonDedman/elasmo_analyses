export default function Legend({ colorBy, palettes }) {
  const pal = palettes[colorBy] ?? {};
  const entries = Object.entries(pal);
  if (entries.length === 0) return null;

  const label = {
    gender: 'Gender',
    country: 'Country',
    origin_region: 'Origin region (NamSor)',
  }[colorBy];

  return (
    <div className="legend">
      <div className="legend-title">{label}</div>
      <div className="legend-swatches">
        {entries.map(([key, rgba]) => (
          <div key={key} className="legend-row">
            <span
              className="swatch"
              style={{
                background: `rgb(${rgba[0]}, ${rgba[1]}, ${rgba[2]})`,
                opacity: (rgba[3] ?? 255) / 255,
              }}
            />
            <span className="label">{key}</span>
          </div>
        ))}
        <div className="legend-row">
          <span className="swatch" style={{ background: '#969696' }} />
          <span className="label muted">other / unknown</span>
        </div>
      </div>
    </div>
  );
}
