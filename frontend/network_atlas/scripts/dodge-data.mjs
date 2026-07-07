// Build step: apply the geoDodge coordinate-dodge to the copied authors.geojson
// so co-located authors get distinct coordinates BEFORE supercluster ever sees
// them. Runs as part of `npm run copy-data`, right after the raw un-dodged data
// is copied from outputs/author_atlas/, so every rebuild (CI or local) produces
// dodged data. Without this the deploy Action kept overwriting the dodge with the
// un-dodged pipeline source, resurrecting the "megacluster never splits" bug.
import { dodgeCoincidentAuthors } from '../src/lib/geoDodge.js';
import fs from 'fs';

const path = 'public/data/authors.geojson';
const d = JSON.parse(fs.readFileSync(path, 'utf8'));
const before = new Set(d.features.map(f => f.geometry.coordinates.join(','))).size;
dodgeCoincidentAuthors(d);
const after = new Set(d.features.map(f => f.geometry.coordinates.join(','))).size;
fs.writeFileSync(path, JSON.stringify(d));
console.log(`dodge-data: ${path} unique coords ${before} -> ${after} (of ${d.features.length} authors)`);
if (after < d.features.length * 0.9) {
  console.error('dodge-data: WARNING — dodge did not separate coincident authors as expected');
  process.exit(1);
}
