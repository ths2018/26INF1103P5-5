"""MongoUserSync: pushes user accounts to MongoDB (collection 'users')."""

import os
import re
import time

try:  # CASE_MONGO_URI lives in the same .env as the other settings
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .config import MONGO_DB_NAME, MONGO_USERS_COLLECTION
from .errors import UserExistsError


class MongoUserSync:
    """
    Best-effort sync. If MongoDB is unreachable every method degrades quietly
    (returns None/False) so local signup still works; the account is marked
    'pending' and pushed later by UserService.sync_pending().
    """

    RETRY_AFTER_SECONDS = 30   # don't wait for a 3s timeout on every single call

    def __init__(self, uri=None, db_name=MONGO_DB_NAME, collection=MONGO_USERS_COLLECTION):
        self._uri = uri or os.environ.get("CASE_MONGO_URI", "mongodb://localhost:27017")
        self._db_name = db_name
        self._collection_name = collection
        self._col = None
        self._failed_at = None
        self.last_error = None

    @staticmethod
    def _hide_credentials(text):
        return re.sub(r"//[^@/\s]*@", "//***@", str(text))

    def _collection(self, force=False):
        if self._col is not None:
            return self._col
        if (not force and self._failed_at
                and time.monotonic() - self._failed_at < self.RETRY_AFTER_SECONDS):
            return None
        try:
            from pymongo import ASCENDING, MongoClient
            client = MongoClient(self._uri, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            col = client[self._db_name][self._collection_name]
            col.create_index([("email", ASCENDING)], unique=True)
            self._col, self._failed_at, self.last_error = col, None, None
        except Exception as exc:  # ImportError, PyMongoError, bad URI...
            self._failed_at = time.monotonic()
            self.last_error = f"{type(exc).__name__}: {self._hide_credentials(exc)}"
            return None
        return self._col

    def is_available(self, force=False):
        return self._collection(force) is not None

    def email_taken(self, email, user_id=None):
        """True/False, or None if MongoDB can't be reached."""
        col = self._collection()
        if col is None:
            return None
        try:
            doc = col.find_one({"email": email}, {"_id": 1})
        except Exception as exc:
            self._mark_failed(exc)
            return None
        return bool(doc) and doc["_id"] != user_id

    def upsert(self, user):
        """Insert/update the account. True on success, False if unreachable."""
        col = self._collection()
        if col is None:
            return False
        try:
            from pymongo.errors import DuplicateKeyError
        except ImportError:
            return False
        doc = user.to_mongo_doc()
        try:
            col.replace_one({"_id": doc["_id"]}, doc, upsert=True)
            return True
        except DuplicateKeyError as exc:   # same email, different user_id
            raise UserExistsError(f"{user.email} is already registered in MongoDB.") from exc
        except Exception as exc:
            self._mark_failed(exc)
            return False

    def _mark_failed(self, exc):
        self._col = None
        self._failed_at = time.monotonic()
        self.last_error = f"{type(exc).__name__}: {self._hide_credentials(exc)}"
