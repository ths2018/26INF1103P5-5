class AuthController:
    """The sign-in gate: shows the sign-up / log-in menu until the user either
    signs in or chooses to exit. All console input/output goes through `view`
    (pass the input_output_manager module, or any object with the same functions).
    """

    _MAX_ATTEMPTS = 3

    def __init__(self, auth_service, view):
        # ASSOCIATION: collaborators that are used, not owned
        self._auth = auth_service
        self._view = view

    def run(self):
        """Returns the signed-in user's profile dict (always includes 'email'),
        or None if the user chose to exit."""
        while True:
            choice = self._view.get_auth_menu_choice()
            if choice == "3":
                return None
            if choice == "2":
                self._sign_up()
            elif choice == "1":
                user = self._log_in()
                if user is not None:
                    return user

    # ---- protected helpers ------------------------------------------------

    def _sign_up(self):
        email = self._view.get_email()
        details = self._view.get_signup_details(email)
        password, profile = self._split_details(details)
        try:
            created = self._auth.register(email, password, profile)
        except ValueError as exc:
            self._view.display_auth_message(str(exc))
            return
        if created:
            self._view.display_signup_success()
        else:
            self._view.display_auth_message("An account with this email already exists.")

    def _log_in(self):
        for _ in range(self._MAX_ATTEMPTS):
            email = self._view.get_email()
            password = self._view.get_login_password()
            if self._auth.sign_in(email, password):
                self._view.display_login_success()
                profile = self._auth.get_profile(email)
                return {**profile, "email": email.strip().lower()}
            self._view.display_login_error()
        self._view.display_auth_message("Too many failed attempts. Returning to the menu.")
        return None

    @staticmethod
    def _split_details(details):
        """get_signup_details() may return a dict that includes 'password', or just
        the password string. Returns (password, profile_without_password)."""
        if isinstance(details, dict):
            profile = dict(details)
            return profile.pop("password", None), profile
        return details, {}
