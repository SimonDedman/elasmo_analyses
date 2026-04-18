export default function Legend({ colorBy, palettes }) {
  const pal = palettes[colorBy] ?? {};
  const entries = Object.entries(pal);
  if (entries.length === 0) return null;

  const label = {
    gender: 'Gender',
    country: 'Country',
    origin_region: 'Origin region (NamSor)',
  }[colorBy];

  // If the palette already includes an Unknown/Other entry, skip the
  // generic catch-all row — avoids the duplicate "Unknown / other/unknown".
  const hasCatchAll = entries.some(([k]) =>
    /^(unknown|other)$/i.test(k));

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
        {!hasCatchAll && (
          <div className="legend-row">
            <span className="swatch" style={{ background: '#969696' }} />
            <span className="label muted">other / unknown</span>
          </div>
        )}
      </div>
    </div>
  );
}
