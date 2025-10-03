---
editor_options: 
  markdown: 
    wrap: 72
---

# Missing Names Search Report

## EEA 2025 Attendee List

**Date**: 2025-10-03 **Task**: Identify missing surnames from EEA 2025
Attendee List

------------------------------------------------------------------------

## Summary

Searched through all submitted abstracts (89 DOCX files, 23 PDF files)
to identify missing attendee names.

### Results

| Original Entry | Identified As | Status | Source |
|---------------------|---------------------|----------------|----------------|
| **Renzo** | **Lorenzo Elias** | ✓ FOUND | Abstract O_30 (Greenway et al.) |
| **?? (Shark Trust #1)** | **Hettie Brown** | ✓ FOUND | Abstracts O_08, P02 |
| **?? (Shark Trust #2)** | **Paul Cox** | \~ TENTATIVE | Abstract O_28 (Gordon & Cox) |
| **WOZEP** | Unknown | ✗ NOT FOUND | No matches in abstracts |

------------------------------------------------------------------------

## Detailed Findings

### 1. Renzo → Lorenzo Elias

**Abstract**: O_30_Greenway_EEA2025_abstract_form.docx

**Full Author List**: - Eleanor Greenway - **Lorenzo Elias** - Antonella
Consiglio - Andrea Bellodi - Blondine Agus - Jurgen Batsleer - Karen
Bekaert - Pierluigi Carbonara - Manfredi Madia - Mauro Sinopoli -
Michele Palmisano - Ilse Maertens - Jan Jaap Poos

**Title**: Age determination in Raja brachyura, Raja clavata, and Raja
montagui from the Northeast Atlantic: a comparison of different
techniques

**Institution**: Wageningen University and Research **Email**: Not
provided in abstract (Eleanor:
[Eleanor.greenway\@wur.nl](mailto:Eleanor.greenway@wur.nl){.email})

**Updated in attendee list**: ✓ Yes (Row 140, highlighted in yellow)

------------------------------------------------------------------------

### 2. ?? (Shark Trust) → Hettie Brown

**Abstracts**:

#### O_08: Guitarfish fisheries in the Gulf of Gabès, Tunisia

**Authors**: Saidi, B; Enajjar, S; **Brown, H**; Bartolí, À; Hood, A &
Bradai, M.N **Email**:
[hettie\@sharktrust.org](mailto:hettie@sharktrust.org){.email}
**Institution**: Shark Trust

#### P02: Angel Sharks in the Eastern and Central Mediterranean: Three Years On

**Authors**: **Brown, H**; Bartolí, À; Beton, D; Ciprian, M; Enajjar, S;
Giovos, I; Gordon, C; Papageorgiou, M; Snape, R; Ulman, A; Hood, A
**Email**:
[hettie\@sharktrust.org](mailto:hettie@sharktrust.org){.email}
**Institution**: Shark Trust

**Updated in attendee list**: ✓ Yes (Row 154, highlighted in yellow)

**Note**: Hettie Brown was already in candidate database, so no
duplicate was added.

------------------------------------------------------------------------

### 3. ?? (Shark Trust #2) → Paul Cox (TENTATIVE)

**Abstract**: O_28: The Future of Living with Sharks

**Full Author List**: - Cat A. Gordon - **Paul B. Cox**

**Institution**: The Shark Trust **Address**: 4 Creykes Court, The
Millfields, Plymouth, PL1 3JB **Contact**:
[cat\@sharktrust.org](mailto:cat@sharktrust.org){.email} (Cat Gordon)

**Status**: TENTATIVE - Paul Cox appears as co-author on Cat Gordon's
abstract, but no independent confirmation. Should verify with Shark
Trust or conference organizers.

**Updated in attendee list**: \~ Yes (Row 155, highlighted in yellow) -
marked as tentative

**Added to candidate database**: ✓ Yes (241 → 243 candidates)

------------------------------------------------------------------------

### 4. WOZEP → Unknown

**Search Results**: No matches found in any abstracts (DOCX or PDF
files)

**Possible Explanations**: 1. Misspelling or typo in attendee list 2.
Nickname or abbreviated name 3. Organization acronym mistakenly entered
as name 4. Person who withdrew before abstract submission 5.
Non-presenting attendee

**Recommendation**: Contact conference organizers directly to clarify
this entry.

------------------------------------------------------------------------

## Other Shark Trust Personnel Identified in Abstracts

For context, here are all Shark Trust-affiliated people found in the
abstracts:

| Name          | Found In        | Role             | In Attendee List?     |
|---------------|-----------------|------------------|-----------------------|
| Cat Gordon    | O_02, O_28, P01 | Author/Co-author | ✓ Yes                 |
| Harriet Allen | O_02, P01       | Author/Co-author | ✓ Yes                 |
| Jack Renwick  | O_58            | Author           | ✓ Yes                 |
| Ali Hood      | O_08, O_31, P02 | Author/Co-author | ✓ Yes                 |
| Hettie Brown  | O_08, P02       | Author           | ✓ Yes (was ??)        |
| Paul Cox      | O_28            | Co-author        | \~ Tentative (was ??) |
| John Hepburn  | O_02            | Co-author        | ✗ Not listed          |

**Note**: John Hepburn is listed with Mewstone Enterprises (not Shark
Trust directly), so may not be in attendee list.

------------------------------------------------------------------------

## Actions Taken

1.  [x] Created search script: `scripts/search_abstracts_simple.sh`
2.  [x] Searched all 89 DOCX abstracts using `unzip` + XML extraction
3.  [x] Searched all 23 PDF abstracts using `pdftotext`
4.  [x] Updated attendee list: `EEA 2025 Attendee List.xlsx`
    -   Lorenzo Elias (row 140) - yellow highlight
    -   Hettie Brown (row 154) - yellow highlight
    -   Paul Cox (row 155) - yellow highlight (tentative)
5.  [x] Integrated new attendees into candidate database
    -   Added Lorenzo Elias
    -   Added Paul Cox
    -   Hettie Brown already present (no duplicate)
6.  [x] Updated candidate database: 241 → 243 candidates

------------------------------------------------------------------------

## Files Modified

-   `EEA 2025 Attendee List.xlsx` - Updated with found names (yellow
    highlighting)
-   `outputs/candidate_database_phase1.csv` - Added 2 new candidates

## Scripts Created

-   `scripts/search_abstracts_simple.sh` - Bash script to search
    DOCX/PDF files
-   `scripts/update_attendee_list_missing_names.R` - R script to update
    attendee list
-   `scripts/integrate_newly_identified_attendees.R` - R script to add
    to database

------------------------------------------------------------------------

## Remaining Issues

### WOZEP - Unresolved

**Status**: No information found in abstracts

**Next Steps**: 1. Check if there are any abstracts with unusual file
encodings that might not have been read correctly 2. Search for
phonetically similar names in abstracts (e.g., "Woosep", "Wozup", etc.)
3. Contact conference organizers 4. Check registration system for
additional details 5. Review if this might be an
organization/affiliation rather than a person's name

**Priority**: Medium - if this person is not presenting, they may simply
be an attendee with no abstract

------------------------------------------------------------------------

## Statistics

-   **Abstracts searched**: 112 files (89 DOCX + 23 PDF)
-   **Names successfully identified**: 3 of 4 (75%)
-   **High confidence identifications**: 2 (Lorenzo Elias, Hettie Brown)
-   **Tentative identifications**: 1 (Paul Cox)
-   **Unresolved**: 1 (WOZEP)

------------------------------------------------------------------------

## Recommendation

The abstract search was successful in resolving most missing names. For
the remaining "WOZEP" entry, recommend:

1.  Direct contact with conference organizers
2.  Review of registration records
3.  If unresolvable, mark as "withdrawn" or "TBD" in attendee list

All identified names have been integrated into the candidate database
and are ready for further data enrichment (publication metrics,
conference history, etc.).
