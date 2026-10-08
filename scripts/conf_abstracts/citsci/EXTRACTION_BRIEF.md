# Extraction brief: citizen / community science in elasmobranch conference abstracts

You will read ONE JSON file of conference abstracts (sharks, rays, chimaeras) and write ONE JSON file of structured extractions. Colleagues at the Shark Trust are building a global inventory of citizen/community science projects for elasmobranch conservation and want to find project leads to invite. Your output feeds a spreadsheet they will read.

Input: a JSON list; each item has abstract_id, meeting, year, title, abstract, keywords, authors (semicolon-separated, first = lead), first_affiliation.

Output: a JSON list with EXACTLY one object per input abstract_id, same order, with these keys:

- "abstract_id": copy verbatim.
- "relevance": one of
  - "Project" — the abstract describes a citizen/community science project, programme, platform, or network that the authors run or co-run (public, divers, anglers, fishers, tourists, students, or volunteers collecting or contributing data on an ongoing or repeated basis).
  - "Uses citsci data" — the study analyses data from a citizen/community science programme run by someone else (e.g. a national sightings scheme, iNaturalist, dive-operator logbooks, social-media mining of public photos).
  - "Fisher / LEK knowledge" — interviews, questionnaires, or local ecological knowledge surveys of fishers or communities, with no ongoing public data-collection programme.
  - "Mentions only" — citizen science is recommended, proposed for the future, or named in passing; no actual programme or data.
  - "Not citsci" — false positive (e.g. "volunteer" meaning lab/field assistants, "community" meaning an ecological community, "participatory" meaning stakeholder management workshops with no data collection).
- "elasmo_relevant": true if the abstract concerns sharks, rays, skates, sawfish, or chimaeras; false otherwise.
- "project_name": the programme/platform/network name exactly as written in the abstract, or null if unnamed. Never invent a name.
- "organisation": the organisation(s) running the project if stated (NGO, aquarium, university, agency, dive operator), else null.
- "country_region": countries or seas where the project operates, as stated, else null.
- "species_taxa": the focal species/taxa named, as a short comma list, else null.
- "participants": who contributes data (e.g. "recreational divers", "anglers", "beach walkers", "dive operators", "general public", "fishers", "school students"), else null.
- "data_type": what is collected (e.g. "sightings", "photo-ID images", "eggcase finds", "tag recaptures", "catch records", "social-media photos", "interviews", "acoustic receivers hosted by volunteers"), else null.
- "platform_or_app": named app, website, or database used (e.g. iNaturalist, Wildbook, Sharkbook, eOceans, Redmap, a bespoke app), else null.
- "scale_or_outputs": one short phrase with any numbers given (participants, records, years running), else null.
- "summary": ONE sentence (max 30 words) saying what the citizen-science element is. For "Not citsci", say why it is a false positive.
- "likely_lead": the author most likely leading the project (usually the first author), copied from the authors string, or null.

Rules
- Use only what the abstract says. null beats a guess. Do not infer a country from an affiliation; the affiliation column is already in the spreadsheet.
- Keep species names as given; do not add Latin names the abstract lacks.
- Output must be valid JSON (a bare list, no markdown fences, no commentary) written with the Write tool to the output path you were given. Do not print the JSON to chat; reply with one line: how many items you wrote and the count per relevance value.
- Read the input with the Read tool (it is a plain JSON file). Do not modify the input file.
