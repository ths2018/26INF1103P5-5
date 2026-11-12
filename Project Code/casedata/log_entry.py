"""LogEntry: one question/answer exchange owned by a Case."""


from datetime import datetime


class LogEntry:
    """One question/answer exchange. Immutable-ish value object owned by a Case."""

    def __init__(self, user_input, ai_response, timestamp=None):
        self._timestamp = timestamp or datetime.now().isoformat()
        self._user_input = user_input
        self._ai_response = ai_response

    # Read-only timestamp, editable content (encapsulation via properties)
    @property
    def timestamp(self):
        return self._timestamp

    @property
    def user_input(self):
        return self._user_input

    @user_input.setter
    def user_input(self, value):
        self._user_input = value

    @property
    def ai_response(self):
        return self._ai_response

    @ai_response.setter
    def ai_response(self, value):
        self._ai_response = value

    # Dict-style access so older code like log["user_input"] keeps working
    def __getitem__(self, key):
        if key in ("timestamp", "user_input", "ai_response"):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self):
        return {
            "timestamp": self._timestamp,
            "user_input": self._user_input,
            "ai_response": self._ai_response,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data.get("user_input", ""),
            data.get("ai_response", ""),
            data.get("timestamp"),
        )
