"""Record filters (interface + implementations + composite) and the query parser."""


import shlex
from abc import ABC, abstractmethod
from datetime import date, datetime

from .urgency import UrgencyClassifier


class RecordFilter(ABC):
    """INTERFACE: anything that can decide whether one record matches."""

    @abstractmethod
    def matches(self, record):
        """Return True if the record passes this filter."""

    def apply(self, records):
        return [r for r in records if self.matches(r)]

    def __and__(self, other):
        return AllOf(self, other)


class KeywordFilter(RecordFilter):
    """Keyword in the user input or the AI response (case-insensitive)."""

    def __init__(self, keyword):
        self._keyword = keyword.lower()

    def matches(self, record):
        return (self._keyword in record.get("user_input", "").lower()
                or self._keyword in record.get("ai_response", "").lower())


class DateRangeFilter(RecordFilter):
    """Records whose timestamp falls between start and end (inclusive, either optional)."""

    def __init__(self, start=None, end=None):
        self._start = self._to_date(start)
        self._end = self._to_date(end)
        if self._start and self._end and self._start > self._end:
            raise ValueError("Start date is after end date.")

    @staticmethod
    def _to_date(value):
        if value is None or isinstance(value, date):
            return value
        if str(value).lower() == "today":
            return date.today()
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD.")

    def matches(self, record):
        try:
            day = datetime.fromisoformat(record.get("timestamp", "")).date()
        except ValueError:
            return False
        return ((self._start is None or day >= self._start)
                and (self._end is None or day <= self._end))


class CaseNameFilter(RecordFilter):
    """
    Match by case name. 'case_3' or '3' matches that case exactly;
    anything else is treated as a partial, case-insensitive match.
    """

    def __init__(self, name):
        name = name.strip().lower()
        self._exact = f"case_{name}" if name.isdigit() else None
        self._name = name

    def matches(self, record):
        case_id = str(record.get("case_id", "")).lower()
        if self._exact:
            return case_id == self._exact
        return self._name in case_id


class UrgencyFilter(RecordFilter):
    """Records whose AI response has the given urgency classification."""

    def __init__(self, label):
        label = label.strip().lower()
        if label not in UrgencyClassifier.LABELS + [UrgencyClassifier.UNCLASSIFIED]:
            raise ValueError(
                f"Unknown urgency '{label}'. Choose from: {', '.join(UrgencyClassifier.LABELS)}")
        self._label = label

    def matches(self, record):
        return UrgencyClassifier.classify(record.get("ai_response", "")) == self._label


class AllOf(RecordFilter):
    """COMPOSITE: a record must pass every child filter (AND)."""

    def __init__(self, *filters):
        self._filters = list(filters)

    def matches(self, record):
        return all(f.matches(record) for f in self._filters)


def build_filter(query):
    """
    Builds a filter from a search string, e.g.
        fever date:2026-11-01..2026-11-04 case:3 urgency:urgent
    Bare words are keywords. Keys: keyword, date, case (or name), urgency.
    Date forms: 2026-11-04 | 2026-11-01..2026-11-04 | 2026-11-01.. | ..2026-11-04 | today
    """
    filters = []
    try:
        tokens = shlex.split(query or "")
    except ValueError:  # e.g. an unmatched apostrophe as in "patient's"
        tokens = (query or "").split()
    for token in tokens:
        key, sep, value = token.partition(":")
        key = key.lower()
        if not sep or key not in ("keyword", "date", "case", "name", "urgency"):
            filters.append(KeywordFilter(token))
            continue
        if not value:
            raise ValueError(f"Missing value after '{key}:'")
        if key == "keyword":
            filters.append(KeywordFilter(value))
        elif key in ("case", "name"):
            filters.append(CaseNameFilter(value))
        elif key == "urgency":
            filters.append(UrgencyFilter(value))
        else:  # date
            if ".." in value:
                start, _, end = value.partition("..")
                filters.append(DateRangeFilter(start or None, end or None))
            else:
                filters.append(DateRangeFilter(value, value))
    return AllOf(*filters)
