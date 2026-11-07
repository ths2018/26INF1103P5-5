"""
data_manager.py - backwards-compatible entry point.

The real code now lives in the `casedata` package (one module per class).
This file keeps the old module-level functions so existing code such as
`data_manager.add_log(...)` or `data_manager.show_history(...)` keeps working,
and re-exports the classes for anyone who wants to use them directly.
"""
import input_output_manager
from casedata import *  # noqa: F401,F403  (re-export all classes and constants)
from casedata import (CSV_FILE, XLSX_FILE, CaseManager, CsvExporter,
                      HistoryViewer, JsonCaseRepository, PerCaseReport,
                      UrgencySummaryReport, XlsxExporter, create_repository)

_manager = None


def get_manager():
    """Lazily builds the default CaseManager using the configured backend."""
    global _manager
    if _manager is None:
        _manager = CaseManager(create_repository())
        # First run on a database backend: pull in any legacy JSON cases.
        if not isinstance(_manager.repository, JsonCaseRepository) \
                and not _manager.repository.list_all():
            migrated = _manager.import_from(JsonCaseRepository())
            if migrated:
                input_output_manager.print_output(
                    f"Imported {migrated} existing JSON case(s) into the database.")
    return _manager


def get_backend_name():
    """Name of the storage backend in use, e.g. 'MongoCaseRepository'."""
    return type(get_manager().repository).__name__


# --- Original API ---
def create_new_case():                      return get_manager().create_new_case()
def get_active_case():                      return get_manager().get_active_case()
def close_case(case):                       return get_manager().close_case(case)
def add_log(case, user_input, response_text): return get_manager().add_log(case, user_input, response_text)
def load_all_logs():                        return get_manager().load_all_logs()
def filter_records_by_keyword(keyword, records=None): return get_manager().filter_records_by_keyword(keyword, records)
def convert_json_to_csv(csv_file=CSV_FILE): return get_manager().export(CsvExporter(), csv_file)
def convert_json_to_xlsx(xlsx_file=XLSX_FILE): return get_manager().export(XlsxExporter(), xlsx_file)
def show_history(results, page_size=2):     return HistoryViewer(results, page_size).show()


# --- Search / statistics ---
def search_records(query):                  return get_manager().search(query)


def show_stats(query="", per_case=False):
    """Prints urgency statistics for the records matching `query` (all if empty)."""
    mgr = get_manager()
    records = mgr.search(query) if query else mgr.load_all_logs()
    report = PerCaseReport() if per_case else UrgencySummaryReport()
    input_output_manager.print_output(mgr.report(report, records))


# --- CRUD helpers ---
def get_case(case_id):                      return get_manager().get_case(case_id)
def list_cases():                           return get_manager().list_cases()
def delete_case(case_id):                   return get_manager().delete_case(case_id)
def update_log(case, index, user_input=None, ai_response=None):
    return get_manager().update_log(case, index, user_input, ai_response)
def delete_log(case, index):                return get_manager().delete_log(case, index)
