"""Password hashing (PBKDF2-HMAC-SHA256 with a random salt, stdlib only)."""

import hashlib
import hmac
import os


class PasswordHasher:
    ALGORITHM = "pbkdf2_sha256"
    ITERATIONS = 600_000

    @classmethod
    def hash(cls, password):
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, cls.ITERATIONS)
        return f"{cls.ALGORITHM}${cls.ITERATIONS}${salt.hex()}${digest.hex()}"

    @classmethod
    def verify(cls, password, stored):
        try:
            algorithm, iterations, salt_hex, digest_hex = stored.split("$")
            if algorithm != cls.ALGORITHM:
                return False
            candidate = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"),
                bytes.fromhex(salt_hex), int(iterations))
            return hmac.compare_digest(candidate.hex(), digest_hex)
        except (ValueError, AttributeError):
            return False
