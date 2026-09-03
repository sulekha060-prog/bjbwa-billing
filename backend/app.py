"""
FastAPI Server for Basant Jamini Bhawan Welfare Association - Automation Hub Web App
Replicates all desktop application business logic, calculations, dues tracking, and PDF generation,
powered by Google Sheets (with local mirror store fallback).
"""

import os
import io
import json
import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request, Depends, Header
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

PROJECT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")

import billing_core as core
import file_parser
import pdf_generator
from google_sheets_service import GoogleSheetsManager
from auth_service import AuthManager

app = FastAPI(title="Basant Jamini Bhawan Welfare Association - Automation Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".js") or path.endswith(".css") or path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Static files
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

# Initialize Storage & Configs
sheets_mgr = GoogleSheetsManager()
auth_mgr = AuthManager()

def _extract_token(authorization: Any, x_admin_token: Any) -> Optional[str]:
    if isinstance(x_admin_token, str) and x_admin_token.strip():
        return x_admin_token.strip()
    if isinstance(authorization, str) and authorization.strip():
        return authorization.replace("Bearer ", "").strip()
    return None

def verify_admin(
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None)
):
    token = _extract_token(authorization, x_admin_token)
    if not auth_mgr.is_valid_token(token):
        raise HTTPException(status_code=401, detail="Admin authentication required. Please log in.")
    return True

def load_json(filename, default):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_commercial_config():
    return load_json("commercial_config.json", core.DEFAULT_COMMERCIAL_CONFIG)

def get_domestic_config():
    return load_json("domestic_config.json", core.DEFAULT_DOMESTIC_CONFIG)

def get_rpu_rates():
    return load_json("billing_rpu_rates.json", {"domestic": core.RATE_DOMESTIC, "commercial": core.RATE_COMMERCIAL})

def get_notices_text():
    data = load_json("invoice_notices.json", {"notice_text": core.DEFAULT_NOTICE_TEXT})
    return data.get("notice_text", core.DEFAULT_NOTICE_TEXT)

# Serve Frontend Root
@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

# ----------------- AUTHENTICATION ENDPOINTS -----------------

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
def auth_login(req: LoginRequest):
    token = auth_mgr.login(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid admin username or password.")
    return {"status": "ok", "token": token, "username": req.username}

@app.get("/api/auth/status")
def auth_status(
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None)
):
    token = _extract_token(authorization, x_admin_token)
    is_admin = auth_mgr.is_valid_token(token)
    return {"is_admin": is_admin, "username": "admin" if is_admin else None}

@app.post("/api/auth/logout")
def auth_logout(
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None)
):
    token = _extract_token(authorization, x_admin_token)
    auth_mgr.logout(token)
    return {"status": "ok"}

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@app.post("/api/auth/change-password")
def auth_change_password(req: ChangePasswordRequest, _: bool = Depends(verify_admin)):
    success, msg = auth_mgr.change_password(req.old_password, req.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "ok", "message": msg}

# ----------------- CONFIG ENDPOINTS -----------------

@app.get("/api/config")
def get_all_configs():
    return {
        "commercial_config": get_commercial_config(),
        "domestic_config": get_domestic_config(),
        "rpu_rates": get_rpu_rates(),
        "notice_text": get_notices_text(),
        "google_sheets_status": sheets_mgr.get_status()
    }

class SaveRPURatesRequest(BaseModel):
    domestic: float
    commercial: float

@app.post("/api/config/rpu")
def update_rpu_rates(req: SaveRPURatesRequest, _: bool = Depends(verify_admin)):
    if req.domestic < 0 or req.commercial < 0:
        raise HTTPException(status_code=400, detail="RPU values cannot be negative.")
    data = {"domestic": round(req.domestic, 2), "commercial": round(req.commercial, 2)}
    save_json("billing_rpu_rates.json", data)
    return {"status": "ok", "rpu_rates": data}

class SaveRatesRequest(BaseModel):
    mode: str
    target_flats: List[str]
    field_key: str
    value: float
    start_month: str
    start_year: int

