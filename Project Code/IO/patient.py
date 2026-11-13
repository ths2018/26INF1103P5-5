
from datetime import datetime, date


class Patient:
    def __init__(self, name, dob, gender,
                 has_symptoms, symptoms, symptom_duration):

        self.name = name
        self.dob = dob
        self.gender = gender
        self.has_symptoms = has_symptoms
        self.symptoms = symptoms
        self.symptom_duration = symptom_duration
        self.timestamp = datetime.now().isoformat(
            timespec="seconds"
        )

    @staticmethod
    def calculate_age(dob):
        today = date.today()

        age = today.year - dob.year

        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1

        return age

    def to_dict(self):
        return {
            "name": self.name,
            "dob": self.dob.isoformat(),
            "age": self.calculate_age(self.dob),
            "gender": self.gender,
            "has_symptoms": self.has_symptoms,
            "symptoms": self.symptoms.copy(),
            "symptom_duration": self.symptom_duration,
            "timestamp": self.timestamp
        }
