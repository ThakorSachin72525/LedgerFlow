import pdfplumber
import re
import pandas as pd


DATE_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{4}")
NUMBER_PATTERN = re.compile(r"^\d{1,3}(?:,\d{3})*\.\d{2}$")


def safe_float(value):
    """Safely convert string to float."""
    if not value:
        return 0.0

    value = value.replace(",", "").strip()

    try:
        return float(value)
    except Exception:
        return 0.0


def extract_transactions_from_pdf(pdf_path, password=None):
    settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
    }

    raw_rows = []
    opening_balance = None
    closing_balance = None

    # ---------------------------
    # Extract raw table rows
    # ---------------------------
    with pdfplumber.open(pdf_path, password=password) as pdf:
        for page in pdf.pages:
            table = page.extract_table(settings)
            if table:
                raw_rows.extend(table)

    if not raw_rows:
        raise ValueError("No table data found in PDF.")

    # ---------------------------
    # Merge multiline rows
    # ---------------------------
    merged_rows = []
    current_row = None

    for row in raw_rows:

        if not any(row):
            continue

        first_cell = str(row[0]).strip() if row[0] else ""

        # Skip header row
        if first_cell.startswith("Txn Date"):
            continue

        # Opening Balance
        if first_cell.startswith("Opening Balance"):
            match = re.search(r"([\d,]+\.\d{2})", first_cell)
            if match:
                opening_balance = float(match.group(1).replace(",", ""))
            continue

        # Closing Balance
        if first_cell.startswith("Closing Balance"):
            match = re.search(r"([\d,]+\.\d{2})", first_cell)
            if match:
                closing_balance = float(match.group(1).replace(",", ""))
            continue

        # New transaction row
        if DATE_PATTERN.match(first_cell):
            if current_row:
                merged_rows.append(current_row)
            current_row = list(row)
        else:
            # Continuation row
            if current_row:
                for i in range(len(row)):
                    if row[i] and row[i].strip():
                        if current_row[i]:
                            current_row[i] = (
                                str(current_row[i]).strip() + " " + str(row[i]).strip()
                            )
                        else:
                            current_row[i] = str(row[i]).strip()

    if current_row:
        merged_rows.append(current_row)

    # ---------------------------
    # Clean & Normalize
    # ---------------------------
    cleaned_data = []

    for row in merged_rows:

        # Ensure row length safety
        while len(row) < 6:
            row.append("")

        date = row[0].strip() if row[0] else ""
        description = row[1].replace("\n", " ").strip() if row[1] else ""

        withdrawal = 0.0
        deposit = 0.0

        # Detect numeric values safely
        for cell in row[2:6]:
            if cell:
                value = cell.strip()
                if NUMBER_PATTERN.match(value):
                    amount = safe_float(value)

                    # Decide debit or credit based on column position
                    if cell == row[2]:
                        withdrawal = amount
                    elif cell == row[3]:
                        deposit = amount

        cleaned_data.append({
            "txn_date": date,
            "description": description,
            "withdrawal": withdrawal,
            "deposit": deposit,
            "txn_type": "DEBIT" if withdrawal > 0 else "CREDIT",
        })

    df = pd.DataFrame(cleaned_data)

    return df, opening_balance, closing_balance