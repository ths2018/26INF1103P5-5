import re
from datetime import date, datetime


class PatientValidator:

    def validate_name(self, value: str) -> str:
        name = value.strip()

        if not name or not re.fullmatch(
            r"[A-Za-z][A-Za-z '\-]*", name
        ):
            raise ValueError(
                "Enter a valid full name using letters, "
                "spaces, hyphens or apostrophes."
            )

        return name

    def validate_dob(self, value: str) -> date:
        try:
            dob = datetime.strptime(
                value.strip(), "%d/%m/%Y"
            ).date()

        except ValueError as exc:
            raise ValueError(
                "Enter DOB in DD/MM/YYYY format."
            ) from exc

        if dob > date.today():
            raise ValueError(
                "DOB cannot be in the future."
            )

        return dob

    def validate_gender(self, value: str) -> str:
        gender = value.strip().lower()

        if gender in ("male", "m"):
            return "Male"

        if gender in ("female", "f"):
            return "Female"

        raise ValueError(
            "Enter Male or Female (M/F)."
        )

    def validate_symptoms(self, value: str) -> list[str]:
        symptoms = [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

        if not symptoms:
            raise ValueError(
                "Enter at least one symptom."
            )

        return symptoms

    def validate_duration(self, value: str) -> str:
        duration = " ".join(value.strip().split())

        if not re.fullmatch(
            r"[1-9]\d*\s*(?:minutes?|hours?|days?|weeks?|months?|years?)",
            duration,
            re.I
        ):
            raise ValueError(
                "Enter a duration such as "
                "'2 days' or '3 hours'."
            )

        return duration