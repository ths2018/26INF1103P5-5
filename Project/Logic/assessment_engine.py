from input_output_manager import ask_yes_no, get_additional_input, print_output
from Logic.ai_response import AIResponse
from Logic.emergency_detector import EmergencyDetector
from Logic.health_detector import HealthDetector
from Logic.keywords import MAX_FOLLOW_UPS
from Logic.memory_question_detector import MemoryQuestionDetector


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
    _LOWER_AGE_LIMIT = 5
    _UPPER_AGE_LIMIT = 65

    def __init__(self, ai_service, repository, case=None, chat=None,
                 max_follow_ups=MAX_FOLLOW_UPS):
        # AGGREGATION: injected from outside; they exist independently of the engine
        # and could be shared with other objects.
        self._ai_service = ai_service
        self._repository = repository
        self._max_follow_ups = max_follow_ups

        # ENCAPSULATION: private state, exposed read-only through properties
        self.__case = case
        self.__chat = chat

        # COMPOSITION: created and owned by the engine, private, gone with it
        self.__health = HealthDetector()
        self.__emergency = EmergencyDetector()
        self.__memory = MemoryQuestionDetector()

    # ---- public API -------------------------------------------------------

    @property
    def case(self):
        return self.__case

    @property
    def chat(self):
        return self.__chat

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

        return self._result(
            response.text,
            urgency=response.urgency,
            certainty=response.certainty,
            is_relevant=True,
            has_follow_up=response.has_follow_up,
            is_health_related=True,
            is_emergency=response.is_emergency,
            exchanges=exchanges,
            age_risk=age_risk,
        )

    # ---- protected helpers ------------------------------------------------

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
        }
        result.update(overrides)
        return result

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
        if not (case and case.get("logs", [])):
            return
        if self._ai_service.is_relevant(user_input, case):
            return

        first_entry = case["logs"][0].get("user_input", "")[:30]
        print_output(f"\n[System] This may be unrelated to {case['case_id']}.json")
        if ask_yes_no(
            f"Is it related to your earlier entry ({first_entry}...)? (y/n): "
        ):
            print_output(f"[System] Continuing with {case['case_id']}.json\n")
            return

        self._repository.close_case(case)
        new_case = self._repository.create_case()
        self.__case = new_case
        self.__chat = self._ai_service.create_chat(new_case)
        # save the new prompt into the new case's log
        self._repository.add_log(new_case, user_input, "")
