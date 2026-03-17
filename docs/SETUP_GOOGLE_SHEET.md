# Setting Up Shared Click Tracking via Google Sheets

This enables team members to share their download progress on the
[remaining papers dashboard](https://simondedman.github.io/elasmo_analyses/remaining_downloads.html).

## Step 1: Create Google Sheet

1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet
2. Name it "EEA Paper Download Tracking"
3. In Sheet1, add these headers in row 1:

| A | B | C | D |
|---|---|---|---|
| doi | title | by | at |

4. Share the sheet with your team (view access is enough; the Apps Script handles writes)

## Step 2: Create Google Apps Script Web App

1. In the spreadsheet, go to **Extensions > Apps Script**
2. Delete any default code and paste the following:

```javascript
// Google Apps Script for EEA Paper Download Tracking
// Deploy as: Web App, execute as: Me, access: Anyone

function doGet(e) {
  var action = e.parameter.action;

  if (action === 'getAll') {
    return getAllClicked();
  }

  return ContentService.createTextOutput(JSON.stringify({error: 'Unknown action'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  var body = JSON.parse(e.postData.contents);
  var action = body.action;

  if (action === 'markClicked') {
    return markClicked(body.doi, body.title, body.by, body.at);
  } else if (action === 'unmark') {
    return unmarkDoi(body.doi);
  }

  return ContentService.createTextOutput(JSON.stringify({error: 'Unknown action'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function getAllClicked() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Sheet1');
  var data = sheet.getDataRange().getValues();
  var result = [];

  for (var i = 1; i < data.length; i++) {  // skip header
    if (data[i][0]) {
      result.push({
        doi: data[i][0],
        title: data[i][1],
        by: data[i][2],
        at: data[i][3]
      });
    }
  }

  return ContentService.createTextOutput(JSON.stringify({data: result}))
    .setMimeType(ContentService.MimeType.JSON);
}

function markClicked(doi, title, by, at) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Sheet1');
  var data = sheet.getDataRange().getValues();

  // Check if DOI already exists
  for (var i = 1; i < data.length; i++) {
    if (data[i][0] === doi) {
      // Update existing row
      sheet.getRange(i + 1, 3).setValue(by);
      sheet.getRange(i + 1, 4).setValue(at);
      return ContentService.createTextOutput(JSON.stringify({status: 'updated'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }

  // Add new row
  sheet.appendRow([doi, title, by, at]);
  return ContentService.createTextOutput(JSON.stringify({status: 'added'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function unmarkDoi(doi) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Sheet1');
  var data = sheet.getDataRange().getValues();

  for (var i = data.length - 1; i >= 1; i--) {
    if (data[i][0] === doi) {
      sheet.deleteRow(i + 1);
      break;
    }
  }

  return ContentService.createTextOutput(JSON.stringify({status: 'removed'}))
    .setMimeType(ContentService.MimeType.JSON);
}
```

3. Click **Deploy > New deployment**
4. Type: **Web app**
5. Execute as: **Me**
6. Who has access: **Anyone**
7. Click **Deploy** and copy the URL (looks like `https://script.google.com/macros/s/XXXXX/exec`)

## Step 3: Configure the Dashboard

1. Open `docs/remaining_downloads.html`
2. Find this line near the top of the `<script>` section:

```javascript
var GOOGLE_SHEET_URL = '';  // e.g. 'https://script.google.com/macros/s/XXXX/exec'
```

3. Replace with your deployed URL:

```javascript
var GOOGLE_SHEET_URL = 'https://script.google.com/macros/s/YOUR_ID_HERE/exec';
```

4. Commit and push to GitHub

## How It Works

- **On page load:** fetches all clicked DOIs from Google Sheet, greys out those rows
- **On "Mark clicked":** records DOI + team member name + timestamp to Sheet and greys out row
- **On "Undo":** removes the row from Sheet and un-greys the row
- **Fallback:** if Sheet is unreachable, uses browser localStorage (local only)
- **"Hide clicked" checkbox:** filters clicked papers from view entirely
- **Journal filter:** type in the journal footer filter to work through one journal at a time

## Important Notes

- The Google Sheet is the **shared click log**, not the master list
- Papers are only **officially removed** from `papers_data.json` after Simon ingests the PDFs
- Team members should upload downloaded PDFs to the shared NAS
- The click log helps avoid duplicate effort — it does not confirm acquisition
