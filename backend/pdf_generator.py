"""
PDF Generator for Basant Jamini Bhawan Welfare Association
Generates high-precision A4 PDF statements matching the exact physical billing layout
with standard 2-column description & amount format, clear lines, and structured notes.
"""

import io
import re
from datetime import datetime
from xhtml2pdf import pisa
from billing_core import canonical_flat, RATE_COMMERCIAL, RATE_DOMESTIC, DEFAULT_NOTICE_TEXT

PDF_HTML_WRAPPER = """
<html>
<head>
    <meta charset='utf-8'>
    <style>
        @page {{
            size: a4 portrait;
            margin: 10mm 16mm 8mm 16mm;
        }}
        body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #000000;
            font-size: 10pt;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
        }}
        table.header-box {{
            width: 100%;
            border: 1.2px solid #000000;
            border-collapse: collapse;
            margin-bottom: 14px;
        }}
        table.header-box td {{
            border: 0;
            text-align: center;
            padding: 6px 4px;
            line-height: 1.35;
        }}
        .title {{
            font-size: 11pt;
            font-weight: bold;
            letter-spacing: 0.2px;
        }}
        .sub-title {{
            font-size: 9.5pt;
            font-weight: bold;
        }}
        .charge-title {{
            font-size: 10pt;
            font-weight: bold;
            padding-top: 2px;
        }}
        .meta-table {{
            width: 100%;
            margin-bottom: 5px;
            font-size: 9.5pt;
            font-weight: bold;
        }}
        .meta-table td {{
            border: 0 !important;
            padding: 2px 1px;
        }}
        .main-table {{
            width: 100%;
            border-collapse: collapse;
            border: 1.2px solid #000000;
        }}
        .main-table th, .main-table td {{
            border: 1px solid #000000;
            padding: 3px 5px;
            font-size: 9pt;
            vertical-align: middle;
        }}
        .col-desc {{
            width: 86%;
        }}
        .col-rs {{
            width: 10.5%;
            text-align: center;
        }}
        .col-p {{
            width: 3.5%;
            text-align: center;
        }}
        .center {{
            text-align: center;
        }}
        .right {{
            text-align: right;
        }}
        .bold {{
            font-weight: bold;
        }}
        .inner-tbl {{
            width: 100%;
            border-collapse: collapse;
        }}
        .inner-tbl td {{
            border: 0 !important;
            padding: 0 !important;
            font-size: 9pt;
        }}
        /* Legacy & Fallback Styles */
        .header-table {{
            background-color: #ffffff;
            border: 2px solid #000000;
            padding: 12px;
            text-align: center;
        }}
        .header-title {{
            color: #000000;
            font-size: 22px;
            font-weight: bold;
            letter-spacing: 0.5px;
        }}
        .header-subtitle {{
            color: #000000;
            font-size: 13px;
            font-weight: bold;
            padding-top: 4px;
        }}
        .meta-table-dom {{
            font-size: 14px;
            line-height: 1.2;
            width: 100%;
        }}
        .metrics-box {{
            background-color: #ffffff;
            padding: 8px;
            border: 2px solid #000000;
            color: #000000;
            font-size: 14px;
        }}
        .th-item {{
            background-color: #ffffff;
            color: #000000;
            padding: 8px 7px;
            font-size: 14px;
            font-weight: bold;
            border-top: 2px solid #000000;
            border-bottom: 2px solid #000000;
        }}
        .td-item {{
            padding: 6px 7px;
            font-size: 13px;
            border-bottom: 1.5px solid #000000;
        }}
        .total-box {{
            background-color: #ffffff;
            border: 2px solid #000000;
            padding: 8px;
            text-align: right;
            font-size: 15px;
            font-weight: bold;
            color: #000000;
        }}
        .notice-box {{
            background-color: #ffffff;
            border: 2px solid #000000;
            color: #000000;
            padding: 8px;
            font-size: 10px;
            line-height: 1.2;
        }}
        .footer-text {{
            font-size: 9px;
            color: #000000;
            text-align: center;
            border-top: 2px solid #000000;
            padding-top: 4px;
        }}
        .section-gap {{
            height: 21pt;
            line-height: 21pt;
        }}
    </style>
</head>
<body>
{compiled_html}
</body>
</html>
"""

