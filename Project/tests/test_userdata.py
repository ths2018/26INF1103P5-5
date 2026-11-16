import os
import sqlite3
import tempfile
import unittest

from userdata import (InvalidUserDataError, PasswordHasher, UserExistsError,
                      UserService)
from userdata import user_service as us_mod


class FakeSync:
    """Stands in for MongoUserSync so tests need no MongoDB server."""
    def __init__(self, online=True):
        self.online, self.docs = online, {}

    def is_available(self, force=False):
        return self.online

    def email_taken(self, email, user_id=None):
        if not self.online:
            return None
        return any(d["email"] == email and d["_id"] != user_id for d in self.docs.values())

    def upsert(self, user):
        if not self.online:
            return False
        self.docs[user.user_id] = user.to_mongo_doc()
        return True


DETAILS = {"email": "Jane.Doe@Example.com", "full_name": "Jane O'Doe",
           "dob": "1990-04-23", "gender": "Female", "password": "s3cret!"}


class UserServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sync = FakeSync()
        self.svc = UserService(self.tmp.name, sync=self.sync)

    def test_creates_directory_and_db_file(self):
        user = self.svc.create_user(dict(DETAILS))
        folder = os.path.join(self.tmp.name, user.directory)
        self.assertTrue(os.path.isdir(folder))
        self.assertTrue(user.directory.startswith("jane-o-doe_"))
        db = os.path.join(folder, "user.db")
        self.assertTrue(os.path.isfile(db))
        row = sqlite3.connect(db).execute("SELECT email, full_name FROM profile").fetchone()
        self.assertEqual(row, ("jane.doe@example.com", "Jane O'Doe"))

    def test_syncs_to_mongo_without_plaintext_password(self):
        user = self.svc.create_user(dict(DETAILS))
        self.assertEqual(user.sync_status, "synced")
        doc = self.sync.docs[user.user_id]
        self.assertEqual(doc["email"], "jane.doe@example.com")
        self.assertNotIn("password", doc)
        self.assertNotIn("s3cret!", str(doc))

    def test_offline_then_sync_pending(self):
        self.sync.online = False
        user = self.svc.create_user(dict(DETAILS))
        self.assertEqual(user.sync_status, "pending")
        self.assertEqual(self.svc.get_user(DETAILS["email"]).sync_status, "pending")
        self.assertEqual(self.sync.docs, {})
        self.sync.online = True
        self.assertEqual(self.svc.sync_pending(), 1)
        self.assertIn(user.user_id, self.sync.docs)
        self.assertEqual(self.svc.get_user(DETAILS["email"]).sync_status, "synced")
        self.assertEqual(self.svc.sync_pending(), 0)

    def test_duplicate_email_rejected_locally_and_in_mongo(self):
        self.svc.create_user(dict(DETAILS))
        with self.assertRaises(UserExistsError):
            self.svc.create_user(dict(DETAILS, email="JANE.DOE@example.com"))
        # account that exists only in Mongo (created on another machine)
        self.sync.docs["x"] = {"_id": "x", "email": "other@example.com"}
        with self.assertRaises(UserExistsError):
            self.svc.create_user(dict(DETAILS, email="other@example.com"))
        self.assertEqual(len([d for d in os.listdir(self.tmp.name)
                              if os.path.isdir(os.path.join(self.tmp.name, d))]), 1)

    def test_authenticate(self):
        self.svc.create_user(dict(DETAILS))
        self.assertIsNotNone(self.svc.authenticate("jane.doe@example.com", "s3cret!"))
        self.assertIsNone(self.svc.authenticate("jane.doe@example.com", "wrong"))
        self.assertIsNone(self.svc.authenticate("nobody@example.com", "s3cret!"))

    def test_invalid_input(self):
        for bad in (dict(DETAILS, email="nope"), dict(DETAILS, dob="23/04/1990"),
                    dict(DETAILS, password="")):
            with self.assertRaises(InvalidUserDataError):
                self.svc.create_user(bad)

    def test_rollback_when_registry_fails(self):
        original = us_mod.UserRegistry.add
        def boom(self_, user): raise RuntimeError("disk full")
        us_mod.UserRegistry.add = boom
        try:
            with self.assertRaises(RuntimeError):
                self.svc.create_user(dict(DETAILS))
        finally:
            us_mod.UserRegistry.add = original
        folders = [d for d in os.listdir(self.tmp.name)
                   if os.path.isdir(os.path.join(self.tmp.name, d))]
        self.assertEqual(folders, [])

    def test_per_user_case_repository(self):
        user = self.svc.create_user(dict(DETAILS))
        repo = self.svc.case_repository(user)
        case = repo.next_case_id()
        self.assertEqual(case, "case_1")
        tables = {r[0] for r in sqlite3.connect(self.svc.db_path(user)).execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"profile", "cases", "logs"} <= tables)

    def test_password_hash(self):
        h = PasswordHasher.hash("abc")
        self.assertNotIn("abc", h)
        self.assertTrue(PasswordHasher.verify("abc", h))
        self.assertFalse(PasswordHasher.verify("abd", h))
        self.assertNotEqual(h, PasswordHasher.hash("abc"))   # random salt


if __name__ == "__main__":
    unittest.main()
