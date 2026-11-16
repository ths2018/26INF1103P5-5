import re


class AIResponse:
    """Value object that knows how to read the sections of an AI reply."""

    SECTION_LABELS = (
        "Urgency classification:",
        "Certainty:",
        "Follow-Up Questions:",
        "Next-Step Guidance:",
        "AI Response:",
    )
    _NO_FOLLOW_UP = {"none", "none.", "not applicable"}
    _URGENCY_PATTERN = re.compile(
        r"Urgency classification:\s*(emergency|urgent|non-urgent|insufficient information)",
        re.IGNORECASE,
    )
    _CERTAINTY_PATTERN = re.compile(r"Certainty:\s*(\d+(?:\.\d+)?)\s*%?", re.IGNORECASE)

    def __init__(self, text):
        self.__text = text  # private: read through the `text` property

    @classmethod
    def emergency(cls, guidance):
        """Build a canned emergency reply without calling the AI."""
        return cls(
            "Urgency classification: emergency\n"
            "Certainty: 100%\n\n"
            "Follow-Up Questions:\n"
            "None\n\n"
            "Next-Step Guidance:\n" + guidance
        )

    @property
    def text(self):
        return self.__text

    def section(self, label, stop_labels=None):
        """Content of one labelled section, or None. Stops at the next known label."""
        if not isinstance(self.__text, str):
            return None
        if stop_labels is None:
            stop_labels = self.SECTION_LABELS

        captured = []
        inside = False
        for line in self.__text.splitlines():
            stripped = line.strip()
            if stripped.startswith(label):
                inside = True
                continue  # skip the label line itself
            if not inside:
                continue
            if any(stripped.startswith(lbl) for lbl in stop_labels if lbl != label):
                break
            captured.append(line.rstrip())

        while captured and not captured[0].strip():
            captured.pop(0)
        while captured and not captured[-1].strip():
            captured.pop()

        return "\n".join(captured) if captured else None

    @property
    def urgency(self):
        if not isinstance(self.__text, str):
            return "insufficient information"
        match = self._URGENCY_PATTERN.search(self.__text)
        return match.group(1).lower() if match else "insufficient information"

    @property
    def certainty(self):
        if not isinstance(self.__text, str):
            return 0.0
        match = self._CERTAINTY_PATTERN.search(self.__text)
        if not match:
            return 0.0
        value = float(match.group(1))
        if "%" in match.group(0) or value > 1:
            value /= 100
        return max(0.0, min(value, 1.0))

    @property
    def follow_up_question(self):
        section = self.section("Follow-Up Questions:")
        if not section:
            return None
        cleaned = section.strip()
        if cleaned.lower() in self._NO_FOLLOW_UP:
            return None
        return cleaned

    @property
    def has_follow_up(self):
        return self.follow_up_question is not None

    @property
    def is_emergency(self):
        """True only if the AI said 'emergency' ('urgent' does NOT count)."""
        return self.urgency == "emergency"