def fmt_num(v):
    if v is None or v == '' or v == 0:
        return ''
    try:
        fv = float(v)
        return f"{int(fv + 0.5)}" if abs(fv - round(fv)) < 0.01 else f"{fv:.2f}"
    except (ValueError, TypeError):
        return str(v)

def build_notice_rows_html(raw_text=None):
    """Dynamically builds HTML table rows for the NOTE section from the Invoice Notices."""
    if not raw_text or not str(raw_text).strip():
        raw_text = DEFAULT_NOTICE_TEXT

    lines = [ln.strip() for ln in str(raw_text).strip().split('\n') if ln.strip()]
    items = []
    curr_item = []

    prefix_re = re.compile(r'^(?:[ivxIVX]+\s*[\)\.]|\d+[\)\.]|[•\-\*])\s*')
    header_re = re.compile(r'^(?:note\s*:?|important notice.*:?)$', re.IGNORECASE)

    for line in lines:
        if header_re.match(line):
            continue
        if prefix_re.match(line):
            if curr_item:
                items.append(' '.join(curr_item))
                curr_item = []
            curr_item.append(line)
        else:
            if curr_item:
                curr_item.append(line)
            else:
                curr_item = [line]

    if curr_item:
        items.append(' '.join(curr_item))

    if not items:
        items = [str(raw_text).strip()]

    rows_html = [
        "<tr>",
        "  <td style='font-weight: bold; font-size: 8.5pt; padding-left: 15px;'>NOTE :</td>",
        "  <td class='col-rs'></td>",
        "  <td class='col-p'></td>",
        "</tr>"
    ]

    for itm in items:
        rows_html.append("<tr>")
        rows_html.append(f"  <td style='font-size: 7.6pt; line-height: 1.2;'>{itm}</td>")
        rows_html.append("  <td class='col-rs'></td>")
        rows_html.append("  <td class='col-p'></td>")
        rows_html.append("</tr>")

    return '\n'.join(rows_html)