@app.post("/api/config/rates")
def update_flat_rates(req: SaveRatesRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    cfg_filename = "commercial_config.json" if mode == "COMMERCIAL" else "domestic_config.json"
    cfg = get_commercial_config() if mode == "COMMERCIAL" else get_domestic_config()

    if mode == "DOMESTIC" and req.field_key == "water":
        raise HTTPException(status_code=400, detail="Water fees can only be set for COMMERCIAL mode.")

    for flat in req.target_flats:
        if flat not in cfg:
            continue
        if req.field_key == "fixed":
            timeline = cfg[flat].setdefault("fixed", [])
            updated = False
            for node in timeline:
                if node.get("start_month") == req.start_month and int(node.get("start_year", 0)) == req.start_year:
                    node["val"] = req.value
                    updated = True
                    break
            if not updated:
                timeline.append({"start_month": req.start_month, "start_year": req.start_year, "val": req.value})
        else:
            cfg[flat][req.field_key] = req.value

    save_json(cfg_filename, cfg)
    return {"status": "ok", "updated_count": len(req.target_flats), "config": cfg}

class SaveNoticeRequest(BaseModel):
    notice_text: str

@app.post("/api/config/notices")
def save_notice(req: SaveNoticeRequest, _: bool = Depends(verify_admin)):
    save_json("invoice_notices.json", {"notice_text": req.notice_text.strip()})
    return {"status": "ok", "notice_text": req.notice_text.strip()}

# ----------------- UPLOAD & PROCESS -----------------

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), mode: str = Form("COMMERCIAL"), _: bool = Depends(verify_admin)):
    content = await file.read()
    flat_cfg = get_commercial_config() if mode.upper() == "COMMERCIAL" else get_domestic_config()

    try:
        parsed_result = file_parser.parse_meter_reading_document(content, file.filename, flat_cfg)
        return parsed_result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parsing error: {str(e)}")

class ProcessBillsRequest(BaseModel):
    mode: str
    target_month: str
    target_year: str
    extracted_metrics: Dict[str, List[float]]  # {flat: [open, close]}
    common_open: Optional[float] = None
    common_close: Optional[float] = None

