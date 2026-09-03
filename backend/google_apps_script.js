/**
 * Google Apps Script for Basant Jamini Bhawan Welfare Association
 * Automatically formats sheets and provides real-time Web API sync for the website.
 *
 * HOW TO USE (1 Minute Setup):
 * 1. In your Google Spreadsheet, click 'Extensions' > 'Apps Script'
 * 2. Delete any code in Code.gs and PASTE THIS ENTIRE SCRIPT.
 * 3. Click 'Deploy' (top right blue button) > 'New deployment'
 * 4. Click the gear icon next to 'Select type' > choose 'Web app'
 * 5. Configuration:
 *    - Description: BJBWA Billing Sync
 *    - Execute as: Me (your Google account)
 *    - Who has access: Anyone
 * 6. Click 'Deploy', authorize access, and COPY the Web App URL.
 * 7. In your website, click 'Google Sheets [⚙️ Settings]', paste the Web App URL, and click 'Save Configuration'.
 */

const COMMERCIAL_COLS = [
  "Tenant_Name", "Flat_No", "Due_Month", "Billing_Year", "Open_Meter_Reading",
  "Closing_Meter_Reading", "Consumed_Units", "Electric_Charges_Rs", "Fixed_Meter_Charges_Rs",
  "Municipal_Tax_Rs", "Water_Charges_Rs", "Building_Maint_Fund_Rs", "Lift_Charges_Rs",
  "Others_Charges_Rs", "Total_Amount_Due_Rs", "Partial_Payment_Rs", "Payment_Date",
  "Actual_Due_Rs", "Payment_Status", "Reset"
];

const DOMESTIC_COLS = [
  "Tenant_Name", "Flat_No", "Due_Month", "Billing_Year", "Open_Meter_Reading",
  "Closing_Meter_Reading", "Consumed_Units", "Common_Area_Units", "Electric_Charges_Rs",
  "Fixed_Meter_Charges_Rs", "Municipal_Tax_Rs", "Building_Maint_Fund_Rs", "Lift_Charges_Rs",
  "Others_Charges_Rs", "Total_Amount_Due_Rs", "Partial_Payment_Rs", "Payment_Date",
  "Actual_Due_Rs", "Payment_Status", "Reset"
];

/**
 * Initializes and formats the two required worksheets if they don't exist.
 */
function initializeSheets() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  const setupSheet = (title, columns) => {
    let sheet = ss.getSheetByName(title);
    if (!sheet) {
      sheet = ss.insertSheet(title);
    }
    
    // Set headers if first row is empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(columns);
    }
    
    // Format Header Row (Royal Blue, White Bold, Centered)
    const headerRange = sheet.getRange(1, 1, 1, columns.length);
    headerRange.setBackground("#1E3A8A");
    headerRange.setFontColor("#FFFFFF");
    headerRange.setFontWeight("bold");
    headerRange.setHorizontalAlignment("center");
    headerRange.setVerticalAlignment("middle");
    sheet.setFrozenRows(1);
  };

  setupSheet("Maintenance bill", COMMERCIAL_COLS);
  setupSheet("Domestic Maintenance bill", DOMESTIC_COLS);

  // Remove default 'Sheet1' if present and other sheets exist
  const defaultSheet = ss.getSheetByName("Sheet1");
  if (defaultSheet && ss.getSheets().length > 1) {
    try { ss.deleteSheet(defaultSheet); } catch (e) {}
  }
}

/**
 * GET Handler: Returns records as JSON
 */
function doGet(e) {
  initializeSheets();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const mode = (e && e.parameter && e.parameter.mode) ? e.parameter.mode.toUpperCase() : "COMMERCIAL";
  const sheetName = (mode === "DOMESTIC") ? "Domestic Maintenance bill" : "Maintenance bill";
  const sheet = ss.getSheetByName(sheetName);
  
  if (!sheet) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: "Sheet not found: " + sheetName
    })).setMimeType(ContentService.MimeType.JSON);
  }

  const data = sheet.getDataRange().getValues();
  if (data.length <= 1) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "ok",
      mode: mode,
      records: []
    })).setMimeType(ContentService.MimeType.JSON);
  }

  const headers = data[0];
  const records = [];

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const rec = {};
    for (let j = 0; j < headers.length; j++) {
      rec[headers[j]] = row[j];
    }
    records.push(rec);
  }

  return ContentService.createTextOutput(JSON.stringify({
    status: "ok",
    mode: mode,
    count: records.length,
    records: records
  })).setMimeType(ContentService.MimeType.JSON);
}

/**
 * POST Handler: Appends or syncs records
 */
function doPost(e) {
  try {
    initializeSheets();
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const payload = JSON.parse(e.postData.contents);
    const mode = (payload.mode || "COMMERCIAL").toUpperCase();
    const action = payload.action || "sync";
    const sheetName = (mode === "DOMESTIC") ? "Domestic Maintenance bill" : "Maintenance bill";
    const columns = (mode === "DOMESTIC") ? DOMESTIC_COLS : COMMERCIAL_COLS;
    
    let sheet = ss.getSheetByName(sheetName);
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      sheet.appendRow(columns);
    }

    if (action === "sync") {
      // Overwrite all data rows with synced records
      sheet.clearContents();
      sheet.appendRow(columns);

      const records = payload.records || [];
      if (records.length > 0) {
        const rows = records.map(r => columns.map(c => (r[c] !== undefined && r[c] !== null) ? r[c] : ""));
        sheet.getRange(2, 1, rows.length, columns.length).setValues(rows);
      }

      // Re-apply header styling
      const headerRange = sheet.getRange(1, 1, 1, columns.length);
      headerRange.setBackground("#1E3A8A");
      headerRange.setFontColor("#FFFFFF");
      headerRange.setFontWeight("bold");
      headerRange.setHorizontalAlignment("center");
      sheet.setFrozenRows(1);

      return ContentService.createTextOutput(JSON.stringify({
        status: "ok",
        message: "Successfully synchronized " + (payload.records ? payload.records.length : 0) + " records to " + sheetName
      })).setMimeType(ContentService.MimeType.JSON);
    } 
    else if (action === "append") {
      const records = payload.records || [];
      for (let i = 0; i < records.length; i++) {
        const r = records[i];
        const row = columns.map(c => (r[c] !== undefined && r[c] !== null) ? r[c] : "");
        sheet.appendRow(row);
      }
      return ContentService.createTextOutput(JSON.stringify({
        status: "ok",
        message: "Appended " + records.length + " record(s) to " + sheetName
      })).setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: "Unknown action: " + action
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
