"""XlsxExporter: writes records to a formatted Excel workbook."""


from ..config import EXPORT_FIELDS, XLSX_FILE
from .base import BaseExporter


class XlsxExporter(BaseExporter):
    default_path = XLSX_FILE
    dependency_hint = (
        "Excel export needs the 'openpyxl' package.\n"
        "Install it with: python -m pip install openpyxl\n"
        "Or use the 'export' command to save a CSV instead, which Excel can also open."
    )

    # (text the response starts with, fill colour)
    _RULES = [
        ("urgency classification: insufficient_information", "808080"),  # grey
        ("urgency classification: emergency",                "FFC7CE"),  # red
        ("urgency classification: non-urgent",               "FFFF00"),  # yellow
        ("urgency classification: urgent",                   "FFA500"),  # orange
    ]

    def _write(self, records, path):
        from openpyxl import Workbook  # ImportError handled in BaseExporter.export
        from openpyxl.styles import Alignment, Border, Side, PatternFill
        from openpyxl.formatting.rule import FormulaRule

        wb = Workbook()
        ws = wb.active
        ws.title = "Assessments"
        ws.append(EXPORT_FIELDS)
        for record in records:
            ws.append(self._row(record))

        for column, width in zip("ABCD", (12, 25, 50, 80)):
            ws.column_dimensions[column].width = width

        wrap = Alignment(wrap_text=True, vertical="top")
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=len(EXPORT_FIELDS)):
            for cell in row:
                cell.alignment = wrap

        # Bold line under the last row of each case
        thick = Border(bottom=Side(style="medium"))
        for i in range(len(records) - 1):
            if records[i].get("case_id") != records[i + 1].get("case_id"):
                for cell in ws[i + 2][:len(EXPORT_FIELDS)]:
                    cell.border = thick

        col = chr(ord("A") + EXPORT_FIELDS.index("ai_response"))
        rng = f"{col}2:{col}{ws.max_row}"
        first = f"{col}2"
        for text, colour in self._RULES:
            fill = PatternFill(start_color=colour, end_color=colour, fill_type="solid")
            ws.conditional_formatting.add(
                rng,
                FormulaRule(formula=[f'LEFT(LOWER({first}),{len(text)})="{text}"'], fill=fill),
            )
        wb.save(path)
