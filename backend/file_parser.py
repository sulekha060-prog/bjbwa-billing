"""
Document Parser for Basant Jamini Bhawan Welfare Association
Extracts month, year, and opening/closing meter readings from uploaded files.
Supports PDF, DOCX, TXT, and CSV.
"""

import re
from datetime import datetime

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import docx
except ImportError:
    docx = None

def extract_text_from_file(file_bytes, filename):
    """Extracts raw text from uploaded document bytes."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    text = ""

    if ext == 'pdf':
        if not pdfplumber:
            raise RuntimeError("pdfplumber library is not installed.")
        import io
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

    elif ext == 'docx':
        if not docx:
            raise RuntimeError("python-docx library is not installed.")
        import io
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([p.text for p in doc.paragraphs])

    else:
        # Default txt / csv / plain text
        try:
            text = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            text = file_bytes.decode('latin-1', errors='ignore')

    return text

def parse_meter_reading_document(file_bytes, filename, flat_configs):
    """
    Parses document text for billing month, year, and opening/closing readings per flat.
    Returns: {
        "month": str,
        "year": str,
        "extracted_metrics": { flat_no: [opening, closing] },
        "raw_text_preview": str
    }
    """
    content = extract_text_from_file(file_bytes, filename)

    months_regex = r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|JAN|FEB|MAR|APR|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
    month_found = re.search(months_regex, content, re.IGNORECASE)
    year_found = re.search(r"\b(20\d{2})\b", content)

    target_month = month_found.group(1)[:3].upper() if month_found else "JAN"
    target_year = year_found.group(1) if year_found else str(datetime.now().year)

    raw_lines = content.split('\n')
    cleaned_lines = [line.strip() for line in raw_lines if line.strip() and "--- PAGE" not in line]

    extracted_temp_metrics = {}

    for flat_key in flat_configs.keys():
        alt_flat_key = flat_key.replace("-", "")
        pattern = rf"\b({flat_key}|{alt_flat_key})\b"
        for line in cleaned_lines:
            if re.search(pattern, line, re.IGNORECASE):
                tokens = re.split(r'[\s,\t\|]+', line)
                numeric_values = []
                for tok in tokens:
                    tok_cleaned = re.sub(r'[^\d\.]', '', tok)
                    if tok_cleaned != "":
                        try:
                            numeric_values.append(float(tok_cleaned))
                        except ValueError:
                            pass
                clean_metrics = [v for v in numeric_values if v not in [1, 2, 3, 4]]
                while len(clean_metrics) < 2:
                    clean_metrics.append(0.0)
                extracted_temp_metrics[flat_key] = [clean_metrics[0], clean_metrics[1]]
                break

    return {
        "month": target_month,
        "year": target_year,
        "extracted_metrics": extracted_temp_metrics,
        "raw_text_preview": content[:1000]
    }
