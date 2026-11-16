from abc import ABC, abstractmethod


class ResponseValidator(ABC):
    """Abstract base class for one cross-check of an AI response against the
    medical guideline data.

    Every validator takes the same inputs and returns a list of "findings", so the
    engine can run any mix of validators without knowing what each one checks.
    """

    def __init__(self, guidelines):
        # AGGREGATION: the repository is created elsewhere and shared
        self._guidelines = guidelines

    @abstractmethod
    def validate(self, response, patient_text):
        """Return a list of finding dicts (see _finding). Never raises on odd input.

        response     - the AIResponse being checked
        patient_text - everything the patient typed (symptoms and follow-up answers)
        """

    def _finding(self, kind, message, record=None, min_urgency=None):
        """kind: 'red_flag' | 'consistent' | 'no_match' | 'note'."""
        return {
            "validator": type(self).__name__,
            "type": kind,
            "message": message,
            "source": self._guidelines.source_label(record) if record else None,
            "source_details": (
                self._guidelines.source_details(record) if record else None
            ),
            "min_urgency": min_urgency,
            "needs_review": bool(record and self._guidelines.needs_review(record)),
        }