@app.post("/api/process")
def process_extracted_bills(req: ProcessBillsRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    cfg_dict = get_commercial_config() if mode == "COMMERCIAL" else get_domestic_config()
    rpu = get_rpu_rates()
    current_rpu = rpu.get("commercial", core.RATE_COMMERCIAL) if mode == "COMMERCIAL" else rpu.get("domestic", core.RATE_DOMESTIC)
    notice = get_notices_text()

    existing_records = sheets_mgr.load_records(mode)

    # Helper: duplicate check
    def is_duplicate(flat, m, y):
        for r in existing_records:
            if str(r.get("Flat_No", "")).strip() == str(flat).strip() and \
               str(r.get("Due_Month", "")).strip().upper() == str(m).strip().upper() and \
               str(r.get("Billing_Year", "")).strip() == str(y).strip():
                return True
        return False

    # Compute common area shared units for Domestic
    shared_common_units = 0.0
    if mode == "DOMESTIC":
        if "Common" in req.extracted_metrics:
            cm_vals = req.extracted_metrics["Common"]
            if len(cm_vals) >= 2 and cm_vals[1] >= cm_vals[0]:
                shared_common_units = round((cm_vals[1] - cm_vals[0]) / 18.0, 2)
        if shared_common_units <= 0.0 and req.common_open is not None and req.common_close is not None:
            if req.common_close >= req.common_open:
                shared_common_units = round((req.common_close - req.common_open) / 18.0, 2)

    new_records = []
    skipped_duplicates = []

    for flat_key, cfg in cfg_dict.items():
        if cfg.get("is_common", False):
            continue
        if flat_key in req.extracted_metrics:
            if is_duplicate(flat_key, req.target_month, req.target_year):
                skipped_duplicates.append(flat_key)
                continue

            op = req.extracted_metrics[flat_key][0]
            cl = req.extracted_metrics[flat_key][1]

            if mode == "COMMERCIAL":
                rec = core.calculate_commercial_bill(
                    flat_no=flat_key, cfg=cfg, month_str=req.target_month,
                    year_str=req.target_year, prev_r=op, curr_r=cl, rpu_rate=current_rpu
                )
            else:
                rec = core.calculate_domestic_bill(
                    flat_no=flat_key, cfg=cfg, month_str=req.target_month,
                    year_str=req.target_year, prev_r=op, curr_r=cl, rpu_rate=current_rpu,
                    common_share_units=shared_common_units
                )
            new_records.append(rec)

    if not new_records and skipped_duplicates:
        return {
            "status": "warning",
            "message": f"All flats skipped because records already exist for: {', '.join(skipped_duplicates)}.",
            "added_count": 0,
            "skipped_flats": skipped_duplicates
        }

    # Append records to Google Sheets / Local Mirror
    if new_records:
        sheets_mgr.append_records(mode, new_records)

    return {
        "status": "success",
        "added_count": len(new_records),
        "skipped_flats": skipped_duplicates,
        "shared_common_units": shared_common_units,
        "records": new_records
    }

class ProcessManualBillRequest(BaseModel):
    mode: str
    flat_no: str
    month: str
    year: str
    open_reading: float
    close_reading: float
    others_charge: Optional[float] = 0.0
    common_open: Optional[float] = None
    common_close: Optional[float] = None

@app.post("/api/process-manual")
def process_manual_bill(req: ProcessManualBillRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    cfg_dict = get_commercial_config() if mode == "COMMERCIAL" else get_domestic_config()
    cfg = cfg_dict.get(req.flat_no, {"tenant": "N/A", "fixed": [], "tax": 0, "water": 0, "maintenance": 0, "lift": 0, "others": 0})
    rpu = get_rpu_rates()
    current_rpu = rpu.get("commercial", core.RATE_COMMERCIAL) if mode == "COMMERCIAL" else rpu.get("domestic", core.RATE_DOMESTIC)

    if req.open_reading > req.close_reading:
        raise HTTPException(status_code=400, detail="Opening reading cannot exceed closing reading.")

    existing_records = sheets_mgr.load_records(mode)
    for r in existing_records:
        if str(r.get("Flat_No", "")).strip() == req.flat_no.strip() and \
           str(r.get("Due_Month", "")).strip().upper() == req.month.strip().upper() and \
           str(r.get("Billing_Year", "")).strip() == req.year.strip():
            raise HTTPException(status_code=400, detail=f"Bill for Flat {req.flat_no} for {req.month}-{req.year} already exists.")

    if mode == "COMMERCIAL":
        rec = core.calculate_commercial_bill(
            flat_no=req.flat_no, cfg=cfg, month_str=req.month,
            year_str=req.year, prev_r=req.open_reading, curr_r=req.close_reading,
            rpu_rate=current_rpu, others_val=req.others_charge or 0.0
        )
    else:
        shared_common = 0.0
        if req.common_open is not None and req.common_close is not None and req.common_close >= req.common_open:
            shared_common = round((req.common_close - req.common_open) / 18.0, 2)
        rec = core.calculate_domestic_bill(
            flat_no=req.flat_no, cfg=cfg, month_str=req.month,
            year_str=req.year, prev_r=req.open_reading, curr_r=req.close_reading,
            rpu_rate=current_rpu, common_share_units=shared_common, others_val=req.others_charge or 0.0
        )

    sheets_mgr.append_records(mode, [rec])
    return {"status": "success", "record": rec}

# ----------------- MASTER LEDGER -----------------

@app.get("/api/ledger")
def get_ledger(
    mode: str = "COMMERCIAL",
    flat: Optional[str] = None,
    month: Optional[str] = None,
    year: Optional[str] = None,
    refresh: bool = False
):
    records = sheets_mgr.load_records(mode, force_refresh=refresh)
    filtered = []
    for idx, r in enumerate(records):
        r_copy = r.copy()
        r_copy["_index"] = idx

        if flat and flat.lower() not in str(r.get("Flat_No", "")).lower():
            continue
        if month and month.lower() not in str(r.get("Due_Month", "")).lower():
            continue
        if year and year.lower() not in str(r.get("Billing_Year", "")).lower():
            continue
        filtered.append(r_copy)

    return {
        "mode": mode,
        "total_count": len(records),
        "filtered_count": len(filtered),
        "columns": core.COMMERCIAL_COLUMNS if mode.upper() == "COMMERCIAL" else core.DOMESTIC_COLUMNS,
        "records": filtered
    }

class UpdateRowRequest(BaseModel):
    mode: str
    index: int
    open_reading: float
    close_reading: float
    payment_status: str
    reset: int
    partial_payment: float

@app.put("/api/ledger/row/{index}")
def update_ledger_row(index: int, req: UpdateRowRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    records = sheets_mgr.load_records(mode)
    if index < 0 or index >= len(records):
        raise HTTPException(status_code=404, detail="Record index not found.")

    if req.open_reading > req.close_reading:
        raise HTTPException(status_code=400, detail="Opening reading cannot exceed closing reading.")

    rec = records[index]
    flat_no = str(rec.get("Flat_No", ""))
    month_str = str(rec.get("Due_Month", ""))
    year_str = str(rec.get("Billing_Year", ""))

    cfg_dict = get_commercial_config() if mode == "COMMERCIAL" else get_domestic_config()
    cfg = cfg_dict.get(flat_no, {"tenant": rec.get("Tenant_Name", ""), "fixed": [], "tax": 0, "water": 0, "maintenance": 0, "lift": 0, "others": 0})
    rpu = get_rpu_rates()
    current_rpu = rpu.get("commercial", core.RATE_COMMERCIAL) if mode == "COMMERCIAL" else rpu.get("domestic", core.RATE_DOMESTIC)
    others_val = float(rec.get("Others_Charges_Rs", 0) or 0)

    if mode == "COMMERCIAL":
        updated = core.calculate_commercial_bill(
            flat_no=flat_no, cfg=cfg, month_str=month_str, year_str=year_str,
            prev_r=req.open_reading, curr_r=req.close_reading, rpu_rate=current_rpu, others_val=others_val
        )
    else:
        com_units = float(rec.get("Common_Area_Units", 0) or 0)
        updated = core.calculate_domestic_bill(
            flat_no=flat_no, cfg=cfg, month_str=month_str, year_str=year_str,
            prev_r=req.open_reading, curr_r=req.close_reading, rpu_rate=current_rpu,
            common_share_units=com_units, others_val=others_val
        )

    gross = updated["Total_Amount_Due_Rs"]
    partial = min(float(req.partial_payment), gross)
    new_status = req.payment_status.upper()

    if new_status == "PAID":
        updated["Partial_Payment_Rs"] = gross
        updated["Actual_Due_Rs"] = 0.0
        updated["Payment_Status"] = "PAID"
        updated["Payment_Date"] = datetime.now().strftime('%d-%m-%Y')
    else:
        updated["Partial_Payment_Rs"] = partial
        updated["Actual_Due_Rs"] = max(0.0, gross - partial)
        updated["Payment_Status"] = "PAID" if updated["Actual_Due_Rs"] == 0 else "UNPAID"

    updated["Reset"] = 1 if req.reset == 1 else 0
    records[index] = updated

    sheets_mgr.save_records(mode, records)
    return {"status": "ok", "record": updated}

class BatchStatusRequest(BaseModel):
    mode: str
    indices: List[int]
    status: str

@app.post("/api/ledger/batch-status")
def batch_update_status(req: BatchStatusRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    records = sheets_mgr.load_records(mode)
    target_status = req.status.upper()
    today = datetime.now().strftime('%d-%m-%Y')

    for idx in req.indices:
        if 0 <= idx < len(records):
            r = records[idx]
            gross = float(r.get("Total_Amount_Due_Rs", 0) or 0)
            if target_status == "PAID":
                r["Payment_Status"] = "PAID"
                r["Partial_Payment_Rs"] = gross
                r["Actual_Due_Rs"] = 0.0
                r["Payment_Date"] = today
            else:
                r["Payment_Status"] = "UNPAID"
                if float(r.get("Actual_Due_Rs", 0) or 0) == 0:
                    r["Partial_Payment_Rs"] = 0.0
                    r["Payment_Date"] = ""
                    r["Actual_Due_Rs"] = gross

    sheets_mgr.save_records(mode, records)
    return {"status": "ok", "updated_count": len(req.indices)}

class BatchResetRequest(BaseModel):
    mode: str
    indices: List[int]
    reset_val: int

@app.post("/api/ledger/batch-reset")
def batch_update_reset(req: BatchResetRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    records = sheets_mgr.load_records(mode)
    val = 1 if req.reset_val == 1 else 0

    for idx in req.indices:
        if 0 <= idx < len(records):
            records[idx]["Reset"] = val

    sheets_mgr.save_records(mode, records)
    return {"status": "ok", "updated_count": len(req.indices)}

class PartialPayRequest(BaseModel):
    mode: str
    index: int
    payment_amount: float

@app.post("/api/ledger/partial-pay")
def apply_partial_pay(req: PartialPayRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    records = sheets_mgr.load_records(mode)
    if req.index < 0 or req.index >= len(records):
        raise HTTPException(status_code=404, detail="Index not found.")

    r = records[req.index]
    gross = float(r.get("Total_Amount_Due_Rs", 0) or 0)
    already_paid = float(r.get("Partial_Payment_Rs", 0) or 0)
    remaining_before = max(0.0, gross - already_paid)

    if req.payment_amount <= 0:
        raise HTTPException(status_code=400, detail="Payment must be greater than zero.")
    if req.payment_amount > remaining_before:
        raise HTTPException(status_code=400, detail=f"Payment cannot exceed remaining due of Rs. {remaining_before:.2f}")

    total_paid = already_paid + req.payment_amount
    actual_due = max(0.0, gross - total_paid)

    r["Partial_Payment_Rs"] = total_paid
    r["Actual_Due_Rs"] = actual_due
    r["Payment_Date"] = datetime.now().strftime('%d-%m-%Y')
    r["Payment_Status"] = "PAID" if actual_due == 0 else "UNPAID"

    sheets_mgr.save_records(mode, records)
    return {"status": "ok", "record": r}

class DeleteRowsRequest(BaseModel):
    mode: str
    indices: List[int]

@app.post("/api/ledger/delete")
def delete_ledger_rows(req: DeleteRowsRequest, _: bool = Depends(verify_admin)):
    mode = req.mode.upper()
    records = sheets_mgr.load_records(mode)
    drop_set = set(req.indices)
    new_records = [r for idx, r in enumerate(records) if idx not in drop_set]
    sheets_mgr.save_records(mode, new_records)
    return {"status": "ok", "deleted_count": len(records) - len(new_records)}

# ----------------- DUES MANAGEMENT -----------------

@app.get("/api/dues")
def get_dues_overview(mode: str = "COMMERCIAL", flat: Optional[str] = None):
    records = sheets_mgr.load_records(mode)

    # All unique flats for dropdown
    all_flats = sorted(list(set(str(r.get("Flat_No", "")).strip() for r in records if str(r.get("Flat_No", "")).strip())))

    # Filter unpaid, reset=0
    unpaid_records = []
    for idx, r in enumerate(records):
        status = str(r.get("Payment_Status", "")).strip().upper()
        reset_val = int(r.get("Reset", 0) or 0)
        f_no = str(r.get("Flat_No", "")).strip()

        if status != "PAID" and reset_val == 0:
            if not flat or flat == "ALL FLATS" or f_no.lower() == flat.lower():
                r_copy = r.copy()
                r_copy["_index"] = idx
                unpaid_records.append(r_copy)

    # Chronological sort
    def sort_key(r):
        try:
            y = int(str(r.get("Billing_Year", "2020")).strip())
            m = core.MONTH_MAP_INDEX.get(str(r.get("Due_Month", "JAN")).strip().upper()[:3], 1)
            return (y, m)
        except Exception:
            return (2020, 1)

    unpaid_records.sort(key=sort_key)

    total_due = sum(float(r.get("Total_Amount_Due_Rs", 0) or 0) for r in unpaid_records)
    total_paid = sum(float(r.get("Partial_Payment_Rs", 0) or 0) for r in unpaid_records)
    balance_left = sum(float(r.get("Actual_Due_Rs", 0) or 0) for r in unpaid_records)

    return {
        "flats": all_flats,
        "selected_flat": flat or "ALL FLATS",
        "total_due": total_due,
        "total_paid": total_paid,
        "balance_left": balance_left,
        "records": unpaid_records
    }

class AllocateDuesPaymentRequest(BaseModel):
    mode: str
    flat_no: str
    payment_amount: float
    payment_date: Optional[str] = None

@app.post("/api/dues/allocate")
def allocate_dues_payment(req: AllocateDuesPaymentRequest, _: bool = Depends(verify_admin)):
    if not req.flat_no or req.flat_no == "ALL FLATS":
        raise HTTPException(status_code=400, detail="Please select a specific Flat No to allocate payment.")
    if req.payment_amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero.")

    mode = req.mode.upper()
    records = sheets_mgr.load_records(mode)
    p_date = req.payment_date or datetime.now().strftime('%d-%m-%Y')

    updated_records, cleared_count, unallocated = core.apply_fifo_payment_allocation(
        records=records, target_flat=req.flat_no, payment_amount=req.payment_amount, payment_date=p_date
    )

    sheets_mgr.save_records(mode, updated_records)

    return {
        "status": "ok",
        "flat_no": req.flat_no,
        "cleared_count": cleared_count,
        "unallocated_balance": unallocated,
        "payment_amount": req.payment_amount
    }

# ----------------- LIVE AVERAGE LOOKUP -----------------

@app.get("/api/average-lookup")
def get_historical_common_average(month: str = "JAN", year: str = "2026"):
    records = sheets_mgr.load_records("DOMESTIC")
    target_m = month.strip().upper()[:3]
    target_y = str(year).strip()

    matches = [
        float(r.get("Common_Area_Units", 0) or 0)
        for r in records
        if str(r.get("Due_Month", "")).strip().upper()[:3] == target_m and \
           str(r.get("Billing_Year", "")).strip() == target_y and \
           float(r.get("Common_Area_Units", 0) or 0) > 0
    ]

    if matches:
        avg = round(sum(matches) / len(matches), 2)
        return {"status": "ok", "average_units": f"{avg:.2f} Units", "count": len(matches)}
    return {"status": "not_found", "average_units": "N/A (Empty)", "count": 0}

# ----------------- PDF PRINTING -----------------

class PrintStatementsRequest(BaseModel):
    mode: str
    indices: List[int]

@app.post("/api/print")
def print_selected_statements(req: PrintStatementsRequest):
    if not req.indices:
        raise HTTPException(status_code=400, detail="No rows selected for printing.")

    mode = req.mode.upper()
    records = sheets_mgr.load_records(mode)
    selected_rows = [records[i] for i in req.indices if 0 <= i < len(records)]

    if not selected_rows:
        raise HTTPException(status_code=400, detail="No valid rows found to print.")

    # Automatically bundle ALL JHD units for the same billing period if any JHD row is selected
    jhd_periods = set()
    for row in selected_rows:
        if core.is_jhd_group_record(row):
            jhd_periods.add((str(row.get("Due_Month", "")).strip().upper()[:3], str(row.get("Billing_Year", "")).strip()))

    if jhd_periods:
        existing_keys = {(core.canonical_flat(r.get("Flat_No", "")), str(r.get("Due_Month", "")).strip().upper()[:3], str(r.get("Billing_Year", "")).strip()) for r in selected_rows}
        for r in records:
            if core.is_jhd_group_record(r):
                m = str(r.get("Due_Month", "")).strip().upper()[:3]
                y = str(r.get("Billing_Year", "")).strip()
                k = (core.canonical_flat(r.get("Flat_No", "")), m, y)
                if (m, y) in jhd_periods and k not in existing_keys:
                    selected_rows.append(r)
                    existing_keys.add(k)

    notice_content = get_notices_text()
    compiled_html = ""

    for kind, group in core.build_grouped_print_records(selected_rows):
        if kind == "group":
            first = group[0]
            compiled_html += pdf_generator.generate_html_grouped_invoice(
                records=group,
                due_month_str=str(first.get("Due_Month", "")),
                due_year_str=str(first.get("Billing_Year", "")),
                tenant_type=mode,
                notice_content=notice_content
            )
        else:
            r = group[0]
            cfg = {
                "tenant": r.get("Tenant_Name", "N/A"),
                "fixed": float(r.get("Fixed_Meter_Charges_Rs", 0) or 0),
                "tax": float(r.get("Municipal_Tax_Rs", 0) or 0),
                "water": float(r.get("Water_Charges_Rs", 0) or 0) if mode == "COMMERCIAL" else 0.0,
                "maintenance": float(r.get("Building_Maint_Fund_Rs", 0) or 0),
                "lift": float(r.get("Lift_Charges_Rs", 0) or 0),
                "others": float(r.get("Others_Charges_Rs", 0) or 0)
            }
            com_units = float(r.get("Common_Area_Units", 0) or 0) if mode == "DOMESTIC" else 0.0
            consumed = float(r.get("Consumed_Units", 0) or 0) + com_units

            compiled_html += pdf_generator.generate_html_single_bill(
                flat_no=str(r.get("Flat_No", "")),
                cfg=cfg,
                due_month_str=str(r.get("Due_Month", "")),
                due_year_str=str(r.get("Billing_Year", "")),
                prev_r=float(r.get("Open_Meter_Reading", 0) or 0),
                float_curr=float(r.get("Closing_Meter_Reading", 0) or 0),
                consumed=consumed,
                elec_charge=float(r.get("Electric_Charges_Rs", 0) or 0),
                others_val=float(r.get("Others_Charges_Rs", 0) or 0),
                total=float(r.get("Total_Amount_Due_Rs", 0) or 0),
                tenant_type=mode,
                com_area_val=com_units,
                notice_content=notice_content
            )

    pdf_bytes = pdf_generator.compile_pdf_bytes(compiled_html)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Statement.pdf"}
    )

# ----------------- GOOGLE SHEETS SETTINGS & SYNC -----------------

@app.get("/api/google-sheets/status")
def google_sheets_status(test: bool = False):
    return sheets_mgr.get_status(retest=test)

class GoogleSheetsConfigRequest(BaseModel):
    apps_script_url: Optional[str] = ""
    spreadsheet_id: Optional[str] = ""
    spreadsheet_url: Optional[str] = ""
    credentials_file: Optional[str] = "service_account.json"
    use_live_google_sheets: bool = True

@app.post("/api/google-sheets/config")
def update_google_sheets_config(req: GoogleSheetsConfigRequest, _: bool = Depends(verify_admin)):
    cfg_dict = req.dict()
    if cfg_dict.get("apps_script_url"):
        cfg_dict["use_live_google_sheets"] = True
    connected, msg = sheets_mgr.save_config(cfg_dict)
    return {"status": "ok" if connected else "error", "message": msg, "details": sheets_mgr.get_status()}

class SyncRequest(BaseModel):
    action: Optional[str] = "push"  # "push" or "pull"

@app.post("/api/google-sheets/sync")
def sync_google_sheets(req: Optional[SyncRequest] = None, _: bool = Depends(verify_admin)):
    action = req.action if req else "push"
    if action == "pull":
        success, msg = sheets_mgr.pull_from_google_sheets()
    else:
        success, msg = sheets_mgr.sync_all_to_google_sheets()
    return {"status": "ok" if success else "error", "message": msg, "details": sheets_mgr.get_status()}

@app.get("/api/download-template")
def download_google_sheets_template():
    path = os.path.join(PROJECT_DIR, "Basant_Jamini_Bhawan_Maintenance_Ledger.xlsx")
    if os.path.exists(path):
        return FileResponse(path, filename="Basant_Jamini_Bhawan_Maintenance_Ledger.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    raise HTTPException(status_code=404, detail="Template file not found.")

@app.get("/api/apps-script-code")
def get_apps_script_code():
    path = os.path.join(BASE_DIR, "google_apps_script.js")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {"status": "ok", "code": f.read()}
    raise HTTPException(status_code=404, detail="Apps Script file not found.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
