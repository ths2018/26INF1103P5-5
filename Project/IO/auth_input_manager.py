import re
from getpass import getpass

from IO.input_manager import InputManager


class AuthInputManager:

    def __init__(
        self,
        input_manager=None,
        input_func=None,
        output_func=None,
        password_func=None
    ):
        self._input = (
            input_func if input_func is not None else input
        )

        self._print = (
            output_func if output_func is not None else print
        )

        self._password = (
            password_func
            if password_func is not None
            else getpass
        )

        self.patient_input = (
            input_manager
            if input_manager is not None
            else InputManager(
                input_func=self._input,
                output_func=self._print
            )
        )

    def get_email(self):
        while True:
            email = self._input(
                "Enter your email: "
            ).strip().lower()

            if (
                len(email) <= 254
                and re.fullmatch(
                    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
                    email
                )
            ):
                return email

            self._print(
                "Invalid email format. Please try again."
            )

    def get_signup_details(self, email):
        """
        Called when the Logic Manager determines
        that the email is not registered.
        """

        self._print("\n===== SIGN UP =====")

        name = self.patient_input.get_name()
        dob = self.patient_input.get_dob()
        gender = self.patient_input.get_gender()

        while True:
            password = self._password(
                "Create password: "
            )

            confirmation = self._password(
                "Confirm password: "
            )

            if password != confirmation:
                self._print(
                    "Passwords do not match. "
                    "Please try again."
                )

            elif not password:
                self._print(
                    "Password cannot be empty."
                )

            else:
                break

        return {
            "email": email,
            "full_name": name,
            "dob": dob.isoformat(),
            "gender": gender,
            "password": password
        }

    def get_login_password(self):
        return self._password(
            "Enter your password: "
        )

    def display_auth_message(self, message):
        self._print(message)

    def display_signup_success(self):
        self._print(
            "Account created successfully. "
            "Please log in to continue."
        )

    def display_login_success(self):
        self._print(
            "Login successful. Welcome to the "
            "Healthcare Assessment Chatbot!"
        )

    def display_login_error(self):
        self._print(
            "Login failed. Please check your "
            "credentials and try again."
        )