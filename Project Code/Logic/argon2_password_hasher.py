from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerificationError

from Logic.password_hasher import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    """Argon2id via the argon2-cffi package (pip install argon2-cffi).

    The stored string carries its own salt and settings: $argon2id$v=19$m=...
    """

    def __init__(self):
        self.__argon2 = _Argon2()  # private: the library object is an internal detail

    def needs_rehash(self, stored_hash):
        try:
            return self.__argon2.check_needs_rehash(stored_hash)
        except (InvalidHashError, TypeError):
            return True

    def _hash(self, password):
        return self.__argon2.hash(password)

    def _verify(self, password, stored_hash):
        try:
            return self.__argon2.verify(stored_hash, password)
        except (VerificationError, InvalidHashError):
            return False
