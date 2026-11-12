import re
from abc import ABC, abstractmethod


class TextDetector(ABC):
    """Abstract base class: shared template for 'does this text contain X?'.

    detect() is the shared behaviour. Each subclass supplies WHAT to look for
    (the abstract `phrases` property) and may change HOW a phrase is matched
    by overriding _matches().
    """

    def detect(self, text):
        if not isinstance(text, str):
            return False
        prepared = self._prepare(text)
        if not prepared:
            return False
        return any(self._matches(prepared, phrase) for phrase in self.phrases)

    @property
    @abstractmethod
    def phrases(self):
        """The keywords/phrases this detector looks for."""

    def _prepare(self, text):
        """Hook: normalise the text before matching (default: lower-case + strip)."""
        return text.lower().strip()

    def _matches(self, text, phrase):
        """Default: match a whole word/phrase (so 'arm' does not match 'alarm')."""
        pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
        return re.search(pattern, text, re.IGNORECASE) is not None
