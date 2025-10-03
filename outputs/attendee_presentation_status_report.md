# Attendee Presentation Status Update

**Date**: 2025-10-03
**File Updated**: `EEA 2025 Attendee List.xlsx`

---

## Summary

Successfully added 4 logical columns to the attendee list to track presentation roles:
- `presenting` - Oral presentation
- `poster` - Poster presentation
- `panel` - Panel/breakout session participant
- `organiser` - Conference organiser

---

## Statistics

### Overall Coverage

| Status | Count | Percentage |
|--------|-------|------------|
| **Total Attendees** | 155 | 100% |
| Oral Presentations | 48 | 31.0% |
| Poster Presentations | 19 | 12.3% |
| Panel Members | 12 | 7.7% |
| Organisers | 2 | 1.3% |
| **Not Presenting** | 85 | 54.8% |

### Multiple Roles

| Combination | Count |
|-------------|-------|
| Presenting + Panel | 9 |
| Organiser + Presenting + Panel | 1 (Simon Dedman) |
| Organiser + Panel | 1 (Guuske Tiktak) |
| Presenting + Poster | 0 |
| Poster + Panel | 0 |

---

## Data Sources Cross-Referenced

### 1. Final Speakers EEA 2025.xlsx
- **Source**: `Decision` column and `PanelPrez` column
- **Matched**: 63 speakers with presentation status
- **Fields Used**:
  - Oral presentations: Parsed from "oral presentation" or "presentation" decision
  - Posters: Parsed from "poster" decision
  - Panel: Parsed from "panel/breakout session" or `PanelPrez` field

### 2. candidate_database_phase1.csv
- **Source**: `eea_2025_status` column
- **Matched**: 243 candidates
- **Fields Used**:
  - Oral: "presentation" or "oral" in status
  - Poster: "poster" in status
  - Panel: "panel" in status

### 3. Known Organisers
- Simon Dedman (panel + organiser)
- Guuske Tiktak (panel + organiser)

---

## Panel Members (12 total)

| Name | Also Presenting | Role |
|------|----------------|------|
| Simon Dedman | ✓ Yes | Organiser + Panelist + Presenter |
| Guuske Tiktak | No | Organiser + Panelist |
| Amy Jeffries | ✓ Yes | Panelist + Presenter |
| Charlotte Nuyt | ✓ Yes | Panelist + Presenter |
| Eva Meyers | ✓ Yes | Panelist + Presenter |
| Lydia Koehler | ✓ Yes | Panelist + Presenter |
| Nicholas Dulvy | ✓ Yes | Panelist + Presenter |
| Ryan Charles | ✓ Yes | Panelist + Presenter |
| Eleanor Greenway | ✓ Yes | Panelist + Presenter |
| Ali Hood | ✓ Yes | Panelist + Presenter |
| Paddy Walker | No | Panelist only |
| Irene Kingma | No | Panelist only |

**Note**: 9 of 12 panel members (75%) are also giving oral presentations.

---

## Formatting Applied

### Column Additions
- 4 new columns added to the right of existing data
- Column headers formatted with bold, blue background, white text

### Value Highlighting
- **TRUE values**: Green background (#C6EFCE), green text (#006100)
- **FALSE values**: No special formatting
- Makes it easy to visually identify presenting attendees

---

## Validation Notes

### Discrepancies Found
1. **Posters in speakers list**: 0 posters identified from `Final Speakers EEA 2025.xlsx`
   - However, 19 posters found via candidate database cross-reference
   - Likely because poster format codes (P_01, P_02, etc.) are in the database

2. **Panel members**:
   - Speakers list: 11 with panel designation
   - Final count: 12 (includes organisers who are also on panel)

### Quality Checks
✅ All organisers correctly identified
✅ Cross-reference successful between 3 data sources
✅ No duplicate entries with conflicting status
✅ Logical consistency (organisers are also panel members)

---

## Use Cases

### 1. Conference Planning
- Identify attendees without presentation roles (85 attendees)
- Target for engagement activities, workshops, or networking sessions

### 2. Session Management
- Quick filter for all presenters (48 oral + 19 poster = 67 total)
- Identify panel session participants (12 people)

### 3. Communication
- Segment attendees by role for targeted emails:
  - Presenters: AV setup, timing, session assignments
  - Poster presenters: Poster board specs, setup times
  - Panel members: Panel preparation materials
  - Non-presenters: General conference information

### 4. Badge Production
- Color-code badges by role:
  - Presenters: Blue
  - Poster: Green
  - Panel: Red
  - Organiser: Gold

---

## Example Queries

### Find All Presenters
Filter: `presenting = TRUE`
Result: 48 attendees

### Find Panel-Only Members
Filter: `panel = TRUE AND presenting = FALSE AND poster = FALSE`
Result: 2 attendees (Paddy Walker, Irene Kingma)

### Find Attendees Not Presenting
Filter: `presenting = FALSE AND poster = FALSE AND panel = FALSE`
Result: 85 attendees

### Find Multi-Role Attendees
Filter: Count of TRUE values > 1
Result: 10 attendees with multiple roles

---

## Files Modified

- ✅ `EEA 2025 Attendee List.xlsx` - Added 4 columns with green highlighting

## Scripts Created

- `scripts/add_presentation_status_to_attendees.R` - Cross-reference and update script

---

## Recommendations

1. **Verify poster presenters**: Cross-check the 19 poster identifications with actual poster submissions
2. **Contact non-presenters**: Reach out to the 85 non-presenting attendees to:
   - Confirm attendance
   - Offer networking opportunities
   - Encourage participation in discussions
3. **Panel preparation**: Ensure all 12 panel members receive panel materials and preparation guidelines
4. **Organiser checklist**: Ensure Simon and Guuske have all necessary organiser access and materials

---

*Update completed: 2025-10-03*
*Script: `scripts/add_presentation_status_to_attendees.R`*
