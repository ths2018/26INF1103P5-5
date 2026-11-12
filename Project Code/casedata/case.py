"""Case: a case and the LogEntry objects it owns (composition)."""


from datetime import datetime

from .log_entry import LogEntry


class Case:
    """
    A case and the log entries it contains.

    COMPOSITION: the Case creates its LogEntry objects (add_log) and manages
    their whole lifecycle; log entries never exist outside a case.
    """

    OPEN = "open"
    CLOSED = "closed"

    def __init__(self, case_id, status=OPEN, created=None, closed=None, logs=None):
        self._case_id = case_id
        self._status = status
        self._created = created
        self._closed = closed
        self._logs = [LogEntry.from_dict(l) if isinstance(l, dict) else l
                      for l in (logs or [])]

    # --- read-only state ---
    @property
    def case_id(self):
        return self._case_id

    @property
    def status(self):
        return self._status

    @property
    def created(self):
        return self._created

    @property
    def closed(self):
        return self._closed

    @property
    def logs(self):
        """A copy, so outside code cannot bypass add/update/delete_log."""
        return list(self._logs)

    def is_open(self):
        return self._status == self.OPEN

    # --- behaviour ---
    def close(self):
        self._status = self.CLOSED
        self._closed = datetime.now().isoformat()

    def add_log(self, user_input, ai_response):
        entry = LogEntry(user_input, ai_response)
        self._logs.append(entry)
        return entry

    def update_log(self, index, user_input=None, ai_response=None):
        entry = self._logs[index]  # IndexError if invalid
        if user_input is not None:
            entry.user_input = user_input
        if ai_response is not None:
            entry.ai_response = ai_response
        return entry

    def delete_log(self, index):
        return self._logs.pop(index)  # IndexError if invalid

    # --- serialisation ---
    def to_dict(self):
        data = {
            "case_id": self._case_id,
            "status": self._status,
            "created": self._created,
            "logs": [l.to_dict() for l in self._logs],
        }
        if self._closed:
            data["closed"] = self._closed
        return data

    @classmethod
    def from_dict(cls, data, case_id=None):
        # legacy format: a bare list of log records == a closed case
        if isinstance(data, list):
            return cls(case_id, cls.CLOSED, logs=data)
        return cls(
            case_id or data.get("case_id"),
            data.get("status", cls.CLOSED),
            data.get("created"),
            data.get("closed"),
            data.get("logs", []),
        )

    # Dict-style access so older code like case["logs"] keeps working
    def __getitem__(self, key):
        if key == "logs":
            return [l.to_dict() for l in self._logs]  # old format: list of dicts
        if key in ("case_id", "status", "created", "closed"):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key, default=None):
        """dict-style get(); missing/empty optional fields return the default."""
        try:
            value = self[key]
        except KeyError:
            return default
        return default if value is None else value

    def __repr__(self):
        return f"Case({self._case_id!r}, {self._status}, {len(self._logs)} logs)"
