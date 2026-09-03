"""
Google Sheets Service for Basant Jamini Bhawan Welfare Association
High-performance persistence engine:
  - In-Memory RAM Cache for ultra-fast, zero-latency (0ms) reads and instant UI response.
  - Disk-backed local mirror (JSON) for offline resilience and data integrity.
  - Asynchronous background synchronization to Google Sheets (Apps Script Web App or gspread).
  - Explicit pull/push capabilities for on-demand cloud synchronization.
"""

import os
import json
import threading
import requests
import pandas as pd
from datetime import datetime
from billing_core import COMMERCIAL_COLUMNS, DOMESTIC_COLUMNS

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SHEETS_CONFIG_FILE = os.path.join(CONFIG_DIR, "google_sheets_config.json")
LOCAL_STORE_FILE = os.path.join(CONFIG_DIR, "local_sheets_store.json")

# Desktop source files to seed initial data from, if available
DESKTOP_EXCEL_COMMERCIAL = r"C:\Users\anupr\OneDrive\Desktop\Maintenance Billing App\Maintenance bill.xlsx"
DESKTOP_EXCEL_DOMESTIC = r"C:\Users\anupr\OneDrive\Desktop\Maintenance Billing App\Domestic Maintenance bill.xlsx"


class GoogleSheetsManager:
    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self._lock = threading.Lock()
        self.config = self._load_config()
        self.client = None
        self.spreadsheet = None
        self.is_connected = False
        self.connection_error = None
        self.connection_type = "local"  # 'apps_script', 'gspread', or 'local'

        # Background sync state
        self.is_syncing = False
        self.last_sync_time = None
        self.last_sync_error = None

        # 1. Initialize local file if needed
        self._init_local_store_if_needed()

        # 2. Preload in-memory cache directly from local store
        self._memory_cache = self._read_local_store()

        # 3. Connect to Google Sheets
        self.try_connect_google_sheets()

    def _load_config(self):
        if os.path.exists(SHEETS_CONFIG_FILE):
            try:
                with open(SHEETS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "spreadsheet_id": "",
            "spreadsheet_url": "",
            "apps_script_url": "",
            "credentials_file": "service_account.json",
            "use_live_google_sheets": False
        }

    def save_config(self, new_config):
        self.config.update(new_config)
        with open(SHEETS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
        return self.try_connect_google_sheets()

    def _init_local_store_if_needed(self):
        """Initializes local store, seeding from desktop Excel files if available."""
        if os.path.exists(LOCAL_STORE_FILE):
            return

        initial_store = {
            "Maintenance bill": [],
            "Domestic Maintenance bill": []
        }

        # Attempt to seed commercial records from desktop Excel
        if os.path.exists(DESKTOP_EXCEL_COMMERCIAL):
            try:
                df_c = pd.read_excel(DESKTOP_EXCEL_COMMERCIAL)
                df_c = self._sanitize_records(df_c, COMMERCIAL_COLUMNS)
                initial_store["Maintenance bill"] = df_c.to_dict(orient="records")
            except Exception as e:
                print(f"Warning: Could not seed Commercial Excel data: {e}")

        # Attempt to seed domestic records from desktop Excel
        if os.path.exists(DESKTOP_EXCEL_DOMESTIC):
            try:
                df_d = pd.read_excel(DESKTOP_EXCEL_DOMESTIC)
                df_d = self._sanitize_records(df_d, DOMESTIC_COLUMNS)
                initial_store["Domestic Maintenance bill"] = df_d.to_dict(orient="records")
            except Exception as e:
                print(f"Warning: Could not seed Domestic Excel data: {e}")

        with open(LOCAL_STORE_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_store, f, indent=4)

    def _sanitize_records(self, df, required_columns):
        """Standardizes columns, types, and defaults for records."""
        df = df.copy()
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0 if col in ["Reset", "Consumed_Units", "Common_Area_Units"] else ("" if "Date" in col or "Tenant" in col or "Flat" in col or "Month" in col or "Status" in col else 0.0)

        df['Reset'] = pd.to_numeric(df['Reset'], errors='coerce').fillna(0).astype(int).clip(0, 1)
        df['Partial_Payment_Rs'] = pd.to_numeric(df['Partial_Payment_Rs'], errors='coerce').fillna(0.0).clip(lower=0.0)
        gross = pd.to_numeric(df['Total_Amount_Due_Rs'], errors='coerce').fillna(0.0)
        df['Actual_Due_Rs'] = (gross - df['Partial_Payment_Rs']).clip(lower=0.0)
        df.loc[df['Actual_Due_Rs'].eq(0), 'Payment_Status'] = 'PAID'
        return df[required_columns]

    def try_connect_google_sheets(self):
        """Attempts to authenticate either via Apps Script Webhook or Google Service Account."""
        self.is_connected = False
        self.connection_error = None
        self.connection_type = "local"

        if not self.config.get("use_live_google_sheets"):
            return False, "Live Google Sheets mode is disabled. Using Local Mirror."

        # 1. Check Apps Script Web App URL first (Easiest & most reliable)
        apps_script_url = self.config.get("apps_script_url", "").strip()
        if apps_script_url and apps_script_url.startswith("http"):
            try:
                # Fast connectivity test (5s timeout)
                res = requests.get(apps_script_url, params={"mode": "COMMERCIAL"}, timeout=6)
                if res.status_code in [200, 302]:
                    self.is_connected = True
                    self.connection_type = "apps_script"
                    return True, "Successfully connected to Google Sheets via Apps Script Web App."
                else:
                    self.connection_error = f"Apps Script returned status code {res.status_code}."
            except Exception as e:
                self.connection_error = f"Failed to reach Apps Script URL: {e}"

        # 2. Check Service Account credentials
        cred_filename = self.config.get("credentials_file", "service_account.json")
        cred_path = cred_filename if os.path.isabs(cred_filename) else os.path.join(CONFIG_DIR, cred_filename)
        sheet_id = self.config.get("spreadsheet_id", "").strip()

        if os.path.exists(cred_path) and sheet_id:
            try:
                import gspread
                from google.oauth2.service_account import Credentials

                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
                credentials = Credentials.from_service_account_file(cred_path, scopes=scopes)
                self.client = gspread.authorize(credentials)
                self.spreadsheet = self.client.open_by_key(sheet_id)
                self.is_connected = True
                self.connection_type = "gspread"
                return True, "Successfully connected to Google Sheets via Service Account."
            except Exception as e:
                self.connection_error = str(e)
                return False, f"Failed to connect via Service Account: {e}"

        if not self.is_connected:
            if not self.connection_error:
                self.connection_error = "No valid Google Apps Script Web App URL or Service Account key provided."
            return False, self.connection_error

        return True, "Connected."

    def get_status(self, retest=False):
        """Returns the current connection status and statistics instantly from memory."""
        if retest:
            self.try_connect_google_sheets()

        with self._lock:
            comm_count = len(self._memory_cache.get("Maintenance bill", []))
            dom_count = len(self._memory_cache.get("Domestic Maintenance bill", []))

        mode_str = "Local Mirror Store (Ready to Sync)"
        if self.is_connected:
            if self.connection_type == "apps_script":
                mode_str = "Live Google Sheets (Apps Script Webhook)"
            else:
                mode_str = "Live Google Sheets (Service Account)"

        return {
            "is_connected": self.is_connected,
            "connection_type": self.connection_type,
            "use_live_google_sheets": self.config.get("use_live_google_sheets", False),
            "apps_script_url": self.config.get("apps_script_url", ""),
            "spreadsheet_id": self.config.get("spreadsheet_id", ""),
            "spreadsheet_url": self.config.get("spreadsheet_url", ""),
            "connection_error": self.connection_error,
            "commercial_rows": comm_count,
            "domestic_rows": dom_count,
            "mode": mode_str,
            "is_syncing": self.is_syncing,
            "last_sync_time": self.last_sync_time,
            "last_sync_error": self.last_sync_error
        }

    def _read_local_store(self):
        if os.path.exists(LOCAL_STORE_FILE):
            try:
                with open(LOCAL_STORE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"Maintenance bill": [], "Domestic Maintenance bill": []}

    def _write_local_store(self, data):
        try:
            with open(LOCAL_STORE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error writing to local store: {e}")

    def get_sheet_name_for_mode(self, mode):
        return "Maintenance bill" if str(mode).upper() == "COMMERCIAL" else "Domestic Maintenance bill"

    def get_columns_for_mode(self, mode):
        return COMMERCIAL_COLUMNS if str(mode).upper() == "COMMERCIAL" else DOMESTIC_COLUMNS

    def load_records(self, mode, force_refresh=False):
        """
        Loads records for COMMERCIAL or DOMESTIC.
        Ultra-fast: serves immediately from RAM memory cache (0ms).
        Only contacts remote Google Sheets if force_refresh is True or cache is empty.
        """
        sheet_name = self.get_sheet_name_for_mode(mode)
        cols = self.get_columns_for_mode(mode)

        # 1. If we have records in memory and force_refresh is False, return immediately
        with self._lock:
            cached = self._memory_cache.get(sheet_name)
            if cached and not force_refresh:
                return [r.copy() for r in cached]

        # 2. If force_refresh or memory cache is empty, fetch from remote
        if self.is_connected and self.connection_type == "apps_script":
            try:
                url = self.config.get("apps_script_url")
                res = requests.get(url, params={"mode": mode}, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "ok":
                        df = pd.DataFrame(data.get("records", []))
                        df = self._sanitize_records(df, cols)
                        records = df.to_dict(orient="records")
                        with self._lock:
                            self._memory_cache[sheet_name] = records
                            self._write_local_store(self._memory_cache)
                        return [r.copy() for r in records]
            except Exception as e:
                print(f"Apps Script load warning: {e}. Serving from local cache.")

        elif self.is_connected and self.spreadsheet:
            try:
                worksheet = self.spreadsheet.worksheet(sheet_name)
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
                df = self._sanitize_records(df, cols)
                records = df.to_dict(orient="records")
                with self._lock:
                    self._memory_cache[sheet_name] = records
                    self._write_local_store(self._memory_cache)
                return [r.copy() for r in records]
            except Exception as e:
                print(f"Error loading from live Google Sheets: {e}. Serving from local cache.")

        # Fallback to local memory cache or disk store
        with self._lock:
            records = self._memory_cache.get(sheet_name, [])
            if not records:
                disk_data = self._read_local_store()
                records = disk_data.get(sheet_name, [])
                self._memory_cache[sheet_name] = records
            df = pd.DataFrame(records)
            df = self._sanitize_records(df, cols)
            return df.to_dict(orient="records")

    def save_records(self, mode, records, sync_background=True):
        """
        Saves records to In-Memory Cache and Local Mirror immediately (0ms).
        Dispatches Google Sheets synchronization to a background thread to prevent UI freezing.
        """
        sheet_name = self.get_sheet_name_for_mode(mode)
        cols = self.get_columns_for_mode(mode)

        df = pd.DataFrame(records)
        df = self._sanitize_records(df, cols)
        clean_records = df.to_dict(orient="records")

        # 1. Update in-memory cache and write to disk store instantly
        with self._lock:
            self._memory_cache[sheet_name] = clean_records
            self._write_local_store(self._memory_cache)

        # 2. Background sync to Google Sheets if connected
        if self.is_connected:
            if sync_background:
                t = threading.Thread(
                    target=self._sync_worker,
                    args=(mode, sheet_name, cols, clean_records),
                    daemon=True
                )
                t.start()
            else:
                ok, err = self._sync_worker_sync(mode, sheet_name, cols, clean_records)
                if not ok:
                    return False, err

        return True, "Records saved successfully."

    def _sync_worker(self, mode, sheet_name, cols, clean_records):
        """Asynchronous worker that pushes records to Google Sheets in the background."""
        self._sync_worker_sync(mode, sheet_name, cols, clean_records)

    def _sync_worker_sync(self, mode, sheet_name, cols, clean_records):
        """Synchronous implementation of Google Sheets push."""
        self.is_syncing = True
        try:
            if self.connection_type == "apps_script":
                url = self.config.get("apps_script_url")
                res = requests.post(url, json={
                    "action": "sync",
                    "mode": mode,
                    "records": clean_records
                }, timeout=30)
                if res.status_code == 200:
                    self.last_sync_time = datetime.now().strftime("%H:%M:%S")
                    self.last_sync_error = None
                    return True, "Synced to Google Sheets"
                else:
                    self.last_sync_error = f"Status {res.status_code}"
                    return False, self.last_sync_error
            elif self.connection_type == "gspread" and self.spreadsheet:
                worksheet = self.spreadsheet.worksheet(sheet_name)
                header_row = cols
                values = [header_row] + [[r.get(c, "") for c in cols] for r in clean_records]
                worksheet.clear()
                worksheet.update('A1', values)
                self.last_sync_time = datetime.now().strftime("%H:%M:%S")
                self.last_sync_error = None
                return True, "Synced to Google Sheets"
            return True, "Saved locally"
        except Exception as e:
            print(f"Background cloud sync warning: {e}")
            self.last_sync_error = str(e)
            return False, str(e)
        finally:
            self.is_syncing = False

    def append_records(self, mode, new_records, sync_background=True):
        """Appends new records and saves."""
        existing = self.load_records(mode)
        existing.extend(new_records)
        return self.save_records(mode, existing, sync_background=sync_background)

    def pull_from_google_sheets(self):
        """Pulls latest records from Google Sheets for all modes into memory & local store."""
        ok, msg = self.try_connect_google_sheets()
        if not ok:
            return False, msg

        for mode in ["COMMERCIAL", "DOMESTIC"]:
            self.load_records(mode, force_refresh=True)

        self.last_sync_time = datetime.now().strftime("%H:%M:%S")
        return True, "Successfully pulled latest data from Google Sheets."

    def sync_all_to_google_sheets(self):
        """Pushes all local in-memory records to Google Sheets synchronously."""
        ok, msg = self.try_connect_google_sheets()
        if not ok:
            return False, msg

        for mode in ["COMMERCIAL", "DOMESTIC"]:
            sheet_name = self.get_sheet_name_for_mode(mode)
            cols = self.get_columns_for_mode(mode)
            with self._lock:
                records = self._memory_cache.get(sheet_name, [])
            ok_save, err = self._sync_worker_sync(mode, sheet_name, cols, records)
            if not ok_save:
                return False, err

        return True, "All records successfully synchronized to Google Sheets."
