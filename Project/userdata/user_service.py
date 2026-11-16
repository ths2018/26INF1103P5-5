"""UserService: create accounts (folder + db file + MongoDB sync) and log in."""

import os
import shutil
import uuid
from datetime import datetime

from .config import SYNC_PENDING, SYNC_SYNCED, USERS_DIR
from .errors import UserExistsError
from .mongo_sync import MongoUserSync
from .passwords import PasswordHasher
from .profile_store import ProfileStore
from .registry import UserRegistry
from .user import User, slugify


class UserService:
    """
    create_user() does, in order:
      1. validate the signup inputs and hash the password
      2. refuse duplicate emails (local registry, and MongoDB when reachable)
      3. create users/<name>_<id>/ and its user.db file
      4. record the account in users/registry.db
      5. push the account to MongoDB (or mark it 'pending' if offline)
    If steps 3-4 fail, the folder is removed again so nothing is left half-made.
    """

    def __init__(self, users_dir=USERS_DIR, sync=None, registry=None):
        self._users_dir = users_dir
        os.makedirs(users_dir, exist_ok=True)
        self._registry = registry or UserRegistry(os.path.join(users_dir, "registry.db"))
        self._sync = sync if sync is not None else MongoUserSync()

    @property
    def sync(self):
        return self._sync

    # ---- Create ----
    def create_user(self, details):
        clean = User.validate_details(details)
        email = clean["email"]

        if self.email_exists(email):
            raise UserExistsError(f"{email} is already registered.")
        if self._sync.email_taken(email) is True:
            raise UserExistsError(f"{email} is already registered (MongoDB).")

        user_id = uuid.uuid4().hex
        user = User(
            user_id=user_id,
            email=email,
            full_name=clean["full_name"],
            dob=clean["dob"],
            gender=clean["gender"],
            password_hash=PasswordHasher.hash(clean["password"]),
            created=datetime.now().isoformat(),
            directory=f"{slugify(clean['full_name'])}_{user_id[:8]}",
        )

        user_dir = self._user_dir(user)
        try:
            ProfileStore(user_dir).create(user)       # folder + user.db
            self._registry.add(user)                  # local index
        except Exception:
            shutil.rmtree(user_dir, ignore_errors=True)
            raise

        try:
            self._push(user)
        except UserExistsError:                       # lost a race on the email
            shutil.rmtree(user_dir, ignore_errors=True)
            self._registry.remove(user.user_id)
            raise
        return user

    # ---- Read ----
    def email_exists(self, email):
        return self._registry.find_by_email(email) is not None

    def get_user(self, email):
        row = self._registry.find_by_email(email)
        if row is None:
            return None
        store = ProfileStore(os.path.join(self._users_dir, row["directory"]))
        return store.load(row["sync_status"], row["synced_at"])

    def authenticate(self, email, password):
        """Returns the User if the credentials are right, otherwise None."""
        user = self.get_user(email)
        if user and PasswordHasher.verify(password, user.password_hash):
            return user
        return None

    # ---- Per-user paths / data ----
    def _user_dir(self, user):
        return os.path.join(self._users_dir, user.directory)

    def db_path(self, user):
        return ProfileStore(self._user_dir(user)).db_path

    def case_repository(self, user):
        """A SqliteCaseRepository that stores this user's cases in their own user.db."""
        from casedata import SqliteCaseRepository   # lazy: avoids import cycles
        return SqliteCaseRepository(db_path=self.db_path(user))

    # ---- MongoDB sync ----
    def _push(self, user):
        if self._sync.upsert(user):
            now = datetime.now().isoformat()
            self._registry.set_sync(user.user_id, SYNC_SYNCED, now)
            user.sync_status, user.synced_at = SYNC_SYNCED, now
            return True
        self._registry.set_sync(user.user_id, SYNC_PENDING)
        user.sync_status = SYNC_PENDING
        return False

    def sync_pending(self):
        """Retry accounts that couldn't reach MongoDB. Returns how many were synced."""
        if not self._sync.is_available(force=True):
            return 0
        synced = 0
        for row in self._registry.pending():
            user = ProfileStore(os.path.join(self._users_dir, row["directory"])).load()
            if user and self._push(user):
                synced += 1
        return synced
