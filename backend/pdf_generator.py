"""
PDF Generator for Basant Jamini Bhawan Welfare Association
Generates high-quality A4 PDF statements with white backgrounds, bold headlines,
reinforced 2px borders, and bold numbers.
"""

import io
from datetime import datetime
from xhtml2pdf import pisa
from billing_core import canonical_flat

PDF_HTML_WRAPPER = """
<html>
<head>
    <meta charset='utf-8'>
    <style>
        @page {{
            size: a4 portrait;
            margin: 22pt 30pt 20pt 30pt;
        }}
        body {{
            font-family: 'Helvetica', 'Arial', sans-serif;
            color: #000000;
            font-size: 14px;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
        }}
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
        .meta-table {{
            font-size: 14px;
            line-height: 1.2;
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

def generate_html_single_bill(flat_no, cfg, due_month_str, due_year_str, prev_r, float_curr, consumed, elec_charge, others_val, total, tenant_type, com_area_val, notice_content, meter_units=None):
    """Generates the HTML statement for a single flat."""
    total = int(total + 0.5)

    if meter_units is None:
        meter_units = max(0.0, float(consumed) - float(com_area_val)) if tenant_type == "DOMESTIC" else float(consumed)
    else:
        meter_units = float(meter_units)

    water_row = f"<tr><td class='td-item'>Water Utility Charges</td><td class='td-item' style='text-align: right;'><b>Rs. {cfg.get('water', 0.0):.2f}</b></td></tr>" if tenant_type == "COMMERCIAL" else ""

    if tenant_type == "DOMESTIC" and com_area_val > 0:
        metrics_box_html = f"""
        <div class='metrics-box'>
            <b>Meter Readings:</b> Opening [<b>{prev_r:.2f}</b>] | Closing [<b>{float_curr:.2f}</b>] | Consumed Units: <b>{meter_units:.2f}</b><br/>
            <b>Units Calculation:</b> Consumed Units [<b>{meter_units:.2f}</b>] + Common Area Share [<b>{com_area_val:.2f}</b>] = <b>Total Consumed Units: {consumed:.2f}</b>
        </div>"""
        elec_row = f"<tr><td class='td-item'>Electricity Consumption Charges (Total <b>{consumed:.2f}</b> Consumed Units)</td><td class='td-item' style='text-align: right;'><b>Rs. {elec_charge:.2f}</b></td></tr>"
    else:
        metrics_box_html = f"""
        <div class='metrics-box'>
            <b>Meter Readings:</b> Opening [<b>{prev_r:.2f}</b>] | Closing [<b>{float_curr:.2f}</b>] | Total Consumed Units: <b>{consumed:.2f}</b>
        </div>"""
        elec_row = f"<tr><td class='td-item'>Electricity Consumption Charges</td><td class='td-item' style='text-align: right;'><b>Rs. {elec_charge:.2f}</b></td></tr>"

    fixed_val = cfg.get("fixed", 0.0)
    if isinstance(fixed_val, list):
        fixed_val = fixed_val[0].get("val", 0.0) if fixed_val else 0.0

    return f"""
    <div style='margin-bottom: 3px; page-break-after: always; page-break-inside: avoid;'>
        <table width='100%' class='header-table' cellspacing='0'>
            <tr>
                <td>
                    <div class='header-title'>BASANT JAMINI BHAWAN WELFARE ASSOCIATION</div>
                    <div class='header-subtitle'>Monthly Maintenance & Electricity Statement [{tenant_type}]</div>
                </td>
            </tr>
        </table>
        <div class='section-gap'></div>
        <table width='100%' class='meta-table' cellspacing='0'>
            <tr>
                <td><b>Flat No:</b> <b>{flat_no}</b></td>
                <td style='text-align: right;'><b>Billing Period:</b> <b>{due_month_str}-{due_year_str}</b></td>
            </tr>
            <tr>
                <td><b>Resident Name:</b> <b>{cfg.get('tenant', 'N/A')}</b></td>
                <td style='text-align: right;'><b>Issue Date:</b> <b>{datetime.now().strftime('%d-%m-%Y')}</b></td>
            </tr>
        </table>
        <div class='section-gap'></div>
        {metrics_box_html}
        <div class='section-gap'></div>
        <table width='100%' cellspacing='0' cellpadding='0'>
            <tr>
                <td class='th-item'><b>Charge Description Item</b></td>
                <td class='th-item' style='text-align: right;'><b>Amount (Rs.)</b></td>
            </tr>
            {elec_row}
            <tr>
                <td class='td-item'>Fixed Meter Maintenance Charges</td>
                <td class='td-item' style='text-align: right;'><b>Rs. {float(fixed_val):.2f}</b></td>
            </tr>
            <tr>
                <td class='td-item'>Municipal Property Tax</td>
                <td class='td-item' style='text-align: right;'><b>Rs. {cfg.get('tax', 0.0):.2f}</b></td>
            </tr>
            {water_row}
            <tr>
                <td class='td-item'>Building Maintenance Fund</td>
                <td class='td-item' style='text-align: right;'><b>Rs. {cfg.get('maintenance', 0.0):.2f}</b></td>
            </tr>
            <tr>
                <td class='td-item'>Lift Operational Share Fee</td>
                <td class='td-item' style='text-align: right;'><b>Rs. {cfg.get('lift', 0.0):.2f}</b></td>
            </tr>
            <tr>
                <td class='td-item'>Miscellaneous / Others Overheads</td>
                <td class='td-item' style='text-align: right;'><b>Rs. {others_val:.2f}</b></td>
            </tr>
        </table>
        <div class='section-gap'></div>
        <div class='total-box'>
            <b>CUMULATIVE GROSS AMOUNT DUE: Rs. {total:.0f}</b>
        </div>
        <div class='section-gap'></div>
        <div class='notice-box'>
            {notice_content.replace(chr(10), '<br/>')}
        </div>
        <div class='section-gap'></div>
        <div class='footer-text'>
            This is a computer-generated digital statement issued by Basant Jamini Bhawan Welfare Association Hub.
        </div>
    </div>
    """

def generate_html_grouped_invoice(records, due_month_str, due_year_str, tenant_type, notice_content):
    """Generates a consolidated multi-flat invoice statement (e.g. for JHD owning A-1, F-1, F-2)."""
    if not records:
        return ""

    records = sorted(records, key=lambda r: {"A-1": 0, "F-1": 1, "F-2": 2}.get(canonical_flat(r.get("Flat_No", "")), 99))
    tenant = str(records[0].get("Tenant_Name", "JHD"))
    flat_names = [canonical_flat(r.get("Flat_No", "")) for r in records]

    total_elec = sum(float(r.get("Electric_Charges_Rs", 0) or 0) for r in records)
    total_fixed = sum(float(r.get("Fixed_Meter_Charges_Rs", 0) or 0) for r in records)
    total_tax = sum(float(r.get("Municipal_Tax_Rs", 0) or 0) for r in records)
    total_water = sum(float(r.get("Water_Charges_Rs", 0) or 0) for r in records)
    total_maint = sum(float(r.get("Building_Maint_Fund_Rs", 0) or 0) for r in records)
    total_lift = sum(float(r.get("Lift_Charges_Rs", 0) or 0) for r in records)
    total_others = sum(float(r.get("Others_Charges_Rs", 0) or 0) for r in records)
    total_gross = int(total_elec + total_fixed + total_tax + total_water + total_maint + total_lift + total_others + 0.5)
    total_units = sum(float(r.get("Consumed_Units", 0) or 0) for r in records)

    water_row = f"<tr><td class='td-item'>Water Utility Charges</td><td class='td-item' style='text-align:right;'><b>Rs. {total_water:.2f}</b></td></tr>" if tenant_type == "COMMERCIAL" else ""

    flat_rows = ""
    for r in records:
        flat = canonical_flat(r.get("Flat_No", ""))
        op = float(r.get("Open_Meter_Reading", 0) or 0)
        cl = float(r.get("Closing_Meter_Reading", 0) or 0)
        units = float(r.get("Consumed_Units", 0) or 0)
        flat_rows += f"""
            <tr>
                <td class='td-item'><b>{flat}</b></td>
                <td class='td-item' style='text-align:right;'><b>{op:.2f}</b></td>
                <td class='td-item' style='text-align:right;'><b>{cl:.2f}</b></td>
                <td class='td-item' style='text-align:right;'><b>{units:.2f}</b></td>
                <td class='td-item' style='text-align:right;'><b>Rs. {float(r.get('Electric_Charges_Rs',0) or 0):.2f}</b></td>
            </tr>"""

    if tenant_type == "DOMESTIC":
        common_units = sum(float(r.get("Common_Area_Units", 0) or 0) for r in records)
        if common_units > 0:
            metrics_box_html = f"<div class='metrics-box'><b>Combined Meter Consumption:</b> Consumed Units: <b>{total_units:.2f}</b> + Common Area Share: <b>{common_units:.2f}</b> = <b>Total Consumed Units: {total_units + common_units:.2f}</b> across <b>{len(records)}</b> flat(s)</div>"
            elec_row = f"<tr><td class='td-item'>Electricity Consumption Charges (Total <b>{total_units + common_units:.2f}</b> Consumed Units)</td><td class='td-item' style='text-align:right;'><b>Rs. {total_elec:.2f}</b></td></tr>"
        else:
            metrics_box_html = f"<div class='metrics-box'><b>Combined Meter Consumption:</b> Total Units: <b>{total_units:.2f}</b> across <b>{len(records)}</b> flat(s)</div>"
            elec_row = f"<tr><td class='td-item'>Electricity Consumption Charges</td><td class='td-item' style='text-align:right;'><b>Rs. {total_elec:.2f}</b></td></tr>"
    else:
        metrics_box_html = f"<div class='metrics-box'><b>Combined Meter Consumption:</b> Total Units: <b>{total_units:.2f}</b> across <b>{len(records)}</b> flat(s)</div>"
        elec_row = f"<tr><td class='td-item'>Electricity Consumption Charges</td><td class='td-item' style='text-align:right;'><b>Rs. {total_elec:.2f}</b></td></tr>"

    return f"""
    <div style='margin-bottom:3px; page-break-after:always; page-break-inside:avoid;'>
        <table width='100%' class='header-table' cellspacing='0'>
            <tr><td><div class='header-title'>BASANT JAMINI BHAWAN WELFARE ASSOCIATION</div>
            <div class='header-subtitle'>Monthly Maintenance & Electricity Statement [{tenant_type}]</div></td></tr>
        </table>
        <div class='section-gap'></div>
        <table width='100%' class='meta-table' cellspacing='0'>
            <tr><td><b>Resident Name:</b> <b>{tenant}</b></td><td style='text-align:right;'><b>Billing Period:</b> <b>{due_month_str}-{due_year_str}</b></td></tr>
            <tr><td><b>Flat Nos:</b> <b>{', '.join(flat_names)}</b></td><td style='text-align:right;'><b>Issue Date:</b> <b>{datetime.now().strftime('%d-%m-%Y')}</b></td></tr>
        </table>
        <div class='section-gap'></div>
        {metrics_box_html}
        <div class='section-gap'></div>
        <table width='100%' cellspacing='0' cellpadding='0'>
            <tr><td class='th-item'><b>Flat</b></td><td class='th-item' style='text-align:right;'><b>Opening</b></td><td class='th-item' style='text-align:right;'><b>Closing</b></td><td class='th-item' style='text-align:right;'><b>Units</b></td><td class='th-item' style='text-align:right;'><b>Electricity</b></td></tr>
            {flat_rows}
        </table>
        <div class='section-gap'></div>
        <table width='100%' cellspacing='0' cellpadding='0'>
            <tr><td class='th-item'><b>Combined Charge Description</b></td><td class='th-item' style='text-align:right;'><b>Amount (Rs.)</b></td></tr>
            {elec_row}
            <tr><td class='td-item'>Fixed Meter Maintenance Charges (<b>{len(records)}</b> flats)</td><td class='td-item' style='text-align:right;'><b>Rs. {total_fixed:.2f}</b></td></tr>
            <tr><td class='td-item'>Municipal Property Tax</td><td class='td-item' style='text-align:right;'><b>Rs. {total_tax:.2f}</b></td></tr>
            {water_row}
            <tr><td class='td-item'>Building Maintenance Fund (<b>{len(records)}</b> flats)</td><td class='td-item' style='text-align:right;'><b>Rs. {total_maint:.2f}</b></td></tr>
            <tr><td class='td-item'>Lift Operational Share Fee (combined)</td><td class='td-item' style='text-align:right;'><b>Rs. {total_lift:.2f}</b></td></tr>
            <tr><td class='td-item'>Miscellaneous / Others Overheads</td><td class='td-item' style='text-align:right;'><b>Rs. {total_others:.2f}</b></td></tr>
        </table>
        <div class='section-gap'></div>
        <div class='total-box'><b>CUMULATIVE GROSS AMOUNT DUE: Rs. {total_gross:.0f}</b></div>
        <div class='section-gap'></div>
        <div class='notice-box'>{notice_content.replace(chr(10), '<br/>')}</div>
        <div class='section-gap'></div>
        <div class='footer-text'>This is a computer-generated digital statement issued by Basant Jamini Bhawan Welfare Association Hub.</div>
    </div>
    """

def compile_pdf_bytes(compiled_html):
    """Compiles raw HTML content into PDF binary bytes using xhtml2pdf."""
    full_html = PDF_HTML_WRAPPER.format(compiled_html=compiled_html)
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(full_html, dest=pdf_buffer)
    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf compilation error code: {pisa_status.err}")
    return pdf_buffer.getvalue()
