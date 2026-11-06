"""CaseManager: high-level case operations on top of any CaseRepository."""


from datetime import datetime

from .case import Case
from .filters import KeywordFilter, build_filter


class CaseManager:
    """
    High-level case operations.

    AGGREGATION: holds a CaseRepository that is injected from outside and can
    exist (and be reused/swapped) independently of the manager.
    ASSOCIATION: uses exporters / HistoryViewer to do work, without owning them.
    POLYMORPHISM: only talks to the CaseRepository / BaseExporter interfaces.
    """

    def __init__(self, repository):
        self._repo = repository

    @property
    def repository(self):
        return self._repo

    # ---- Create ----
    def create_new_case(self):
        case = Case(self._repo.next_case_id(), Case.OPEN, created=datetime.now().isoformat())
        self._repo.create(case)
        return case

    # ---- Read ----
    def get_case(self, case_id):
        return self._repo.read(case_id)

    def list_cases(self):
        return self._repo.list_all()

    def get_active_case(self):
        """Returns the newest case if it is still open, otherwise None."""
        cases = self._repo.list_all()
        if cases and cases[-1].is_open():
            return cases[-1]
        return None

    # ---- Update ----
    def add_log(self, case, user_input, response_text):
        case.add_log(user_input, response_text)
        return self._repo.update(case)

    def update_log(self, case, index, user_input=None, ai_response=None):
        case.update_log(index, user_input, ai_response)
        return self._repo.update(case)

    def delete_log(self, case, index):
        case.delete_log(index)
        return self._repo.update(case)

    def close_case(self, case):
        case.close()
        return self._repo.update(case)

    # ---- Delete ----
    def delete_case(self, case_id):
        return self._repo.delete(case_id)

    # ---- Querying across all cases ----
    def load_all_logs(self):
        """Every log from every case, as dicts tagged with their case_id."""
        records = []
        for case in self._repo.list_all():
            for log in case.logs:
                records.append({**log.to_dict(), "case_id": case.case_id})
        return records

    def filter_records(self, record_filter, records=None):
        """Apply any RecordFilter (keyword, date, case name, urgency, or AllOf)."""
        if records is None:
            records = self.load_all_logs()
        return record_filter.apply(records)

    def filter_records_by_keyword(self, keyword, records=None):
        return self.filter_records(KeywordFilter(keyword), records)

    def search(self, query):
        """Search with a text query, e.g. 'fever date:2026-11-01.. urgency:urgent'."""
        return self.filter_records(build_filter(query))

    # ---- Statistics (polymorphic: any StatsReport works) ----
    def report(self, stats_report, records=None):
        if records is None:
            records = self.load_all_logs()
        return stats_report.generate(records)

    # ---- Exporting (polymorphic: any BaseExporter works) ----
    def export(self, exporter, path=None):
        return exporter.export(self.load_all_logs(), path)

    # ---- Migration between backends ----
    def import_from(self, source_repo, overwrite=False):
        """Copy every case from another repository into this one."""
        copied = 0
        for case in source_repo.list_all():
            if self._repo.exists(case.case_id):
                if not overwrite:
                    continue
                self._repo.update(case)
            else:
                self._repo.create(case)
            copied += 1
        return copied
