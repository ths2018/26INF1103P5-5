
from .patient import Patient
from .patient_validator import PatientValidator


HELP_TEXT = """
What would you like to do?

1. Start a conversation
2. View all saved cases
3. Browse conversation history
4. Export all records to CSV
5. Export all records to Excel
6. View urgency statistics
7. Quit
"""


class InputManager:

    def __init__(self, validator=None,
                 input_func=input, output_func=print):
        self.validator = (
            validator if validator is not None
            else PatientValidator()
        )
        self.input_func = input_func
        self.output_func = output_func

    def get_valid_input(self, prompt, validation_method):
        while True:
            value = self.input_func(prompt).strip()

            try:
                return validation_method(value)

            except ValueError as error:
                self.output_func(str(error))

    def get_menu_input(self):
        self.output_func(HELP_TEXT)

        while True:
            choice = self.input_func(
                "Enter your choice (1-7): "
            ).strip()

            if choice in ("1", "2", "3", "4", "5", "6", "7"):
                return choice

            self.output_func(
                "Invalid input. Please enter a number from 1 to 7."
            )

    def get_name(self):
        return self.get_valid_input(
            "Enter name: ",
            self.validator.validate_name
        )

    def get_dob(self):
        return self.get_valid_input(
            "Enter date of birth (DD/MM/YYYY): ",
            self.validator.validate_dob
        )

    def get_gender(self):
        return self.get_valid_input(
            "Enter gender (Male/Female): ",
            self.validator.validate_gender
        )

    def ask_yes_no(self, prompt):
        while True:
            answer = self.input_func(prompt).strip().lower()

            if answer in ("y", "yes"):
                return True

            if answer in ("n", "no"):
                return False

            self.output_func("Please enter 'y' or 'n'.")

    def has_symptoms(self):
        return self.ask_yes_no(
            "Do you currently have any symptoms? (Yes/No): "
        )

    def get_symptoms(self):
        return self.get_valid_input(
            "Enter symptoms (separate multiple symptoms "
            "with commas): ",
            self.validator.validate_symptoms
        )

    def get_symptom_duration(self):
        return self.get_valid_input(
            "Enter how long you have had your symptoms "
            "(e.g. 3 days, 2 weeks): ",
            self.validator.validate_duration
        )

    def input_manager(self):
        self.output_func("=== Patient Information ===")

        name = self.get_name()
        dob = self.get_dob()
        gender = self.get_gender()

        symptoms_present = self.has_symptoms()

        if symptoms_present:
            symptoms = self.get_symptoms()
            duration = self.get_symptom_duration()
        else:
            symptoms = []
            duration = "None"

        patient = Patient(
            name=name,
            dob=dob,
            gender=gender,
            has_symptoms=symptoms_present,
            symptoms=symptoms,
            symptom_duration=duration
        )

        return patient.to_dict()

    def get_additional_input(self, follow_up_question):
        while True:
            self.output_func(
                "\nAdditional information is required."
            )
            self.output_func(follow_up_question)

            answer = self.input_func("Answer: ").strip()

            if answer:
                return answer

            self.output_func(
                "Please provide the additional Information."
            )

    def keyword_input(self):
        while True:
            self.output_func(
                "Tip: you can also filter with "
                "date:2026-11-01..2026-11-04, "
                "case:3, urgency:urgent"
            )

            keyword = self.input_func(
                "Enter a keyword to search in "
                "conversation history: "
            ).strip()

            if keyword:
                return keyword

            self.output_func("Keyword cannot be empty.")

    def filter_input(self):
        self.output_func(
            "Filters: keyword, "
            "date:YYYY-MM-DD[..YYYY-MM-DD], "
            "case:<name or number>, urgency:<label>"
        )

        return self.input_func(
            "Enter filter (or press Enter for all records): "
        ).strip()