def generate_html_single_bill(
    flat_no, cfg, due_month_str, due_year_str, prev_r, float_curr, consumed,
    elec_charge, others_val, total, tenant_type, com_area_val=0.0,
    notice_content=None, meter_units=None, rpu_val=None
):
    """Generates the HTML statement for a single flat matching exact physical formats."""
    total = int(total + 0.5)
    yr_display = str(due_year_str)[-2:] if len(str(due_year_str)) == 4 else str(due_year_str)

    if tenant_type == "COMMERCIAL":
        period_display = f"{due_month_str.title()[:3]}-{yr_display}"
        if rpu_val is None:
            rpu_val = RATE_COMMERCIAL

        elec_str = f"{int(elec_charge + 0.5)}"
        fixed_val = cfg.get('fixed', 0.0)
        if isinstance(fixed_val, list):
            fixed_val = fixed_val[0].get("val", 0.0) if fixed_val else 0.0
        fixed_str = fmt_num(float(fixed_val or 0.0))
        tax_val = cfg.get('tax', 0.0)
        tax_str = fmt_num(float(tax_val or 0.0))
        water_val = cfg.get('water', 0.0)
        water_str = fmt_num(float(water_val or 0.0))
        maint_val = cfg.get('maintenance', 0.0)
        maint_str = fmt_num(float(maint_val or 0.0))
        lift_val = cfg.get('lift', 0.0)
        lift_str = fmt_num(float(lift_val or 0.0))
        others_str = fmt_num(float(others_val or 0.0))
        total_str = f"{total}"

        consumed_int = int(consumed + 0.5) if abs(consumed - round(consumed)) < 0.01 else f"{consumed:.2f}"
        prev_int = int(prev_r + 0.5) if abs(prev_r - round(prev_r)) < 0.01 else f"{prev_r:.2f}"
        curr_int = int(float_curr + 0.5) if abs(float_curr - round(float_curr)) < 0.01 else f"{float_curr:.2f}"

        others_row = f"""
        <tr>
          <td>Miscellaneous / Others Overheads</td>
          <td class="col-rs center">{others_str}</td>
          <td class="col-p"></td>
        </tr>""" if others_val and others_val > 0 else ""

        html = f"""
        <div style='page-break-after: always; page-break-inside: avoid;'>
          <!-- Header Box -->
          <table class="header-box" cellspacing="0" cellpadding="0">
            <tr>
              <td>
                <span class="title">BASANT JAMINI BHAWAN WELFARE ASSOCIATION</span><br/>
                <span class="sub-title">Contractor's Area Road No. 2 Bistupur, Jamshedpur - 831001</span><br/>
                <span class="charge-title">Monthly Maintenance Charge</span>
              </td>
            </tr>
          </table>

          <!-- Meta Info -->
          <table class="meta-table" cellspacing="0" cellpadding="0">
            <tr>
              <td style="width: 55%;">Name : {cfg.get('tenant', 'N/A')}</td>
              <td style="width: 45%;"></td>
            </tr>
            <tr>
              <td>Flat No. {flat_no}</td>
              <td style="text-align: right;">Due Month &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {period_display}</td>
            </tr>
          </table>

          <!-- Main Table -->
          <table class="main-table" cellspacing="0" cellpadding="0">
            <tr>
              <td class="col-desc center bold" style="font-size: 9.5pt;">DESCRIPTION</td>
              <td colspan="2" class="center bold" style="font-size: 9.5pt;">AMOUNT</td>
            </tr>
            <tr>
              <td>&nbsp;</td>
              <td class="col-rs center bold" style="font-size: 8.5pt;">Rs.</td>
              <td class="col-p center bold" style="font-size: 8.5pt;">P.</td>
            </tr>
            <tr>
              <td class="center">{flat_no}</td>
              <td class="col-rs"></td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>
                <table class="inner-tbl">
                  <tr>
                    <td style="width: 46%;">Closing Meter Reading</td>
                    <td style="width: 54%; text-align: center;">{curr_int}</td>
                  </tr>
                </table>
              </td>
              <td class="col-rs"></td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>
                <table class="inner-tbl">
                  <tr>
                    <td style="width: 46%;">Opening Meter Reading</td>
                    <td style="width: 54%; text-align: center;">{prev_int}</td>
                  </tr>
                </table>
              </td>
              <td class="col-rs"></td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>
                <table class="inner-tbl">
                  <tr>
                    <td style="width: 46%;">Chargeable Unit</td>
                    <td style="width: 54%; text-align: center;">{consumed_int}</td>
                  </tr>
                </table>
              </td>
              <td class="col-rs"></td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>Total unit Consumed As per individual meter : &nbsp;&nbsp;&nbsp;&nbsp; {consumed_int} &nbsp;&nbsp;&nbsp;&nbsp; units ( {flat_no} )</td>
              <td class="col-rs"></td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>Electric Charges ( Commercial )</td>
              <td class="col-rs"></td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>
                <table class="inner-tbl">
                  <tr>
                    <td style="width: 8%;"></td>
                    <td style="width: 22%;">Meter unit</td>
                    <td style="width: 70%;">Elec. Charge / Unit ( in Rs.)</td>
                  </tr>
                </table>
              </td>
              <td class="col-rs"></td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>
                <table class="inner-tbl">
                  <tr>
                    <td style="width: 8%;">{flat_no}</td>
                    <td style="width: 22%;">{consumed_int}</td>
                    <td style="width: 70%;">{rpu_val:.2f}/-</td>
                  </tr>
                </table>
              </td>
              <td class="col-rs center">{elec_str}</td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>Fixed Meter Charges : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ( {flat_no} : Rs. {fixed_str}/-)</td>
              <td class="col-rs center">{fixed_str}</td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>Municipal Tax</td>
              <td class="col-rs center">{tax_str}</td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>
                <table class="inner-tbl">
                  <tr>
                    <td style="width: 46%;">Water Charges</td>
                    <td style="width: 54%; text-align: center;">{flat_no}</td>
                  </tr>
                </table>
              </td>
              <td class="col-rs center">{water_str}</td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>
                <table class="inner-tbl">
                  <tr>
                    <td style="width: 46%;">Building Maint. fund :</td>
                    <td style="width: 54%; text-align: center;">{flat_no}</td>
                  </tr>
                </table>
              </td>
              <td class="col-rs center">{maint_str}</td>
              <td class="col-p"></td>
            </tr>
            <tr>
              <td>Lift Charges</td>
              <td class="col-rs center">{lift_str}</td>
              <td class="col-p"></td>
            </tr>
            {others_row}
            <tr>
              <td class="right bold" style="font-size: 9.5pt; padding-right: 14px;">TOTAL</td>
              <td class="col-rs center bold" style="font-size: 9.5pt;">{total_str}</td>
              <td class="col-p"></td>
            </tr>
            {build_notice_rows_html(notice_content)}
          </table>
        </div>
        """
        return html

    # DOMESTIC RESIDENT EXACT FORMAT (Matching exact user uploaded reference)
    MONTH_MAP = {
        'JAN': 'January', 'FEB': 'February', 'MAR': 'March', 'APR': 'April',
        'MAY': 'May', 'JUN': 'June', 'JUL': 'July', 'AUG': 'August',
        'SEP': 'September', 'OCT': 'October', 'NOV': 'November', 'DEC': 'December'
    }
    m_key = str(due_month_str).strip().upper()[:3]
    month_full = MONTH_MAP.get(m_key, str(due_month_str).title())
    period_display = f"{month_full} {yr_display}"

    if rpu_val is None:
        rpu_val = RATE_DOMESTIC

    if meter_units is None:
        meter_units = max(0.0, float(consumed) - float(com_area_val or 0.0))
    else:
        meter_units = float(meter_units)

    common_units = float(com_area_val or 0.0)
    total_chargeable = meter_units + common_units

    meter_u_int = int(meter_units + 0.5) if abs(meter_units - round(meter_units)) < 0.01 else f"{meter_units:.2f}"
    common_u_int = int(common_units + 0.5) if abs(common_units - round(common_units)) < 0.01 else f"{common_units:.2f}"
    chargeable_u_int = int(total_chargeable + 0.5) if abs(total_chargeable - round(total_chargeable)) < 0.01 else f"{total_chargeable:.2f}"

    prev_int = int(prev_r + 0.5) if abs(prev_r - round(prev_r)) < 0.01 else f"{prev_r:.2f}"
    curr_int = int(float_curr + 0.5) if abs(float_curr - round(float_curr)) < 0.01 else f"{float_curr:.2f}"

    elec_str = f"{int(elec_charge + 0.5)}"
    fixed_val = cfg.get('fixed', 0.0)
    if isinstance(fixed_val, list):
        fixed_val = fixed_val[0].get("val", 0.0) if fixed_val else 0.0
    fixed_str = fmt_num(float(fixed_val or 0.0))
    tax_val = cfg.get('tax', 0.0)
    tax_str = fmt_num(float(tax_val or 0.0))
    maint_val = cfg.get('maintenance', 0.0)
    maint_str = fmt_num(float(maint_val or 0.0))
    lift_val = cfg.get('lift', 0.0)
    lift_str = fmt_num(float(lift_val or 0.0))
    others_str = fmt_num(float(others_val or 0.0))
    total_str = f"{total}"

    others_row = f"""
    <tr>
      <td>Miscellaneous / Others Overheads</td>
      <td class="col-rs center">{others_str}</td>
      <td class="col-p"></td>
    </tr>""" if others_val and others_val > 0 else ""

    lift_row = f"""
    <tr>
      <td>
        <table class="inner-tbl">
          <tr>
            <td style="width: 46%;">Lift Charges</td>
            <td style="width: 54%; text-align: center;">( {flat_no} )</td>
          </tr>
        </table>
      </td>
      <td class="col-rs center">{lift_str}</td>
      <td class="col-p"></td>
    </tr>""" if lift_val and lift_val > 0 else """
    <tr>
      <td>
        <table class="inner-tbl">
          <tr>
            <td style="width: 46%;">Lift Charges</td>
            <td style="width: 54%; text-align: center;">( {flat_no} )</td>
          </tr>
        </table>
      </td>
      <td class="col-rs center"></td>
      <td class="col-p"></td>
    </tr>"""

    tenant_name_raw = cfg.get('tenant', 'N/A')
    tenant_name_display = "B S A" if str(tenant_name_raw).strip().upper() == "BSA" else str(tenant_name_raw)

    html = f"""
    <div style='page-break-after: always; page-break-inside: avoid;'>
      <table class="header-box" cellspacing="0" cellpadding="0">
        <tr>
          <td>
            <span class="title">BASANT JAMINI BHAWAN WELFARE ASSOCIATION</span><br/>
            <span class="sub-title">Contractor's Area Road No. 2 Bistupur, Jamshedpur - 831001</span><br/>
            <span class="charge-title">Monthly Maintenance Charge</span>
          </td>
        </tr>
      </table>

      <table class="meta-table" cellspacing="0" cellpadding="0">
        <tr>
          <td style="width: 55%;">Name : {tenant_name_display}</td>
          <td style="width: 45%;"></td>
        </tr>
        <tr>
          <td>Flat No. ( {flat_no} )</td>
          <td style="text-align: right;">Due Month &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {period_display}</td>
        </tr>
      </table>

      <table class="main-table" cellspacing="0" cellpadding="0">
        <tr>
          <td class="col-desc center bold" style="font-size: 9.5pt;">DESCRIPTION</td>
          <td colspan="2" class="center bold" style="font-size: 9.5pt;">AMOUNT</td>
        </tr>
        <tr>
          <td>&nbsp;</td>
          <td class="col-rs center bold" style="font-size: 8.5pt;">Rs.</td>
          <td class="col-p center bold" style="font-size: 8.5pt;">P.</td>
        </tr>
        <tr>
          <td class="center">{flat_no}</td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 46%;">Closing Meter Reading</td>
                <td style="width: 54%; text-align: center;">{curr_int}</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 46%;">Opening Meter Reading</td>
                <td style="width: 54%; text-align: center;">{prev_int}</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 46%;">Meter Reading Unit</td>
                <td style="width: 54%; text-align: center;">{meter_u_int} Units</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 46%;">Common Area Electricity charges</td>
                <td style="width: 54%; text-align: center;">{common_u_int} Units</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Total Chargeable Unit &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ( {meter_u_int} + {common_u_int} ) = {chargeable_u_int} units &nbsp;&nbsp;&nbsp;&nbsp; ( {flat_no} )</td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Electric Charges ( Residential )</td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 14%;">&nbsp;</td>
                <td style="width: 32%; text-align: center;">Total Chageable unit</td>
                <td style="width: 54%; text-align: center;">Elec. Charge / Unit ( in Rs.)</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 14%;">{flat_no}</td>
                <td style="width: 32%; text-align: center;">{chargeable_u_int}</td>
                <td style="width: 54%; text-align: center;">{rpu_val:.2f}/-</td>
              </tr>
            </table>
          </td>
          <td class="col-rs center">{elec_str}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 46%;">Fixed Meter Charges</td>
                <td style="width: 54%; text-align: center;">( {flat_no} )</td>
              </tr>
            </table>
          </td>
          <td class="col-rs center">{fixed_str}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Municipal Tax</td>
          <td class="col-rs center">{tax_str}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Water Charges</td>
          <td class="col-rs center"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 46%;">Building Maint. fund</td>
                <td style="width: 54%; text-align: center;">( {flat_no} )</td>
              </tr>
            </table>
          </td>
          <td class="col-rs center">{maint_str}</td>
          <td class="col-p"></td>
        </tr>
        {lift_row}
        {others_row}
        <tr>
          <td class="right bold" style="font-size: 9.5pt; padding-right: 14px;">TOTAL</td>
          <td class="col-rs center bold" style="font-size: 9.5pt;">{total_str}</td>
          <td class="col-p"></td>
        </tr>
        {build_notice_rows_html(notice_content)}
      </table>
    </div>
    """
    return html

