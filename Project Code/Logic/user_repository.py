from abc import ABC, abstractmethod


class UserRepository(ABC):
    """Interface (contract) for wherever user accounts are stored.

    AuthService only talks to this type, so any database can be plugged in by
    writing one class that implements these four methods. Only password HASHES
    are ever passed in or out, never plain passwords.
    """

    @abstractmethod
    def add_user(self, username, password_hash, profile=None):
        """Create an account. Return False if the username already exists."""

    @abstractmethod
    def get_password_hash(self, username):
        """Return the stored hash, or None if there is no such user."""

    @abstractmethod
    def get_profile(self, username):
        """Return the user's profile dict ({} if there is no such user)."""

    @abstractmethod
    def update_password_hash(self, username, password_hash):
        """Replace the stored hash (used to upgrade old hashes after sign-in)."""
