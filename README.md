# Basant Jamini Bhawan Welfare Association - Automation Hub (Web App)

A modern web application based on the association's billing desktop hub, preserving **100% of the original business logic, multi-tab layout, and PDF invoice styling**, backed by **Google Sheets** for cloud ledger storage.

---

## 🌟 Key Features

1. **Top Target Mode Selector**:
   - Seamlessly toggle between **`COMMERCIAL`** and **`DOMESTIC`** billing classifications.
   - Dynamic **`Common Open`** and **`Common Close`** meter reading inputs for domestic common area electricity distribution.
2. **Tab 1: ⚡ Automated File Upload**:
   - Drag-and-drop file upload (`.pdf`, `.docx`, `.txt`, `.csv`).
   - **Interactive Step 2 Verification Modal**: Review and edit parsed readings before committing records.
   - Historical Common Area Average Units lookup for past domestic periods.
   - Single manual entry input override form.
3. **Tab 2: 📊 Master Ledger Database**:
   - Real-time filtering by Flat, Month, and Year.
   - Double-click / inline reading editing with instant bill recalculation.
   - Batch actions: **Mark Paid**, **Save Partial Payment**, **Reset (0/1)**, and **Delete Records**.
   - **Print Selected Statements**: High-contrast PDF statements featuring **JHD multi-flat grouping** (`A-1`, `F-1`, `F-2`).
4. **Tab 3: 📋 Dues Management**:
   - Per-flat or global outstanding dues tracking.
   - Real-time KPI summary cards: **Cumulative Total Due**, **Cumulative Total Paid**, and **Outstanding Balance Left**.
   - **Sequential FIFO Payment Allocation**: Applies lump-sum payments to the oldest unpaid months first.
5. **Tab 4: ⚙️ Live Rate Settings**:
   - Dynamic electricity Rate Per Unit (RPU) rates for Commercial (Rs. 6.90) and Domestic (Rs. 5.40).
   - Time-bound rate validity periods (Start Month & Start Year).
   - Multi-flat selection checklist to update parameters across multiple units simultaneously.
   - Live parameter registry inspector grid.
6. **Tab 5: 📋 Invoice Notices**:
   - Global notice guidelines paragraph editor with permanent persistent storage.
7. **High-Contrast White PDF Invoicing**:
   - Compiles single-flat and grouped invoices with **clean white background**, **bold 2px border lines**, **bold headline typography**, and **bold numbers**.

---

## 🚀 How to Run

### Option 1: 1-Click Windows Launcher
Double-click **`run.bat`** in the project folder. It will start the server and automatically launch `http://127.0.0.1:8000` in your default browser.

### Option 2: Command Line
```powershell
cd C:\Users\anupr\.gemini\antigravity\scratch\bjbwa-billing-web\backend
py -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Then open `http://127.0.0.1:8000` in your web browser.

---

## 📊 Google Sheets Cloud Integration

The web app is configured to use Google Sheets (`Maintenance bill` and `Domestic Maintenance bill`) instead of local Excel files.

### 1. Zero-Config Local Mirror (Out-of-the-Box)
You do not need to configure Google Cloud right away. The app automatically starts in **Local Mirror Mode**, persisting all records and changes to `data/local_sheets_store.json`. All records from your desktop app have been pre-seeded.

### 2. Connecting to Live Google Sheets
To connect your live Google Sheets:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a Service Account with the **Google Sheets API** and **Google Drive API** enabled.
2. Download the service account JSON key file, rename it to **`service_account.json`**, and place it in the `data/` folder:
   ```
   bjbwa-billing-web/data/service_account.json
   ```
3. Run the automated setup script from the project folder:
   ```powershell
   py backend/setup_google_sheets.py --credentials data/service_account.json --share your-email@gmail.com
   ```
   This will automatically create a spreadsheet named **"Basant Jamini Bhawan Maintenance Ledger"** with pre-formatted sheets:
   - `Maintenance bill` (Commercial)
   - `Domestic Maintenance bill` (Domestic)
4. Or, click the **`Google Sheets [⚙️ Settings]`** pill in the top header bar of the web app to paste an existing Spreadsheet ID and click **🔄 Full Sync Now**.

---

## 📁 Project Structure

```
bjbwa-billing-web/
├── backend/
│   ├── app.py                      # FastAPI REST API server
│   ├── billing_core.py             # Core calculation engine & rates
│   ├── file_parser.py              # Multi-format document parser
│   ├── pdf_generator.py            # PDF compiler (white background, bold 2px borders, bold numbers)
│   ├── google_sheets_service.py    # Google Sheets manager + local mirror
│   └── setup_google_sheets.py      # Automated Google Sheets setup CLI
├── frontend/
│   ├── index.html                  # Single Page Application matching desktop layout
│   ├── css/
│   │   └── style.css               # Exact association colors (#1e3a8a, #0d9488, #db2777, #1e293b)
│   └── js/
│       └── app.js                  # Frontend controller & interactivity
├── data/
│   ├── commercial_config.json      # Flat configurations (Commercial)
│   ├── domestic_config.json        # Flat configurations (Domestic)
│   ├── billing_rpu_rates.json      # RPU rates
│   ├── invoice_notices.json        # Persistent notice paragraph
│   ├── google_sheets_config.json   # Google Sheets configuration
│   └── local_sheets_store.json     # Mirrored local data store
├── requirements.txt
├── run.bat
└── README.md
```
