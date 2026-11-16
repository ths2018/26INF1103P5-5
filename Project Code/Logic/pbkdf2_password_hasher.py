import base64
import hashlib
import hmac
import os

from Logic.password_hasher import PasswordHasher


class Pbkdf2PasswordHasher(PasswordHasher):
    """PBKDF2-HMAC-SHA256 from the standard library (no extra install).

    Stored format: pbkdf2_sha256$<iterations>$<salt_base64>$<hash_base64>
    """

    _ALGORITHM = "pbkdf2_sha256"
    _DEFAULT_ITERATIONS = 600_000
    _SALT_BYTES = 16

    def __init__(self, iterations=_DEFAULT_ITERATIONS):
        self._iterations = iterations

    def needs_rehash(self, stored_hash):
        try:
            _, iterations, _, _ = stored_hash.split("$")
            return int(iterations) < self._iterations
        except (ValueError, AttributeError):
            return True

    def _hash(self, password):
        salt = os.urandom(self._SALT_BYTES)
        digest = self._derive(password, salt, self._iterations)
        return "$".join(
            [self._ALGORITHM, str(self._iterations), self._encode(salt), self._encode(digest)]
        )

    def _verify(self, password, stored_hash):
        try:
            algorithm, iterations, salt_b64, hash_b64 = stored_hash.split("$")
            if algorithm != self._ALGORITHM:
                return False
            iterations = int(iterations)
            salt = self._decode(salt_b64)
            expected = self._decode(hash_b64)
        except (ValueError, TypeError):
            return False
        actual = self._derive(password, salt, iterations)
        return hmac.compare_digest(actual, expected)  # constant-time comparison

    @staticmethod
    def _derive(password, salt, iterations):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

    @staticmethod
    def _encode(data):
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def _decode(text):
        return base64.b64decode(text.encode("ascii"), validate=True)
