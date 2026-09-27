import csv
import json
import sys
import subprocess
from datetime import datetime
import os
DATA_FILE = "symptom_assessments.json"
CSV_FILE = "symptom_assessments.csv"
XLSX_FILE = "symptom_assessments.xlsx"
FIELDS = ["timestamp", "user_input", "ai_response"]
# --- Data Persistence Functions ---

def load_records(filename=DATA_FILE):
    """Loads records from a JSON file. Returns an empty list on missing/corrupt files."""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            records = json.load(f)
            if isinstance(records, list):
                return records
            return []
    except (json.JSONDecodeError, IOError, OSError) as e:
        print(f"[Warning] Could not load '{filename}' due to error: {e}. Starting with an empty record set.")
        return []

def save_record(user_input, response_text, filename=DATA_FILE):
    """Appends a single assessment record to the JSON file safely."""
    records = load_records(filename)
    new_record = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "ai_response": response_text
    }
    records.append(new_record)
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4, ensure_ascii=False)
    except (IOError, OSError) as e:
        print(f"[Warning] Failed to save record to disk: {e}")

def filter_records_by_keyword(keyword, records=None):
    """Queries saved records for a specific keyword in user input or response."""
    if records is None:
        records = load_records()
        
    keyword_lower = keyword.lower()
    return [
        r for r in records 
        if keyword_lower in r["user_input"].lower() or keyword_lower in r["ai_response"].lower()
    ]
# --- Exporting to Excel (CSV) ---
def convert_json_to_xlsx(xlsx_file=XLSX_FILE):
    """Writes all saved records to an Excel workbook."""
    try:
        from openpyxl import Workbook
    except ImportError:
        print("Excel export needs the 'openpyxl' package.")
        print("Install it with: pip install openpyxl")
        print("Or use the 'export' command to save a CSV instead, which Excel can also open.")
        return None

    records = load_records()
    if not records:
        print("No records to export yet.")
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Assessments"
    ws.append(FIELDS)
    for record in records:
        ws.append([record.get(field, "") for field in FIELDS])

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 80

    try:
        wb.save(xlsx_file)
    except OSError as e:
        print(f"Error: could not write '{xlsx_file}': {e}")
        return None

    print(f"Exported {len(records)} record(s) to '{xlsx_file}'.")
    return len(records)

def convert_json_to_csv(json_file=DATA_FILE, csv_file=CSV_FILE):
    """Read the JSON records and write them to a CSV file.
    Returns the number of records written, or None on failure."""
    if not os.path.exists(json_file):
        print(f"Error: '{json_file}' not found.")
        return None
 
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            records = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Error: could not read '{json_file}': {e}")
        return None
 
    if not isinstance(records, list):
        print(f"Error: '{json_file}' does not contain a list of records.")
        return None
 
    try:
        # utf-8-sig lets Excel open the file with correct characters;
        # newline="" stops blank lines appearing on Windows.
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            for record in records:
                writer.writerow({field: record.get(field, "") for field in FIELDS})
    except OSError as e:
        print(f"Error: could not write '{csv_file}': {e}")
        return None
 
    print(f"Converted {len(records)} record(s) to '{csv_file}'.")
    return len(records)

# --- Opening the CSV file in Excel ---
def open_file(filename=XLSX_FILE):
    """Opens a file with the system's default application."""
    if not os.path.exists(filename):
        print(f"'{filename}' not found. Type 'export xlsx' first to create it.")
        return False

    try:
        if sys.platform.startswith("win"):
            os.startfile(filename)
        elif sys.platform == "darwin":
            subprocess.run(["open", filename], check=True)
        else:
            subprocess.run(["xdg-open", filename], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"Could not open '{filename}': {e}")
        return False

    print(f"Opening '{filename}'...")
    return True

