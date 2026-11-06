"""MongoCaseRepository: MongoDB backend (needs pymongo and a running server)."""


import os
import re
import re

from ..case import Case
from ..config import case_number
from .base import CaseRepository


class MongoCaseRepository(CaseRepository):
    """MongoDB backend. One document per case, logs embedded as an array."""

    def __init__(self, uri=None, db_name="case_assessments", collection="cases"):
        try:
            from pymongo import MongoClient
            from pymongo.errors import PyMongoError
        except ImportError as e:
            raise RuntimeError(
                "MongoDB backend needs pymongo: python -m pip install pymongo") from e

        uri = uri or "mongodb+srv://kwokjun_db_user:SnKxHtpwKC2sCuEB@healthcare.mr4w2yd.mongodb.net/healthcare?retryWrites=true&w=majority"
        client = None
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")  # forces a real connection attempt now
        except PyMongoError as e:
            if client is not None:
                client.close()
            # main.py shows this as: "[Fatal Error] Could not initialise the application: ..."
            raise RuntimeError(
                f"Cannot connect to MongoDB at {self._hide_credentials(uri)}. "
                "Check that the server is running (for Atlas: your IP allowlist, "
                f"username/password and connection string). [{type(e).__name__}]"
            ) from e

        self._client = client
        self._col = client[db_name][collection]

    @staticmethod
    def _hide_credentials(uri):
        """mongodb+srv://user:pass@host -> mongodb+srv://***@host (keeps passwords out of messages)."""
        return re.sub(r"//[^@/]*@", "//***@", uri)

    @staticmethod
    def _to_doc(case):
        doc = case.to_dict()
        doc["_id"] = doc.pop("case_id")
        doc["case_number"] = case_number(case.case_id)
        return doc

    @staticmethod
    def _from_doc(doc):
        return Case(doc["_id"], doc.get("status", Case.CLOSED), doc.get("created"),
                    doc.get("closed"), doc.get("logs", []))

    def create(self, case):
        from pymongo.errors import DuplicateKeyError
        try:
            self._col.insert_one(self._to_doc(case))
            return True
        except DuplicateKeyError:
            raise ValueError(f"{case.case_id} already exists")

    def read(self, case_id):
        doc = self._col.find_one({"_id": case_id})
        return self._from_doc(doc) if doc else None

    def list_all(self):
        return [self._from_doc(d) for d in self._col.find().sort("case_number", 1)]

    def update(self, case):
        doc = self._to_doc(case)
        result = self._col.replace_one({"_id": doc["_id"]}, doc)
        if result.matched_count == 0:
            raise KeyError(case.case_id)
        return True

    def delete(self, case_id):
        return self._col.delete_one({"_id": case_id}).deleted_count > 0
        
