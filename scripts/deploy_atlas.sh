#!/usr/bin/env bash
# Rebuild Author Atlas end-to-end: data -> frontend -> static site.
#
# Usage: scripts/deploy_atlas.sh
#
# Does NOT commit or push. Review the diff in docs/network_atlas/ first,
# then commit + push manually to deploy to GitHub Pages.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$(pwd)

echo "==> 1/3  Rebuilding Atlas data (R)"
Rscript scripts/build_author_atlas.R

echo "==> 2/3  Refreshing frontend data copy"
cd "$ROOT/frontend/network_atlas"
npm run copy-data

echo "==> 3/3  Building frontend (Vite)"
npm run build

echo
echo "Done. Built site is at:"
echo "  $ROOT/docs/network_atlas/"
echo
echo "Review the diff, then commit + push to deploy to GitHub Pages."
