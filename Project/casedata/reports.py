"""Statistics reports (StatsReport interface + implementations)."""


from abc import ABC, abstractmethod
from collections import Counter

from .config import case_number
from .urgency import UrgencyClassifier


class StatsReport(ABC):
    """INTERFACE: turns a list of records into printable text."""

    @abstractmethod
    def generate(self, records):
        """Return the report as a string."""

    @staticmethod
    def _labels_in_order(counts):
        order = UrgencyClassifier.LABELS + [UrgencyClassifier.UNCLASSIFIED]
        return [l for l in order if counts.get(l)]


class UrgencySummaryReport(StatsReport):
    """Counts and percentages per urgency class across the given records."""

    def generate(self, records):
        if not records:
            return "No records match, so there are no statistics to show."
        counts = Counter(UrgencyClassifier.classify(r.get("ai_response", "")) for r in records)
        per_case = Counter(r.get("case_id", "") for r in records)
        total = len(records)

        lines = [f"Urgency summary ({total} assessment(s) across {len(per_case)} case(s))"]
        for label in self._labels_in_order(counts):
            pct = round(100 * counts[label] / total)
            lines.append(f"  {label:<26}{counts[label]:>4}   ({pct}%)")
        busiest, n = per_case.most_common(1)[0]
        lines.append(f"Busiest case: {busiest} ({n} assessment(s))")
        return "\n".join(lines)


class PerCaseReport(StatsReport):
    """One line per case with its urgency breakdown."""

    def generate(self, records):
        if not records:
            return "No records match, so there are no statistics to show."
        by_case = {}
        for r in records:
            by_case.setdefault(r.get("case_id", ""), []).append(r)

        lines = ["Per-case breakdown"]
        for case_id in sorted(by_case, key=case_number):
            counts = Counter(UrgencyClassifier.classify(r.get("ai_response", ""))
                             for r in by_case[case_id])
            detail = ", ".join(f"{l}: {counts[l]}" for l in self._labels_in_order(counts))
            lines.append(f"  {case_id}: {len(by_case[case_id])} assessment(s)  [{detail}]")
        return "\n".join(lines)
