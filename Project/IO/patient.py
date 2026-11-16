from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Patient:
    name: str
    dob: str
    gender: str
    symptoms: list[str]
    symptom_duration: str
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(
            timespec="seconds"
        )
    )

    @staticmethod
    def calculate_age(dob: date | str) -> int:
        if isinstance(dob, str):
            dob = date.fromisoformat(dob)

        today = date.today()

        return (
            today.year
            - dob.year
            - ((today.month, today.day) < (dob.month, dob.day))
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "dob": self.dob,
            "age": self.calculate_age(self.dob),
            "gender": self.gender,
            "has_symptoms": bool(self.symptoms),
            "symptoms": self.symptoms.copy(),
            "symptom_duration": self.symptom_duration,
            "timestamp": self.timestamp,
        }