class AuthService:
    """Sign-up and sign-in. POLYMORPHISM: it only knows the abstract
    PasswordHasher type, so Pbkdf2PasswordHasher or Argon2PasswordHasher can be
    passed in with no change here and no isinstance()/if-elif per algorithm.
    """

    def __init__(self, hasher, user_repository):
        # AGGREGATION: both are created outside and exist independently of this service
        self._hasher = hasher
        self._users = user_repository
        # Hash checked when the username does not exist, so a wrong username and a
        # wrong password take about the same time.
        self.__dummy_hash = hasher.hash_password("not-a-real-password")

    def register(self, username, password, profile=None):
        """Returns True if the account was created, False if the name is taken.
        Raises ValueError for an empty username or password."""
        username = self._clean(username)
        if not username:
            raise ValueError("Email must not be empty.")
        return self._users.add_user(username, self._hasher.hash_password(password), profile)

    def sign_in(self, username, password):
        """Returns True only if the username exists and the password is correct."""
        username = self._clean(username)
        stored = self._users.get_password_hash(username)
        if stored is None:
            self._hasher.verify_password(password, self.__dummy_hash)
            return False
        if not self._hasher.verify_password(password, stored):
            return False
        if self._hasher.needs_rehash(stored):  # upgrade old hashes after a good sign-in
            self._users.update_password_hash(username, self._hasher.hash_password(password))
        return True

    def get_profile(self, username):
        return self._users.get_profile(self._clean(username))

    @staticmethod
    def _clean(username):
        """Emails are treated as case-insensitive."""
        return username.strip().lower() if isinstance(username, str) else ""
