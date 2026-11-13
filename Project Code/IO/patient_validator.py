
from datetime import datetime, date


class PatientValidator:

    def validate_name(self, name):
        name = name.strip()

        if not name:
            raise ValueError("Name cannot be empty.")

        if not all(
            char.isalpha() or char in " -'"
            for char in name
        ):
            raise ValueError(
                "Name should only contain letters."
            )

        return name

    def validate_dob(self, dob_input):
        try:
            dob = datetime.strptime(
                dob_input, "%d/%m/%Y"
            ).date()

        except ValueError:
            raise ValueError(
                "Invalid date. Please enter DOB "
                "in DD/MM/YYYY format."
            )

        if dob > date.today():
            raise ValueError(
                "Date of birth cannot be in the future."
            )

        return dob

    def validate_gender(self, gender):
        valid_genders = {
            "male": "Male",
            "female": "Female",
            "m": "Male",
            "f": "Female"
        }

        gender = gender.strip().lower()

        if gender not in valid_genders:
            raise ValueError(
                "Please enter a valid option."
            )

        return valid_genders[gender]

    def validate_symptoms(self, symptoms_input):
        symptoms = [
            symptom.strip()
            for symptom in symptoms_input.split(",")
            if symptom.strip()
        ]

        if not symptoms:
            raise ValueError(
                "Please enter at least one symptom."
            )

        return symptoms

    def validate_duration(self, duration):
        valid_units = [
            "minute", "minutes",
            "hour", "hours",
            "day", "days",
            "week", "weeks",
            "month", "months",
            "year", "years"
        ]

        duration = duration.strip().lower()
        parts = duration.split()

        if len(parts) != 2:
            raise ValueError(
                "Please enter duration in the format: 3 days"
            )

        number, unit = parts

        if not number.isdigit():
            raise ValueError(
                "Duration must start with a number."
            )

        if int(number) <= 0:
            raise ValueError(
                "Duration must be greater than 0."
            )

        if unit not in valid_units:
            raise ValueError(
                "Please use minutes, hours, days, "
                "weeks, months, or years."
            )

        return duration
