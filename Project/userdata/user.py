"""User: the account data object."""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from .errors import InvalidUserDataError
from .config import SYNC_PENDING

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def slugify(text, max_length=30):
    """'Mary-Anne O'Neil' -> 'mary-anne-o-neil' (safe for folder names)."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:max_length].strip("-") or "user"


@dataclass
class User:
    user_id: str
    email: str
    full_name: str
    dob: str            # ISO date, e.g. 1990-04-23
    gender: str
    password_hash: str
    created: str
    directory: str      # folder NAME inside USERS_DIR (relative, so it is portable)
    sync_status: str = SYNC_PENDING
    synced_at: str = None

    @staticmethod
    def validate_details(details):
        """Check the dict produced by AuthInputManager.get_signup_details()."""
        required = ("email", "full_name", "dob", "gender", "password")
        missing = [k for k in required if not str(details.get(k, "")).strip()]
        if missing:
            raise InvalidUserDataError(f"Missing signup field(s): {', '.join(missing)}")

        email = details["email"].strip().lower()
        if len(email) > 254 or not _EMAIL_RE.fullmatch(email):
            raise InvalidUserDataError("Invalid email address.")

        dob = details["dob"]
        try:
            dob = dob.isoformat() if isinstance(dob, date) else date.fromisoformat(dob).isoformat()
        except ValueError as exc:
            raise InvalidUserDataError("DOB must be an ISO date (YYYY-MM-DD).") from exc

        return {
            "email": email,
            "full_name": details["full_name"].strip(),
            "dob": dob,
            "gender": details["gender"].strip(),
            "password": details["password"],
        }

    def public_dict(self):
        """Profile without the password hash (safe to show/pass around)."""
        return {
            "user_id": self.user_id, "email": self.email,
            "full_name": self.full_name, "dob": self.dob, "gender": self.gender,
            "created": self.created, "directory": self.directory,
        }

    def to_mongo_doc(self):
        """Document stored in MongoDB. Never contains the plaintext password."""
        doc = self.public_dict()
        doc["_id"] = doc.pop("user_id")
        doc["password_hash"] = self.password_hash
        return doc
