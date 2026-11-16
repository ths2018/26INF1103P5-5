from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Abstract base class (and contract) for every password hashing algorithm.

    Shared behaviour lives here: input checking in hash_password() and
    verify_password(). Subclasses only supply the algorithm-specific parts
    (_hash, _verify, needs_rehash), so client code can use any PasswordHasher
    without knowing which algorithm is behind it.
    """

    def hash_password(self, password):
        """Return the string to store in the database for this password."""
        self._check_password(password)
        return self._hash(password)

    def verify_password(self, password, stored_hash):
        """True if `password` matches `stored_hash`. Never raises on bad data."""
        if not isinstance(password, str) or not isinstance(stored_hash, str):
            return False
        return self._verify(password, stored_hash)

    @abstractmethod
    def needs_rehash(self, stored_hash):
        """True if the stored hash is weaker than the current settings."""

    @abstractmethod
    def _hash(self, password):
        """Algorithm-specific hashing (password is already validated)."""

    @abstractmethod
    def _verify(self, password, stored_hash):
        """Algorithm-specific check. Must return False (not raise) on bad hashes."""

    @staticmethod
    def _check_password(password):
        if not isinstance(password, str) or not password:
            raise ValueError("Password must be a non-empty string.")
