# Archived: genderize.io daily resolver (superseded by NamSor)

**Archived 2026-07-03.** Kept for reference only — do not re-enable.

## Why archived
NamSor enrichment (`scripts/enrich_namsor.py`, completed 2026-04-13) resolves
gender **and** origin **and** diaspora for all 28,922 authors in a single pass
(`outputs/namsor_enrichment.csv`), covering more authors than genderize ever
reached. Genderize.io was gender-only and rate-limited to 100 names/day
(free tier), so it was slow and strictly redundant. The anacron entry was
already removed during the 2026-07-01 anacron-automation fix.

## Files
- `genderize_daily.py` — daily 100-name batch resolver (offline guesser + API)
- `genderize_cron.sh`  — anacron wrapper (su-drop + notify-send)

## To resurrect (unlikely)
Re-install the anacrontab entry documented in `genderize_cron.sh`, and confirm
`outputs/.genderize_cache.json` still exists.
