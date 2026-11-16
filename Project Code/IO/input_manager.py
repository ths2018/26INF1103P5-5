from datetime import date

from IO.patient import Patient
from IO.patient_validator import PatientValidator


class InputManager:

    def __init__(
        self,
        validator=None,
        input_func=None,
        output_func=None
    ):
        self.validator = (
            validator
            if validator is not None
            else PatientValidator()
        )

        self._input = (
            input_func if input_func is not None else input
        )

        self._print = (
            output_func if output_func is not None else print
        )

    def get_valid_input(self, prompt, validator):
        while True:
            try:
                return validator(self._input(prompt))

            except ValueError as exc:
                self._print(str(exc))

    def get_menu_input(self):
        return self.get_valid_input(
            "Choose an option (1-6): ",
            self._validate_menu
        )

    @staticmethod
    def _validate_menu(value):
        choice = value.strip()

        if choice not in {
            "1", "2", "3", "4", "5", "6"
        }:
            raise ValueError(
                "Invalid option. Enter a number from 1 to 6."
            )

        return choice

    def get_name(self):
        return self.get_valid_input(
            "Full name: ",
            self.validator.validate_name
        )

    def get_dob(self):
        return self.get_valid_input(
            "Date of birth (DD/MM/YYYY): ",
            self.validator.validate_dob
        )

    @staticmethod
    def calculate_age(dob):
        return Patient.calculate_age(dob)

    def get_gender(self):
        return self.get_valid_input(
            "Gender (Male/Female): ",
            self.validator.validate_gender
        )

    def ask_yes_no(self, prompt):
        while True:
            answer = self._input(prompt).strip().lower()

            if answer in ("y", "yes"):
                return True

            if answer in ("n", "no"):
                return False

            self._print("Please enter yes or no.")

    def has_symptoms(self):
        return self.ask_yes_no(
            "Are you experiencing symptoms? (yes/no): "
        )

    def get_symptoms(self):
        return self.get_valid_input(
            "Enter symptoms (comma-separated): ",
            self.validator.validate_symptoms
        )

    def get_symptom_duration(self):
        return self.get_valid_input(
            "How long have you had these symptoms? "
            "(e.g. 2 days): ",
            self.validator.validate_duration
        )

    def input_manager(self, user_profile):
        """
        Collect symptoms and symptom duration only.

        The authenticated user profile must be supplied
        by the authentication layer.

        Required profile fields:
        - full_name (or name)
        - dob
        - gender
        """

        if not isinstance(user_profile, dict):
            raise TypeError(
                "An authenticated user profile "
                "dictionary is required."
            )

        name = (
            user_profile.get("full_name")
            or user_profile.get("name")
        )

        dob = user_profile.get("dob")
        gender = user_profile.get("gender")

        if not name or not dob or not gender:
            raise ValueError(
                "Authenticated profile is missing "
                "name, DOB or gender."
            )

        if isinstance(dob, date):
            dob_iso = dob.isoformat()

        elif isinstance(dob, str):
            try:
                dob_iso = date.fromisoformat(
                    dob
                ).isoformat()

            except ValueError:
                dob_iso = self.validator.validate_dob(
                    dob
                ).isoformat()

        else:
            raise ValueError(
                "Unsupported DOB format "
                "in authenticated profile."
            )

        # Only collect these two inputs
        symptoms = self.get_symptoms()
        duration = self.get_symptom_duration()

        patient = Patient(
            name=str(name),
            dob=dob_iso,
            gender=str(gender),
            symptoms=symptoms,
            symptom_duration=duration
        )

        return patient.to_dict()

    def get_additional_input(self, question):
        return self._input(
            f"{question.strip()} "
        ).strip()

    def select_cases(self, cases):
        """
        List `cases` (summary dicts from CaseManager.export_choices) and ask
        which ones to use. Returns a list of case ids, or None if the user
        cancels by pressing Enter.
        """
        self._print("\nWhich case(s) do you want to export?")

        for i, case in enumerate(cases, start=1):
            created = (
                (case.get("created") or "unknown date")[:16]
                .replace("T", " ")
            )
            noun = "entry" if case["entries"] == 1 else "entries"

            self._print(
                f"  {i}. {case['case_id']} - {case['status']}, "
                f"{case['entries']} {noun}, created {created}"
            )

        return self.get_valid_input(
            "Enter numbers (e.g. 1,3 or 1-3), 'all', "
            "or press Enter to cancel: ",
            lambda value: self._validate_case_selection(value, cases)
        )

    @staticmethod
    def _validate_case_selection(value, cases):
        """Turn '1,3', '2-4' or 'all' into case ids. Blank returns None."""
        text = value.strip().lower()

        if not text:
            return None

        if text == "all":
            return [case["case_id"] for case in cases]

        total = len(cases)
        chosen = set()

        for part in text.replace(" ", "").split(","):
            start, dash, end = part.partition("-")

            if not start.isdigit() or (dash and not end.isdigit()):
                raise ValueError(
                    f"'{part}' is not a valid choice. "
                    f"Enter numbers from 1 to {total}."
                )

            first = int(start)
            last = int(end) if dash else first

            if first < 1 or last > total or first > last:
                raise ValueError(
                    f"'{part}' is out of range. "
                    f"Enter numbers from 1 to {total}."
                )

            chosen.update(range(first, last + 1))

        return [cases[i - 1]["case_id"] for i in sorted(chosen)]

    def keyword_input(self):
        return self._input(
            "Enter keyword: "
        ).strip()

    def filter_input(self):
        return self._input(
            "Enter filter: "
        ).strip()