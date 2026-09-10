"""
Billing Core Engine for Basant Jamini Bhawan Welfare Association
Contains all business logic, rates, date validity matching, and calculation rules.
"""

from datetime import datetime

# Base Rates Per Unit (RPU)
RATE_COMMERCIAL = 6.90
RATE_DOMESTIC = 5.40

MONTH_MAP_INDEX = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}

def is_date_after_or_equal(m1, y1, m_start_str, y_start):
    """Returns True if statement date (m1, y1) falls on or after rule threshold (m_start_str, y_start)."""
    if not m1 or not y1:
        return True
    idx1 = MONTH_MAP_INDEX.get(str(m1).upper()[:3], 1)
    idx_start = MONTH_MAP_INDEX.get(str(m_start_str).upper()[:3], 1)
    if int(y1) > int(y_start):
        return True
    if int(y1) == int(y_start) and idx1 >= idx_start:
        return True
    return False

DEFAULT_COMMERCIAL_CONFIG = {
    "G-1": {"tenant": "VLCC", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 5340.0}], "tax": 46.0, "water": 1500.0, "maintenance": 1200.0, "lift": 0.0, "others": 0.0},
    "G-2": {"tenant": "REGALIA WELLNESS LLP", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 13468.0}], "tax": 46.0, "water": 300.0, "maintenance": 2400.0, "lift": 0.0, "others": 0.0},
    "G-3": {"tenant": "DILIGENT SERVICE", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 2670.0}], "tax": 46.0, "water": 200.0, "maintenance": 1200.0, "lift": 0.0, "others": 0.0},
    "A-1": {"tenant": "JHD", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 2670.0}], "tax": 46.0, "water": 0.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "B-1": {"tenant": "PEPPERFRY", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 2670.0}], "tax": 46.0, "water": 0.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "C-1": {"tenant": "PODDAR", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 2670.0}], "tax": 46.0, "water": 0.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "D-1": {"tenant": "PAWAN KUMAR SARAWGI", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 2670.0}], "tax": 46.0, "water": 0.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "E-1": {"tenant": "PINKI BANSAL", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 2670.0}], "tax": 46.0, "water": 0.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "F-1": {"tenant": "JHD", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1335.0}], "tax": 0.0, "water": 0.0, "maintenance": 600.0, "lift": 295.0, "others": 0.0},
    "F-2": {"tenant": "JHD", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1335.0}], "tax": 0.0, "water": 0.0, "maintenance": 600.0, "lift": 295.0, "others": 0.0},
}

