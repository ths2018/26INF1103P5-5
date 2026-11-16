from input_output_manager import ask_yes_no, get_additional_input, print_output
from Logic.ai_response import AIResponse
from Logic.emergency_detector import EmergencyDetector
from Logic.health_detector import HealthDetector
from Logic.keywords import MAX_FOLLOW_UPS
from Logic.memory_question_detector import MemoryQuestionDetector
from Logic.service_advice_validator import ServiceAdviceValidator
from Logic.urgency_validator import UrgencyValidator


class AssessmentEngine:
    """Runs one healthcare conversation: validation, safety checks, AI calls,
    follow-up questions, case switching and age-risk handling.

    It also holds the current case and chat (replaces passing active_case/chat around).
    """

    _EMERGENCY_GUIDANCE = (
        "The information you provided may indicate a "
        "medical emergency. Seek emergency medical "
        "attention immediately. Do not delay professional "
        "care while using this application."
    )
    _FOLLOW_UP_EMERGENCY_GUIDANCE = (
        "The information you provided may indicate "
        "a medical emergency. Seek emergency medical "
        "attention immediately."
    )
    _NOT_HEALTH_MESSAGE = (
        "I'm sorry, but that question does not appear "
        "to be health-related. Please ask about a "
        "health issue or symptom."
    )
    _URGENCY_RANK = {"insufficient information": 0, "non-urgent": 1, "urgent": 2, "emergency": 3}
    _LOWER_AGE_LIMIT = 5
    _UPPER_AGE_LIMIT = 65

    def __init__(self, ai_service, repository, case=None, chat=None,
                 max_follow_ups=MAX_FOLLOW_UPS, guidelines=None):
        # AGGREGATION: injected from outside; they exist independently of the engine
        # and could be shared with other objects.
        self._ai_service = ai_service
        self._repository = repository
        self._max_follow_ups = max_follow_ups
        self.__guidelines = guidelines

        # ENCAPSULATION: private state, exposed read-only through properties
        self.__case = case
        self.__chat = chat

        # COMPOSITION: created and owned by the engine, private, gone with it
        self.__health = HealthDetector()
        self.__emergency = EmergencyDetector()
        self.__memory = MemoryQuestionDetector()

        # Cross-check of AI answers against the medical guideline data. The
        # GuidelineRepository is injected (aggregation); the validators that use it
        # are created and owned here (composition). No guidelines -> no cross-check.
        self.__validators = (
            [UrgencyValidator(guidelines), ServiceAdviceValidator(guidelines)]
            if guidelines is not None
            else []
        )

    # ---- public API -------------------------------------------------------

    @property
    def case(self):
        return self.__case

    @property
    def chat(self):
        return self.__chat

    def emergency_service_guidance(self):
        """Return public emergency-service advice from the loaded care data."""
        if self.__guidelines is None:
            return None
        record = self.__guidelines.get_service_record("SCDF-EMS-001")
        if not record:
            return None
        source = record.get("source", {})
        return {
            "recommendations": list(record.get("recommendation", [])),
            "source_url": source.get("source_url"),
            "needs_review": self.__guidelines.needs_review(record),
        }

    @staticmethod
    def assess_age_risk(age):
        try:
            age = int(age)
        except (TypeError, ValueError):
            return "Unknown"
        if age < AssessmentEngine._LOWER_AGE_LIMIT or age > AssessmentEngine._UPPER_AGE_LIMIT:
            return "High risk age group"
        return "Not high risk age group"

    def save_exchanges(self, exchanges):
        for exchange in exchanges:
            self._repository.add_log(
                self.__case, exchange["user_input"], exchange["ai_response"]
            )

    def process(self, user_input, age=None):
        """Process one interaction and return the result as a dict."""
        if not isinstance(user_input, str) or not user_input.strip():
            return self._result()
        parsed_input = user_input.strip()

        if self.__memory.detect(parsed_input):
            return self._answer_memory_question(parsed_input)

        if self.__emergency.detect(parsed_input):
            response = AIResponse.emergency(self._EMERGENCY_GUIDANCE)
            return self._result(
                response.text,
                urgency="emergency",
                certainty=1.0,
                is_relevant=True,
                is_health_related=True,
                is_emergency=True,
                exchanges=[self._exchange(parsed_input, response.text)],
            )

        if not self.__health.detect(parsed_input):
            return self._result(self._NOT_HEALTH_MESSAGE, certainty=1.0)

        age_risk = self.assess_age_risk(age) if age is not None else None
        ai_input = self._add_age_note(parsed_input, age_risk)

        # IMPORTANT: never process the reply before checking for None.
        reply = self._ai_service.ask(self.__chat, ai_input)
        if reply is None:
            print_output(
                "[Error] The AI service could not respond. "
                "Please check your API key, internet connection, "
                "and Gemini configuration."
            )
            return self._result(is_health_related=True, age_risk=age_risk)

        response = AIResponse(reply)
        exchanges = [self._exchange(parsed_input, reply)]

        self._check_case_relevance(user_input)

        for _ in range(self._max_follow_ups):
            question = response.follow_up_question
            if not question:
                break

            answer = get_additional_input(question)

            # The follow-up answer itself may contain an obvious emergency.
            if self.__emergency.detect(answer):
                response = AIResponse.emergency(self._FOLLOW_UP_EMERGENCY_GUIDANCE)
                exchanges.append(self._exchange(answer, response.text))
                break

            reply = self._ai_service.ask(self.__chat, answer)
            if reply is None:
                print_output("[Error] The AI could not process the follow-up answer.")
                return self._result(
                    is_health_related=True, exchanges=exchanges, age_risk=age_risk
                )
            response = AIResponse(reply)
            exchanges.append(self._exchange(answer, reply))

        validation = self._cross_check(response, exchanges)
        urgency = validation["urgency_after"] if validation else response.urgency

        return self._result(
            response.text,
            urgency=urgency,
            certainty=response.certainty,
            is_relevant=True,
            has_follow_up=response.has_follow_up,
            is_health_related=True,
            is_emergency=(urgency == "emergency"),
            exchanges=exchanges,
            age_risk=age_risk,
            validation=validation,
        )

    # ---- protected helpers ------------------------------------------------

    def _cross_check(self, response, exchanges):
        """Run every validator. Urgency can only go UP, never down."""
        if not self.__validators:
            return None
        patient_text = "\n".join(e["user_input"] for e in exchanges)
        findings = []
        for validator in self.__validators:  # polymorphic: any ResponseValidator
            findings.extend(validator.validate(response, patient_text))

        before = response.urgency
        after = before
        for finding in findings:
            minimum = finding.get("min_urgency")
            if minimum and self._URGENCY_RANK[minimum] > self._URGENCY_RANK[after]:
                after = minimum
        return {
            "urgency_before": before,
            "urgency_after": after,
            "escalated": after != before,
            "findings": findings,
            "needs_review": any(f["needs_review"] for f in findings),
        }

    @staticmethod
    def _result(ai_response=None, **overrides):
        result = {
            "ai_response": ai_response,
            "urgency": "insufficient information",
            "certainty": 0.0,
            "is_relevant": False,
            "has_follow_up": False,
            "is_health_related": False,
            "is_emergency": False,
            "exchanges": [],
            "validation": None,
        }
        result.update(overrides)
        # Same value as "urgency": the FINAL urgency classification, after the
        # guideline cross-check (emergency / urgent / non-urgent / insufficient information).
        result["urgency_classification"] = result["urgency"]
        return result

    @staticmethod
    def _read(item, name, default=None):
        """Read a field from a dict OR an object (cases/log entries may be either)."""
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    @staticmethod
    def _exchange(user_input, ai_response):
        return {"user_input": user_input, "ai_response": ai_response}

    @staticmethod
    def _add_age_note(text, age_risk):
        if age_risk and age_risk != "Unknown":
            return (
                text
                + f"\nNote: This patient is in the following age category: "
                f"{age_risk}. Please take this into account when "
                f"assessing urgency."
            )
        return text

    def _answer_memory_question(self, parsed_input):
        reply = self._ai_service.ask(self.__chat, parsed_input)
        if reply is None:
            return self._result(is_relevant=True, is_health_related=True)
        response = AIResponse(reply)
        return self._result(
            reply,
            urgency=response.urgency,
            certainty=response.certainty,
            is_relevant=True,
            is_health_related=True,
            is_emergency=response.is_emergency,
            exchanges=[self._exchange(parsed_input, reply)],
        )

    def _check_case_relevance(self, user_input):
        """If the input looks unrelated to the open case, offer to start a new one."""
        case = self.__case or self._repository.get_active_case()
        logs = self._read(case, "logs", []) if case else []
        if not (case and logs):
            return
        if self._ai_service.is_relevant(user_input, case):
            return

        case_id = self._read(case, "case_id", "")
        first_entry = str(self._read(logs[0], "user_input", ""))[:30]
        print_output(f"\n[System] This may be unrelated to {case_id}")
        if ask_yes_no(
            f"Is it related to your earlier entry ({first_entry}...)? (y/n): "
        ):
            print_output(f"[System] Continuing with {case_id}\n")
            return

        self._repository.close_case(case)
        new_case = self._repository.create_case()
        self.__case = new_case
        self.__chat = self._ai_service.create_chat(new_case)
        # save the new prompt into the new case's log
        self._repository.add_log(new_case, user_input, "")
