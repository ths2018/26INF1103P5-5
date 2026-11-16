import uuid

from Logic.user_repository import UserRepository


class InMemoryUserRepository(UserRepository):
    """Keeps accounts in memory only (lost when the program closes).

    Used for testing, and as a stand-in until the real user database exists.
    """

    def __init__(self):
        self.__users = {}  # private: username -> {"password_hash", "profile"}

    def add_user(self, username, password_hash, profile=None):
        if username in self.__users:
            return False
        self.__users[username] = {
            "password_hash": password_hash,
            "profile": {**dict(profile or {}), "user_id": uuid.uuid4().hex},
        }
        return True

    def get_password_hash(self, username):
        user = self.__users.get(username)
        return user["password_hash"] if user else None

    def get_profile(self, username):
        user = self.__users.get(username)
        return dict(user["profile"]) if user else {}

    def update_password_hash(self, username, password_hash):
        if username in self.__users:
            self.__users[username]["password_hash"] = password_hash
