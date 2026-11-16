"""Paths and constants for user accounts."""

import os

# Project root = folder that contains the userdata package
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every user gets their own sub-directory in here: users/<name>_<id>/
USERS_DIR = os.path.join(BASE_DIR, "users")

# Small local index (email -> user directory) so we can find a user
# without opening every user's folder and without needing MongoDB.
REGISTRY_FILE = os.path.join(USERS_DIR, "registry.db")

# Name of the database file created inside each user's directory.
USER_DB_NAME = "user.db"

MONGO_DB_NAME = "case_assessments"
MONGO_USERS_COLLECTION = "users"

SYNC_SYNCED = "synced"     # local copy and MongoDB match
SYNC_PENDING = "pending"   # MongoDB was unreachable; retry with sync_pending()
