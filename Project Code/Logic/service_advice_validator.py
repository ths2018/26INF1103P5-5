from datetime import date

from Logic.response_validator import ResponseValidator


class ServiceAdviceValidator(ResponseValidator):
    """Checks the healthcare-service advice in the AI's reply against
    care_recommendations.json:
      * 995 / ambulance suggested for a condition SCDF lists as non-emergency
      * the 1777 hotline (being replaced by NurseFirst) is mentioned
    """

    _EMS_ID = "SCDF-EMS-001"
    _NON_EMERGENCY_ID = "SCDF-NON-EMERGENCY-001"

    def __init__(self, guidelines, today=None):
        super().__init__(guidelines)
        self._today = today or date.today()

    def validate(self, response, patient_text):
        ai_text = response.text if isinstance(response.text, str) else ""
        emergency = self._guidelines.get_service_record(self._EMS_ID)
        non_emergency = self._guidelines.get_service_record(self._NON_EMERGENCY_ID)
        findings = []

        if emergency and non_emergency and response.urgency != "emergency":
            suggests_995 = self._guidelines.mentions(ai_text, "995") or \
                self._guidelines.mentions(ai_text, "ambulance")
            if suggests_995:
                serious = self._guidelines.matched_phrases(
                    emergency.get("conditions_requiring_995", []), patient_text)
                minor = self._guidelines.matched_phrases(
                    non_emergency.get("conditions_not_requiring_995", []), patient_text)
                if minor and not serious:
                    findings.append(
                        self._finding(
                            "note",
                            f"The response mentions an ambulance or 995, but SCDF lists "
                            f"{', '.join(m.lower() for m in minor)} as non-emergency. SCDF "
                            f"advises a GP, polyclinic, Urgent Care Centre or the NurseFirst "
                            f"helpline (6262 6262) instead.",
                            non_emergency,
                        )
                    )

        if non_emergency and "1777" in ai_text:
            for change in non_emergency.get("effective_changes", []):
                if "1777" not in change.get("description", ""):
                    continue
                when = change.get("effective_date", "")
                service = change.get("replacement_service", "NurseFirst")
                contact = change.get("replacement_contact", "")
                try:
                    ended = date.fromisoformat(when) <= self._today
                except ValueError:
                    ended = False
                tense = "has ceased" if ended else f"will cease on {when}"
                findings.append(
                    self._finding(
                        "note",
                        f"The 1777 non-emergency ambulance hotline {tense}. Use "
                        f"{service} ({contact}) instead.",
                        non_emergency,
                    )
                )
        return findings
