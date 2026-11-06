"""CsvExporter: writes records to a CSV file."""


import csv

from ..config import CSV_FILE, EXPORT_FIELDS
from .base import BaseExporter


class CsvExporter(BaseExporter):
    default_path = CSV_FILE

    def _write(self, records, path):
        # utf-8-sig lets Excel read the characters correctly;
        # newline="" stops blank lines appearing on Windows.
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(EXPORT_FIELDS)
            for record in records:
                writer.writerow(self._row(record))
