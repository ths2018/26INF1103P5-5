from Logic.response_validator import ResponseValidator


class UrgencyValidator(ResponseValidator):
    """Safety net against UNDER-triage: if the patient mentions a warning sign that
    the guidelines say needs the Emergency Department (or 995), the AI's urgency
    must be at least that high. It can only raise urgency, never lower it.
    """

    # care level in the guideline data -> (minimum AI urgency, wording)
    _LEVELS = {
        "emergency_response": ("emergency", "emergency response (call 995)"),
        "emergency_department": ("urgent", "care at the Emergency Department"),
    }

    def validate(self, response, patient_text):
        records = self._guidelines.find_symptom_records(patient_text)
        if not records:
            return [
                self._finding(
                    "no_match",
                    "No matching guideline was found for these symptoms, so the "
                    "urgency was not cross-checked.",
                )
            ]

        findings = []
        for record in records:
            for level, (minimum, wording) in self._LEVELS.items():
                conditions = self._guidelines.red_flag_conditions(record, level)
                for hit in self._guidelines.matched_phrases(conditions, patient_text):
                    findings.append(
                        self._finding(
                            "red_flag",
                            f"The guideline '{record.get('topic')}' lists "
                            f"'{hit.rstrip('.')}' as a warning sign that needs {wording}.",
                            record,
                            min_urgency=minimum,
                        )
                    )

        if not findings:
            topics = ", ".join(r.get("topic", "?") for r in records)
            findings.append(
                self._finding(
                    "consistent",
                    f"No warning signs from the guideline data were found for: {topics}.",
                    records[0],
                )
            )
        return findings