DEFAULT_DOMESTIC_CONFIG = {
    "A-2": {"tenant": "BSA", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "B-2": {"tenant": "BSA", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "C-2": {"tenant": "S. VINAYAK", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "D-2": {"tenant": "HEMANT KUMAR DEY", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "E-2": {"tenant": "RAMEN DEY", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "F-2": {"tenant": "SUDAMA SINGH", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "A-3": {"tenant": "M. SINGHANIA", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "B-3": {"tenant": "SHEKHAR", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "C-3": {"tenant": "JAI MANGLA SPONG IRON", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "D-3": {"tenant": "M.R. ORGANISATION LTD.", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "E-3": {"tenant": "SULEKHA DEY", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "F-3": {"tenant": "SADHANA DEY", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "A-4": {"tenant": "S.K.BANERJEE", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "B-4": {"tenant": "ASHIRWAD SPONGE IRON", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "C-4": {"tenant": "KABITA SINGH", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "D-4": {"tenant": "R&R LOGISTICS", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "E-4": {"tenant": "PODDAR", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "F-4": {"tenant": "H.K.GIRI", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 1187.0}], "tax": 46.0, "maintenance": 1200.0, "lift": 590.0, "others": 0.0},
    "G-4": {"tenant": "OWN", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 0.0}], "tax": 0.0, "maintenance": 1200.0, "lift": 0.0, "others": 0.0},
    "Common": {"tenant": "ASSOCIATION MASTER METER", "fixed": [{"start_month": "JAN", "start_year": 2020, "val": 0.0}], "tax": 0.0, "maintenance": 0.0, "lift": 0.0, "others": 0.0, "is_common": True}
}

DEFAULT_NOTICE_TEXT = (
    "i) This is to inform you that every month bill must be paid by the 16th of the following month.\n"
    "   If payment is not received by the due date,the connection/line will be disconnected without further notice.\n"
    "ii ) Payment may be made either by cheque in favour of Tata Steel Ltd or in cash\n"
    "iii) This is to inform all holders of the premises that a person will be appointed for the purpose i) Generating bills and ii) collecting payments from each holder.The remunaration of said person will be arranged and shared equally . You are requested to kindly extend your cooperation in this matter,\n"
    "iv) Park your vehicle in the Garrage area alloted to you ."
)

COMMERCIAL_COLUMNS = [
    "Tenant_Name", "Flat_No", "Due_Month", "Billing_Year", "Open_Meter_Reading",
    "Closing_Meter_Reading", "Consumed_Units", "Electric_Charges_Rs", "Fixed_Meter_Charges_Rs",
    "Municipal_Tax_Rs", "Water_Charges_Rs", "Building_Maint_Fund_Rs", "Lift_Charges_Rs",
    "Others_Charges_Rs", "Total_Amount_Due_Rs", "Partial_Payment_Rs", "Payment_Date",
    "Actual_Due_Rs", "Payment_Status", "Reset"
]

DOMESTIC_COLUMNS = [
    "Tenant_Name", "Flat_No", "Due_Month", "Billing_Year", "Open_Meter_Reading",
    "Closing_Meter_Reading", "Consumed_Units", "Common_Area_Units", "Electric_Charges_Rs",
    "Fixed_Meter_Charges_Rs", "Municipal_Tax_Rs", "Building_Maint_Fund_Rs", "Lift_Charges_Rs",
    "Others_Charges_Rs", "Total_Amount_Due_Rs", "Partial_Payment_Rs", "Payment_Date",
    "Actual_Due_Rs", "Payment_Status", "Reset"
]

def resolve_effective_fixed_rate(flat_cfg, month_str, year_str):
    """Finds the most recent fixed rate applicable on or before the statement date."""
    timeline = flat_cfg.get("fixed", [])
    if not timeline:
        return 0.0
    matched_val = timeline[0]["val"]
    max_year = -1
    max_month_idx = -1
    for item in timeline:
        s_m = item["start_month"]
        s_y = int(item["start_year"])
        if is_date_after_or_equal(month_str, year_str, s_m, s_y):
            m_idx = MONTH_MAP_INDEX.get(s_m.upper()[:3], 1)
            if s_y > max_year or (s_y == max_year and m_idx >= max_month_idx):
                max_year = s_y
                max_month_idx = m_idx
                matched_val = item["val"]
    return float(matched_val)

def calculate_commercial_bill(flat_no, cfg, month_str, year_str, prev_r, curr_r, rpu_rate, others_val=0.0):
    """Calculates single line commercial bill record."""
    consumed = max(0.0, float(curr_r) - float(prev_r))
    elec_charge = round(consumed * float(rpu_rate), 2)
    fixed_charge = resolve_effective_fixed_rate(cfg, month_str, year_str)
    tax = float(cfg.get("tax", 0.0))
    water = float(cfg.get("water", 0.0))
    maint = float(cfg.get("maintenance", 0.0))
    lift = float(cfg.get("lift", 0.0))
    others = float(others_val)

    total = elec_charge + fixed_charge + tax + water + maint + lift + others
    gross_total = int(total + 0.5)

    return {
        "Tenant_Name": cfg.get("tenant", "N/A"),
        "Flat_No": str(flat_no),
        "Due_Month": str(month_str).upper()[:3],
        "Billing_Year": str(year_str),
        "Open_Meter_Reading": float(prev_r),
        "Closing_Meter_Reading": float(curr_r),
        "Consumed_Units": consumed,
        "Electric_Charges_Rs": elec_charge,
        "Fixed_Meter_Charges_Rs": fixed_charge,
        "Municipal_Tax_Rs": tax,
        "Water_Charges_Rs": water,
        "Building_Maint_Fund_Rs": maint,
        "Lift_Charges_Rs": lift,
        "Others_Charges_Rs": others,
        "Total_Amount_Due_Rs": gross_total,
        "Partial_Payment_Rs": 0.0,
        "Payment_Date": "",
        "Actual_Due_Rs": gross_total,
        "Payment_Status": "UNPAID",
        "Reset": 0
    }

def calculate_domestic_bill(flat_no, cfg, month_str, year_str, prev_r, curr_r, rpu_rate, common_share_units=0.0, others_val=0.0):
    """Calculates single line domestic bill record."""
    meter_units = max(0.0, float(curr_r) - float(prev_r))
    effective_common = 0.0 if str(flat_no).strip().upper() == "G-4" else float(common_share_units)
    total_units = meter_units + effective_common
    elec_charge = round(total_units * float(rpu_rate), 2)
    fixed_charge = resolve_effective_fixed_rate(cfg, month_str, year_str)
    tax = float(cfg.get("tax", 0.0))
    maint = float(cfg.get("maintenance", 0.0))
    lift = float(cfg.get("lift", 0.0))
    others = float(others_val)

    total = elec_charge + fixed_charge + tax + maint + lift + others
    gross_total = int(total + 0.5)

    return {
        "Tenant_Name": cfg.get("tenant", "N/A"),
        "Flat_No": str(flat_no),
        "Due_Month": str(month_str).upper()[:3],
        "Billing_Year": str(year_str),
        "Open_Meter_Reading": float(prev_r),
        "Closing_Meter_Reading": float(curr_r),
        "Consumed_Units": meter_units,
        "Common_Area_Units": effective_common,
        "Electric_Charges_Rs": elec_charge,
        "Fixed_Meter_Charges_Rs": fixed_charge,
        "Municipal_Tax_Rs": tax,
        "Building_Maint_Fund_Rs": maint,
        "Lift_Charges_Rs": lift,
        "Others_Charges_Rs": others,
        "Total_Amount_Due_Rs": gross_total,
        "Partial_Payment_Rs": 0.0,
        "Payment_Date": "",
        "Actual_Due_Rs": gross_total,
        "Payment_Status": "UNPAID",
        "Reset": 0
    }

def canonical_flat(flat):
    flat = str(flat).strip().upper().replace(" ", "")
    return {"A1": "A-1", "F1": "F-1", "F2": "F-2"}.get(flat, str(flat).strip().upper())

def is_jhd_group_record(row):
    """Returns True if record belongs to JHD resident group (A-1, F-1, F-2)."""
    tenant = str(row.get("Tenant_Name", "")).strip().upper()
    flat = canonical_flat(row.get("Flat_No", ""))
    return tenant == "JHD" and flat in {"A-1", "F-1", "F-2"}

def build_grouped_print_records(rows):
    """Groups JHD A-1/F-1/F-2 rows by (month, year); leaves all other rows as single bills."""
    groups = []
    jhd_groups = {}
    for row in rows:
        month = str(row.get("Due_Month", "")).strip().upper()[:3]
        year = str(row.get("Billing_Year", "")).strip()
        if is_jhd_group_record(row):
            key = (month, year)
            jhd_groups.setdefault(key, []).append(row)
        else:
            groups.append(("single", [row]))
    for key, group in jhd_groups.items():
        groups.append(("group", group))
    return groups

def apply_fifo_payment_allocation(records, target_flat, payment_amount, payment_date=None):
    """
    Sequentially allocates a payment across oldest unpaid, non-reset records for target_flat.
    Returns (updated_records, allocated_count, remaining_balance).
    """
    if not payment_date:
        payment_date = datetime.now().strftime('%d-%m-%Y')

    target_can = canonical_flat(target_flat)

    # Identify matching indices
    unpaid_indices = []
    for idx, r in enumerate(records):
        f = canonical_flat(r.get("Flat_No", ""))
        status = str(r.get("Payment_Status", "")).strip().upper()
        reset_flag = int(r.get("Reset", 0) or 0)
        gross_due = round(float(r.get("Total_Amount_Due_Rs", 0) or 0), 2)
        already_paid = round(float(r.get("Partial_Payment_Rs", 0) or 0), 2)
        actual_due = round(max(0.0, float(r.get("Actual_Due_Rs", gross_due - already_paid) or 0)), 2)

        if f == target_can and status != "PAID" and reset_flag == 0 and actual_due > 0.001:
            unpaid_indices.append(idx)

    # Sort chronologically by (Billing_Year, Due_Month)
    def sort_key(idx):
        r = records[idx]
        try:
            y = int(str(r.get("Billing_Year", "2020")).strip())
            m = MONTH_MAP_INDEX.get(str(r.get("Due_Month", "JAN")).strip().upper()[:3], 1)
            return (y, m)
        except Exception:
            return (2020, 1)

    unpaid_indices.sort(key=sort_key)

    remaining = round(float(payment_amount), 2)
    allocated_count = 0

    for idx in unpaid_indices:
        if remaining <= 0.001:
            break
        r = records[idx]
        gross_due = round(float(r.get("Total_Amount_Due_Rs", 0) or 0), 2)
        already_paid = round(float(r.get("Partial_Payment_Rs", 0) or 0), 2)
        left = round(max(0.0, gross_due - already_paid), 2)

        if left <= 0.001:
            continue

        if remaining >= left:
            r["Partial_Payment_Rs"] = gross_due
            r["Actual_Due_Rs"] = 0.0
            r["Payment_Status"] = "PAID"
            r["Payment_Date"] = payment_date
            remaining = round(remaining - left, 2)
            allocated_count += 1
        else:
            new_paid = round(already_paid + remaining, 2)
            r["Partial_Payment_Rs"] = new_paid
            r["Actual_Due_Rs"] = round(max(0.0, gross_due - new_paid), 2)
            r["Payment_Status"] = "UNPAID"
            r["Payment_Date"] = payment_date
            remaining = 0.0
            allocated_count += 1

    return records, allocated_count, round(remaining, 2)

