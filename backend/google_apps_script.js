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
 *
 * NOTE: After updating this script, you MUST create a NEW deployment (not edit existing)
 * and update the Web App URL in your website settings.
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

const CONFIG_SHEET_NAME = "App Config";

/**
 * Initializes and formats the required worksheets if they don't exist.
 * Also creates the "App Config" sheet for persisting settings like invoice notice.
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

  // Initialize the App Config sheet (key-value store for persisting settings)
  let configSheet = ss.getSheetByName(CONFIG_SHEET_NAME);
  if (!configSheet) {
    configSheet = ss.insertSheet(CONFIG_SHEET_NAME);
    configSheet.appendRow(["config_key", "config_value", "updated_at"]);

    const headerRange = configSheet.getRange(1, 1, 1, 3);
    headerRange.setBackground("#1E3A8A");
    headerRange.setFontColor("#FFFFFF");
    headerRange.setFontWeight("bold");
    headerRange.setHorizontalAlignment("center");
    configSheet.setFrozenRows(1);
    configSheet.setColumnWidth(1, 200);
    configSheet.setColumnWidth(2, 500);
  }

  // Remove default 'Sheet1' if present and other sheets exist
  const defaultSheet = ss.getSheetByName("Sheet1");
  if (defaultSheet && ss.getSheets().length > 1) {
    try { ss.deleteSheet(defaultSheet); } catch (e) {}
  }
}

/**
 * Reads all rows from the App Config sheet, returns as a plain object {key: value}.
 */
function readAllAppConfig() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG_SHEET_NAME);
  if (!sheet || sheet.getLastRow() <= 1) return {};

  const data = sheet.getDataRange().getValues();
  const result = {};
  for (let i = 1; i < data.length; i++) {
    const key = String(data[i][0]).trim();
    const val = data[i][1];
    if (key) result[key] = val;
  }
  return result;
}

/**
 * Saves (upserts) a single key-value pair in the App Config sheet.
 */
function saveAppConfigValue(key, value) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(CONFIG_SHEET_NAME);
  if (!sheet) {
    initializeSheets();
    sheet = ss.getSheetByName(CONFIG_SHEET_NAME);
  }

  const now = new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
  const lastRow = sheet.getLastRow();

  // Search for existing key to update
  if (lastRow > 1) {
    const keys = sheet.getRange(2, 1, lastRow - 1, 1).getValues();
    for (let i = 0; i < keys.length; i++) {
      if (String(keys[i][0]).trim() === key) {
        // Update existing row
        sheet.getRange(i + 2, 2, 1, 2).setValues([[value, now]]);
        return;
      }
    }
  }

  // Insert new row
  sheet.appendRow([key, value, now]);
}

/**
 * GET Handler: Returns records or config as JSON.
 * Params:
 *   mode=COMMERCIAL  → billing records
 *   mode=DOMESTIC    → domestic billing records
 *   mode=CONFIG      → all app config key-value pairs
 */
function doGet(e) {
  initializeSheets();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const mode = (e && e.parameter && e.parameter.mode) ? e.parameter.mode.toUpperCase() : "COMMERCIAL";

  // Return all app config key-value pairs
  if (mode === "CONFIG") {
    const config = readAllAppConfig();
    return ContentService.createTextOutput(JSON.stringify({
      status: "ok",
      config: config
    })).setMimeType(ContentService.MimeType.JSON);
  }

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
 * POST Handler: Appends, syncs records, or saves config values.
 * Body actions:
 *   action=sync       → overwrite all data rows for a mode
 *   action=append     → append new rows
 *   action=saveConfig → save a key-value config entry
 *   action=saveAllConfig → save multiple key-value config entries at once
 */
function doPost(e) {
  try {
    initializeSheets();
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const payload = JSON.parse(e.postData.contents);
    const action = payload.action || "sync";

    // ── Config persistence actions ────────────────────────────────────────
    if (action === "saveConfig") {
      const key   = String(payload.key || "").trim();
      const value = payload.value !== undefined ? payload.value : "";
      if (!key) {
        return ContentService.createTextOutput(JSON.stringify({
          status: "error", message: "config key is required"
        })).setMimeType(ContentService.MimeType.JSON);
      }
      saveAppConfigValue(key, value);
      return ContentService.createTextOutput(JSON.stringify({
        status: "ok",
        message: "Config saved: " + key
      })).setMimeType(ContentService.MimeType.JSON);
    }

    if (action === "saveAllConfig") {
      const entries = payload.entries || {};
      for (const [key, value] of Object.entries(entries)) {
        saveAppConfigValue(key, value);
      }
      return ContentService.createTextOutput(JSON.stringify({
        status: "ok",
        message: "Saved " + Object.keys(entries).length + " config entries"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // ── Billing record actions ────────────────────────────────────────────
    const mode      = (payload.mode || "COMMERCIAL").toUpperCase();
    const sheetName = (mode === "DOMESTIC") ? "Domestic Maintenance bill" : "Maintenance bill";
    const columns   = (mode === "DOMESTIC") ? DOMESTIC_COLS : COMMERCIAL_COLS;

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
        const r   = records[i];
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
