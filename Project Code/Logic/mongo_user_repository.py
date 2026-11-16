import re
import uuid
from datetime import datetime

from pymongo.errors import DuplicateKeyError

from Logic.user_repository import UserRepository


class MongoUserRepository(UserRepository):
    """Reads and writes user accounts in the team's MongoDB 'users' collection.

    A document looks like this (fields as already stored in the database):
        {"_id": "3cdecceb758e494fb1638242428727f2", "email": "ann@example.com", "full_name": "Ann", "dob": "2000-01-01",
         "gender": "Female", "created": "2026-11-16T16:54:38.622798",
         "directory": "ann_3cdecceb", "password_hash": "pbkdf2_sha256$600000$<salt>$<hash>"}

    The login 'username' is the email. Everything except _id and password_hash is
    returned as the user's profile. The collection is passed in, so the same
    MongoDB connection can be shared with the rest of the project.
    """

    _PROFILE_EXCLUDED = ("_id", "password_hash")
    _RESERVED = ("_id", "user_id", "email", "created", "directory", "password_hash")

    def __init__(self, collection):
        self._users = collection

    def add_user(self, username, password_hash, profile=None):
        """Create an account. Returns False if the email is already registered."""
        if self._users.find_one({"email": username}, {"_id": 1}):
            return False
        details = {k: v for k, v in (profile or {}).items() if k not in self._RESERVED}
        user_id = uuid.uuid4().hex  # the _id is a 32-character string, like the existing accounts
        document = {
            "_id": user_id,
            "email": username,
            **details,
            "created": datetime.now().isoformat(),
            "directory": self._directory_name(details.get("full_name"), user_id),
            "password_hash": password_hash,
        }
        try:
            self._users.insert_one(document)
            return True
        except DuplicateKeyError:  # someone else registered it a moment ago
            return False

    def get_password_hash(self, username):
        document = self._users.find_one({"email": username}, {"password_hash": 1})
        return document.get("password_hash") if document else None

    def get_profile(self, username):
        document = self._users.find_one({"email": username})
        if not document:
            return {}
        profile = {k: v for k, v in document.items() if k not in self._PROFILE_EXCLUDED}
        profile["user_id"] = document["_id"]
        return profile

    def update_password_hash(self, username, password_hash):
        self._users.update_one({"email": username}, {"$set": {"password_hash": password_hash}})

    @staticmethod
    def _directory_name(full_name, user_id):
        """'<first name>_<first 8 characters of the id>', like the existing accounts."""
        first = re.sub(r"[^a-z0-9]+", "", str(full_name or "user").split()[0].lower()) or "user"
        return f"{first}_{user_id[:8]}"
