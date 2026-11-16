"""UrgencyClassifier: reads the urgency label from an AI response."""


import re


class UrgencyClassifier:
    """Reads the 'Urgency classification: <label>' prefix of an AI response."""

    LABELS = ["emergency", "urgent", "non-urgent", "insufficient_information"]
    UNCLASSIFIED = "unclassified"
    _PATTERN = re.compile(r"urgency classification:\s*([a-z_\-]+)", re.IGNORECASE)

    @classmethod
    def classify(cls, ai_response):
        match = cls._PATTERN.match((ai_response or "").lstrip())
        if match and match.group(1).lower() in cls.LABELS:
            return match.group(1).lower()
        return cls.UNCLASSIFIED
