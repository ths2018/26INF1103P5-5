"""Paths, constants and tiny shared helpers."""


import os
import re


# Project root = folder that contains the casedata package (and data_manager.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASE_DIR = os.path.join(BASE_DIR, "case")

CSV_FILE = os.path.join(CASE_DIR, "case.csv")
XLSX_FILE = os.path.join(CASE_DIR, "case.xlsx")
DB_FILE = os.path.join(CASE_DIR, "cases.db")

EXPORT_FIELDS = ["case_id", "timestamp", "user_input", "ai_response"]

CASE_PATTERN = re.compile(r"case_(\d+)\.json")
CASE_ID_PATTERN = re.compile(r"case_(\d+)")


def case_number(case_id):
    """Numeric part of 'case_12' -> 12 (used for sorting and for next id)."""
    match = CASE_ID_PATTERN.fullmatch(str(case_id))
    return int(match.group(1)) if match else 0