def generate_html_grouped_invoice(records, due_month_str, due_year_str, tenant_type, notice_content=None, rpu_val=None):
    """Create one invoice page for a resident owning multiple flats (e.g. JHD A-1, F-1, F-2)."""
    if not records:
        return ""

    if rpu_val is None:
        rpu_val = RATE_COMMERCIAL if tenant_type == "COMMERCIAL" else RATE_DOMESTIC

    # Stable flat order for JHD: A-1, F-1, F-2
    records = sorted(records, key=lambda r: {"A-1": 0, "F-1": 1, "F-2": 2}.get(canonical_flat(r.get("Flat_No", "")), 99))
    tenant = str(records[0].get("Tenant_Name", "JHD"))

    yr_display = str(due_year_str)[-2:] if len(str(due_year_str)) == 4 else str(due_year_str)
    period_display = f"{due_month_str.title()[:3]} {yr_display}"

    total_elec = sum(float(r.get("Electric_Charges_Rs", 0) or 0) for r in records)
    total_fixed = sum(float(r.get("Fixed_Meter_Charges_Rs", 0) or 0) for r in records)
    total_tax = sum(float(r.get("Municipal_Tax_Rs", 0) or 0) for r in records)
    total_water = sum(float(r.get("Water_Charges_Rs", 0) or 0) for r in records)
    total_maint = sum(float(r.get("Building_Maint_Fund_Rs", 0) or 0) for r in records)
    total_lift = sum(float(r.get("Lift_Charges_Rs", 0) or 0) for r in records)
    total_others = sum(float(r.get("Others_Charges_Rs", 0) or 0) for r in records)
    total_gross = int(total_elec + total_fixed + total_tax + total_water + total_maint + total_lift + total_others + 0.5)
    total_units = sum(float(r.get("Consumed_Units", 0) or 0) for r in records)

    # Map readings per flat
    rec_map = {canonical_flat(r.get("Flat_No", "")): r for r in records}
    r_a1 = rec_map.get("A-1", records[0] if len(records) > 0 else {})
    r_f1 = rec_map.get("F-1", records[1] if len(records) > 1 else {})
    r_f2 = rec_map.get("F-2", records[2] if len(records) > 2 else {})

    cl_a1 = fmt_num(float(r_a1.get("Closing_Meter_Reading", 0) or 0))
    cl_f1 = fmt_num(float(r_f1.get("Closing_Meter_Reading", 0) or 0))
    cl_f2 = fmt_num(float(r_f2.get("Closing_Meter_Reading", 0) or 0))

    op_a1 = fmt_num(float(r_a1.get("Open_Meter_Reading", 0) or 0))
    op_f1 = fmt_num(float(r_f1.get("Open_Meter_Reading", 0) or 0))
    op_f2 = fmt_num(float(r_f2.get("Open_Meter_Reading", 0) or 0))

    u_a1 = fmt_num(float(r_a1.get("Consumed_Units", 0) or 0))
    u_f1 = fmt_num(float(r_f1.get("Consumed_Units", 0) or 0))
    u_f2 = fmt_num(float(r_f2.get("Consumed_Units", 0) or 0))

    rate = rpu_val

    elec_a1 = fmt_num(float(r_a1.get("Electric_Charges_Rs", 0) or 0))
    elec_f1 = fmt_num(float(r_f1.get("Electric_Charges_Rs", 0) or 0))
    elec_f2 = fmt_num(float(r_f2.get("Electric_Charges_Rs", 0) or 0))

    fixed_a1 = fmt_num(float(r_a1.get("Fixed_Meter_Charges_Rs", 0) or 0))
    fixed_f1 = float(r_f1.get("Fixed_Meter_Charges_Rs", 0) or 0)
    fixed_f2 = float(r_f2.get("Fixed_Meter_Charges_Rs", 0) or 0)
    fixed_f1_f2_combine = fmt_num(fixed_f1 + fixed_f2)

    maint_a1 = fmt_num(float(r_a1.get("Building_Maint_Fund_Rs", 0) or 0))
    maint_f1 = float(r_f1.get("Building_Maint_Fund_Rs", 0) or 0)
    maint_f2 = float(r_f2.get("Building_Maint_Fund_Rs", 0) or 0)
    maint_f1_f2_combine = fmt_num(maint_f1 + maint_f2)

    lift_a1 = fmt_num(float(r_a1.get("Lift_Charges_Rs", 0) or 0))
    lift_f1 = float(r_f1.get("Lift_Charges_Rs", 0) or 0)
    lift_f2 = float(r_f2.get("Lift_Charges_Rs", 0) or 0)
    lift_f1_f2_combine = fmt_num(lift_a1 if (lift_f1 + lift_f2) == 0 else (lift_f1 + lift_f2))

    water_str = fmt_num(total_water) if total_water > 0 else ""
    others_str = fmt_num(total_others)

    others_row = f"""
    <tr>
      <td>Miscellaneous / Others Overheads</td>
      <td class="col-rs center">{others_str}</td>
      <td class="col-p"></td>
    </tr>""" if total_others and total_others > 0 else ""

    html = f"""
    <div style='page-break-after: always; page-break-inside: avoid;'>
      <table class="header-box" cellspacing="0" cellpadding="0">
        <tr>
          <td>
            <span class="title">BASANT JAMINI BHAWAN WELFARE ASSOCIATION</span><br/>
            <span class="sub-title">Contractor's Area Road No. 2 Bistupur, Jamshedpur - 831001</span><br/>
            <span class="charge-title">Monthly Maintenance Charge</span>
          </td>
        </tr>
      </table>

      <table class="meta-table" cellspacing="0" cellpadding="0">
        <tr>
          <td style="width: 55%;">Name : {tenant}</td>
          <td style="width: 45%;"></td>
        </tr>
        <tr>
          <td>Flat No. ( A-1 , F-1 , F-2 )</td>
          <td style="text-align: right;">Due Month &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {period_display}</td>
        </tr>
      </table>

      <table class="main-table" cellspacing="0" cellpadding="0">
        <tr>
          <td class="col-desc center bold" style="font-size: 9.5pt;">DESCRIPTION</td>
          <td colspan="2" class="center bold" style="font-size: 9.5pt;">AMOUNT</td>
        </tr>
        <tr>
          <td>&nbsp;</td>
          <td class="col-rs center bold" style="font-size: 8.5pt;">Rs.</td>
          <td class="col-p center bold" style="font-size: 8.5pt;">P.</td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 40%;">&nbsp;</td>
                <td style="width: 20%; text-align: center;">A-1</td>
                <td style="width: 20%; text-align: center;">F-1</td>
                <td style="width: 20%; text-align: center;">F-2</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 40%;">Closing Meter Reading</td>
                <td style="width: 20%; text-align: center;">{cl_a1}</td>
                <td style="width: 20%; text-align: center;">{cl_f1}</td>
                <td style="width: 20%; text-align: center;">{cl_f2}</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 40%;">&nbsp;</td>
                <td style="width: 20%; text-align: center;">A-1</td>
                <td style="width: 20%; text-align: center;">F-1</td>
                <td style="width: 20%; text-align: center;">F-2</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 40%;">Opening Meter Reading</td>
                <td style="width: 20%; text-align: center;">{op_a1}</td>
                <td style="width: 20%; text-align: center;">{op_f1}</td>
                <td style="width: 20%; text-align: center;">{op_f2}</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 40%;">Chargeable Unit</td>
                <td style="width: 20%; text-align: center;">{u_a1}</td>
                <td style="width: 20%; text-align: center;">{u_f1}</td>
                <td style="width: 20%; text-align: center;">{u_f2}</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Total unit Consumed As per individual meter : &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {fmt_num(total_units)} units ( A1, F1,F2 )</td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Electric Charges ( Commercial )</td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 14%;">&nbsp;</td>
                <td style="width: 26%; text-align: center;">Meter unit</td>
                <td style="width: 60%; text-align: center;">Elec. Charge / Unit ( in Rs.)</td>
              </tr>
            </table>
          </td>
          <td class="col-rs"></td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 14%;">A-1</td>
                <td style="width: 26%; text-align: center;">{u_a1}</td>
                <td style="width: 60%; text-align: center;">{rate:.2f}/-</td>
              </tr>
            </table>
          </td>
          <td class="col-rs center">{elec_a1}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 14%;">F-1</td>
                <td style="width: 26%; text-align: center;">{u_f1}</td>
                <td style="width: 60%; text-align: center;">{rate:.2f}/-</td>
              </tr>
            </table>
          </td>
          <td class="col-rs center">{elec_f1}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>
            <table class="inner-tbl">
              <tr>
                <td style="width: 14%;">F-2</td>
                <td style="width: 26%; text-align: center;">{u_f2}</td>
                <td style="width: 60%; text-align: center;">{rate:.2f}/-</td>
              </tr>
            </table>
          </td>
          <td class="col-rs center">{elec_f2}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Fixed Meter Charges : &nbsp;&nbsp;&nbsp;&nbsp; ( A-1 : Rs. {fixed_a1}/-) + ( F-1 and F-2 combine Rs. {fixed_f1_f2_combine}/-)</td>
          <td class="col-rs center">{fmt_num(total_fixed)}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Municipal Tax</td>
          <td class="col-rs center">{fmt_num(total_tax)}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Water Charges</td>
          <td class="col-rs center">{water_str}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Building Maint. fund : &nbsp;&nbsp;&nbsp;&nbsp; ( A-1 : Rs. {maint_a1}/-) + ( F-1 and F-2 combine Rs. {maint_f1_f2_combine}/-)</td>
          <td class="col-rs center">{fmt_num(total_maint)}</td>
          <td class="col-p"></td>
        </tr>
        <tr>
          <td>Lift Charges : &nbsp;&nbsp;&nbsp;&nbsp; ( A-1 : Rs. {lift_a1}/-) + ( F-1 and F-2 combine Rs. {lift_f1_f2_combine}/-)</td>
          <td class="col-rs center">{fmt_num(total_lift)}</td>
          <td class="col-p"></td>
        </tr>
        {others_row}
        <tr>
          <td class="right bold" style="font-size: 9.5pt; padding-right: 14px;">TOTAL</td>
          <td class="col-rs center bold" style="font-size: 9.5pt;">{total_gross}</td>
          <td class="col-p"></td>
        </tr>
        {build_notice_rows_html(notice_content)}
      </table>
    </div>
    """
    return html

def compile_pdf_bytes(compiled_html):
    """Compiles raw HTML content into PDF binary bytes using xhtml2pdf."""
    full_html = PDF_HTML_WRAPPER.format(compiled_html=compiled_html)
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(full_html, dest=pdf_buffer)
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf compilation error code: {pisa_status.err}")
    return pdf_buffer.getvalue()
