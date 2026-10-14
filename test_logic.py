"""
Offline tests for logic_manager.py

- No live AI / network: every AI reply is hardcoded (see FakeAI below).
- No dependency on ai_manager, input_output_manager or data_manager being
  importable: lightweight stub modules are registered in sys.modules BEFORE
  logic_manager is imported, so nothing like google-generativeai or an API key
  is needed inside the Docker container.
- Standard library only (unittest + unittest.mock), so it also runs under pytest.

Run:
    python -m unittest -v test_logic_manager
"""

import os
import sys
import types
import unittest
from unittest import mock

# ---------------------------------------------------------------------------
# Make logic_manager importable whether this file sits next to it or in tests/
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, os.path.dirname(_HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ---------------------------------------------------------------------------
# Stub the three modules logic_manager imports from
# ---------------------------------------------------------------------------
_STUBS = {
    "ai_manager": ["ask_ai", "check_relevance", "create_chat"],
    "input_output_manager": [
        "input_manager", "create_prompt", "get_additional_input", "print_cases",
        "keyword_input", "print_output", "ask_yes_no",
    ],
    "data_manager": [
        "add_log", "close_case", "convert_json_to_csv", "convert_json_to_xlsx",
        "create_new_case", "filter_records_by_keyword", "get_active_case",
        "list_case_files", "load_case", "open_file", "show_history",
    ],
}

for _module_name, _names in _STUBS.items():
    _stub = types.ModuleType(_module_name)
    for _n in _names:
        setattr(_stub, _n, mock.MagicMock(name=f"{_module_name}.{_n}"))
    sys.modules[_module_name] = _stub

import logic_manager as lm  # noqa: E402  (must come after the stubs)


# ---------------------------------------------------------------------------
# Hardcoded AI replies (same layout the real model is prompted to produce)
# ---------------------------------------------------------------------------
REPLY_NON_URGENT = (
    "Urgency classification: non-urgent\n"
    "Certainty: 85%\n\n"
    "Follow-Up Questions:\n"
    "None\n\n"
    "Next-Step Guidance:\n"
    "Rest, drink fluids and monitor your symptoms."
)

REPLY_URGENT = (
    "Urgency classification: urgent\n"
    "Certainty: 70%\n\n"
    "Follow-Up Questions:\n"
    "None\n\n"
    "Next-Step Guidance:\n"
    "See a doctor within 24 hours."
)

REPLY_EMERGENCY = (
    "Urgency classification: emergency\n"
    "Certainty: 95%\n\n"
    "Follow-Up Questions:\n"
    "None\n\n"
    "Next-Step Guidance:\n"
    "Call emergency services now."
)

REPLY_FOLLOW_UP = (
    "Urgency classification: insufficient information\n"
    "Certainty: 40%\n\n"
    "Follow-Up Questions:\n"
    "How long have you had these symptoms?\n\n"
    "Next-Step Guidance:\n"
    "More information is needed."
)

REPLY_MEMORY = (
    "Earlier you told me you had a headache and mild fever.\n"
    "Urgency classification: non-urgent\n"
    "Certainty: 60%"
)


class FakeAI:
    """Replaces ask_ai: returns scripted replies in order and records calls."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []  # list of (chat, text)

    def __call__(self, chat, text):
        self.calls.append((chat, text))
        if not self.replies:
            raise AssertionError("ask_ai called more times than scripted")
        return self.replies.pop(0)

    @property
    def texts(self):
        return [text for _, text in self.calls]


class LogicManagerTestCase(unittest.TestCase):
    """Base class: patches every external dependency on logic_manager."""

    def setUp(self):
        self.mocks = {}
        names = [n for names in _STUBS.values() for n in names]
        for name in names:
            patcher = mock.patch.object(lm, name, mock.MagicMock(name=name))
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

        # Safe defaults
        self.mocks["get_active_case"].return_value = None
        self.mocks["check_relevance"].return_value = True
        self.mocks["ask_yes_no"].return_value = True

    def script_ai(self, replies):
        fake = FakeAI(replies)
        self.mocks["ask_ai"].side_effect = fake
        return fake

    def printed(self):
        """All text passed to print_output, joined together."""
        return "\n".join(
            str(c.args[0]) for c in self.mocks["print_output"].call_args_list if c.args
        )


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------
class TestKeywordHelpers(unittest.TestCase):
    def test_phrase_matching_respects_word_boundaries(self):
        self.assertTrue(lm._containes_phrase("a cut on my finger", "cut"))
        self.assertFalse(lm._containes_phrase("execute the plan", "cut"))
        self.assertTrue(lm._containes_phrase("I have a SORE THROAT", "sore throat"))

    def test_is_health_related(self):
        self.assertTrue(lm.is_health_related("I have a headache"))
        self.assertTrue(lm.is_health_related("My knee hurts when I walk"))
        self.assertFalse(lm.is_health_related("What is the capital of France?"))
        self.assertFalse(lm.is_health_related(""))
        self.assertFalse(lm.is_health_related(None))
        self.assertFalse(lm.is_health_related(123))

    def test_contains_emergency_keywords(self):
        self.assertTrue(lm.contains_emergency_keywords("He is unconscious"))
        self.assertTrue(lm.contains_emergency_keywords("I can't breathe"))
        self.assertTrue(lm.contains_emergency_keywords("She had a SEIZURE"))
        self.assertFalse(lm.contains_emergency_keywords("I have a mild headache"))
        self.assertFalse(lm.contains_emergency_keywords("my chest pain is mild"))
        self.assertFalse(lm.contains_emergency_keywords(None))

    def test_is_memory_question(self):
        self.assertTrue(lm.is_memory_question("What did we talk about earlier?"))
        self.assertTrue(lm.is_memory_question("  Do you remember my symptoms?  "))
        self.assertFalse(lm.is_memory_question("I have a headache"))
        self.assertFalse(lm.is_memory_question(None))

    def test_is_high_risk_age(self):
        self.assertEqual(lm.is_high_risk_age(3), "High risk age group")
        self.assertEqual(lm.is_high_risk_age(70), "High risk age group")
        self.assertEqual(lm.is_high_risk_age("80"), "High risk age group")
        self.assertEqual(lm.is_high_risk_age(5), "Not high risk age group")
        self.assertEqual(lm.is_high_risk_age(65), "Not high risk age group")
        self.assertEqual(lm.is_high_risk_age(30), "Not high risk age group")
        self.assertEqual(lm.is_high_risk_age("abc"), "Unknown")
        self.assertEqual(lm.is_high_risk_age(None), "Unknown")

    def test_is_answer_relevant(self):
        self.assertTrue(lm.is_answer_relevant("my headache", "a headache can be"))
        self.assertFalse(lm.is_answer_relevant("my headache", "unrelated words"))


# ---------------------------------------------------------------------------
# Parsing of AI responses
# ---------------------------------------------------------------------------
class TestResponseParsing(unittest.TestCase):
    def test_get_urgency(self):
        self.assertEqual(lm.get_urgency(REPLY_NON_URGENT), "non-urgent")
        self.assertEqual(lm.get_urgency(REPLY_URGENT), "urgent")
        self.assertEqual(lm.get_urgency(REPLY_EMERGENCY), "emergency")
        self.assertEqual(lm.get_urgency(REPLY_FOLLOW_UP), "insufficient information")
        self.assertEqual(
            lm.get_urgency("URGENCY CLASSIFICATION: Urgent"), "urgent"
        )

    def test_get_urgency_bad_input(self):
        self.assertEqual(lm.get_urgency("no label here"), "insufficient information")
        self.assertEqual(lm.get_urgency(None), "insufficient information")

    def test_get_certainty(self):
        self.assertAlmostEqual(lm.get_certainty("Certainty: 85%"), 0.85)
        self.assertAlmostEqual(lm.get_certainty("Certainty: 85"), 0.85)
        self.assertAlmostEqual(lm.get_certainty("Certainty: 0.7"), 0.7)
        self.assertAlmostEqual(lm.get_certainty("Certainty: 100%"), 1.0)
        self.assertAlmostEqual(lm.get_certainty("Certainty: 150"), 1.0)  # clamped

    def test_get_certainty_bad_input(self):
        self.assertEqual(lm.get_certainty("nothing here"), 0.0)
        self.assertEqual(lm.get_certainty(None), 0.0)

    def test_is_emergency_only_for_explicit_emergency(self):
        self.assertTrue(lm.is_emergency(REPLY_EMERGENCY))
        self.assertFalse(lm.is_emergency(REPLY_URGENT))
        self.assertFalse(lm.is_emergency(REPLY_NON_URGENT))

    def test_extract_follow_up_question(self):
        self.assertEqual(
            lm.extract_follow_up_question(REPLY_FOLLOW_UP),
            "How long have you had these symptoms?",
        )

    def test_extract_follow_up_question_none_cases(self):
        self.assertIsNone(lm.extract_follow_up_question(REPLY_NON_URGENT))
        self.assertIsNone(
            lm.extract_follow_up_question("Follow-Up Questions:\nNot applicable")
        )
        self.assertIsNone(lm.extract_follow_up_question("no sections at all"))
        self.assertIsNone(lm.extract_follow_up_question(None))

    def test_has_follow_up_question(self):
        self.assertTrue(lm.has_follow_up_question(REPLY_FOLLOW_UP))
        self.assertFalse(lm.has_follow_up_question(REPLY_NON_URGENT))

    def test_extract_section_stops_at_next_label(self):
        guidance = lm.extract_section(REPLY_URGENT, "Next-Step Guidance:")
        self.assertEqual(guidance, "See a doctor within 24 hours.")
        follow_up = lm.extract_section(REPLY_FOLLOW_UP, "Follow-Up Questions:")
        self.assertNotIn("Next-Step", follow_up)

    def test_extract_section_missing_or_invalid(self):
        self.assertIsNone(lm.extract_section(REPLY_NON_URGENT, "Nonexistent:"))
        self.assertIsNone(lm.extract_section(None, "Follow-Up Questions:"))


# ---------------------------------------------------------------------------
# is_case_related
# ---------------------------------------------------------------------------
class TestIsCaseRelated(LogicManagerTestCase):
    def test_true_without_case_or_logs(self):
        self.assertTrue(lm.is_case_related("anything", None))
        self.assertTrue(lm.is_case_related("anything", {"logs": []}))
        self.mocks["check_relevance"].assert_not_called()

    def test_memory_question_is_always_related(self):
        case = {"logs": [{"user_input": "headache", "ai_response": "x"}]}
        self.assertTrue(lm.is_case_related("what did we talk about", case))
        self.mocks["check_relevance"].assert_not_called()

    def test_delegates_to_check_relevance(self):
        case = {"logs": [{"user_input": "headache", "ai_response": "x"}]}
        self.mocks["check_relevance"].return_value = False
        self.assertFalse(lm.is_case_related("my ankle hurts", case))
        self.mocks["check_relevance"].assert_called_once_with("my ankle hurts", case)


# ---------------------------------------------------------------------------
# process_interaction
# ---------------------------------------------------------------------------
class TestProcessInteractionGuards(LogicManagerTestCase):
    def test_non_string_input(self):
        fake = self.script_ai([])
        result = lm.process_interaction(None, chat=object())
        self.assertIsNone(result["ai_response"])
        self.assertFalse(result["is_health_related"])
        self.assertEqual(fake.calls, [])

    def test_empty_and_whitespace_input(self):
        fake = self.script_ai([])
        for text in ("", "   \n\t"):
            result = lm.process_interaction(text, chat=object())
            self.assertIsNone(result["ai_response"])
            self.assertEqual(result["exchanges"], [])
        self.assertEqual(fake.calls, [])

    def test_non_health_question_never_reaches_ai(self):
        fake = self.script_ai([])
        result = lm.process_interaction("What is the capital of France?", chat=object())
        self.assertFalse(result["is_health_related"])
        self.assertFalse(result["is_relevant"])
        self.assertEqual(result["exchanges"], [])
        self.assertIn("does not appear", result["ai_response"])
        self.assertEqual(fake.calls, [])

    def test_emergency_keyword_overrides_ai(self):
        fake = self.script_ai([])
        result = lm.process_interaction(
            "My dad is unconscious and not breathing", chat=object()
        )
        self.assertTrue(result["is_emergency"])
        self.assertEqual(result["urgency"], "emergency")
        self.assertEqual(result["certainty"], 1.0)
        self.assertEqual(len(result["exchanges"]), 1)
        self.assertEqual(fake.calls, [])  # AI is never consulted

    def test_memory_question_goes_to_ai_once(self):
        fake = self.script_ai([REPLY_MEMORY])
        result = lm.process_interaction("What did we talk about earlier?", chat="CHAT")
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(fake.calls[0][0], "CHAT")
        self.assertEqual(result["ai_response"], REPLY_MEMORY)
        self.assertEqual(result["urgency"], "non-urgent")
        self.assertFalse(result["has_follow_up"])
        self.assertEqual(len(result["exchanges"]), 1)

    def test_memory_question_ai_failure(self):
        self.script_ai([None])
        result = lm.process_interaction("What did we talk about earlier?", chat=object())
        self.assertIsNone(result["ai_response"])
        self.assertEqual(result["exchanges"], [])


class TestProcessInteractionAI(LogicManagerTestCase):
    def test_simple_assessment(self):
        fake = self.script_ai([REPLY_NON_URGENT])
        result = lm.process_interaction("I have a headache and a mild fever", chat=object())
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(result["urgency"], "non-urgent")
        self.assertAlmostEqual(result["certainty"], 0.85)
        self.assertFalse(result["has_follow_up"])
        self.assertFalse(result["is_emergency"])
        self.assertTrue(result["is_health_related"])
        self.assertEqual(len(result["exchanges"]), 1)
        self.assertIsNone(result["age_risk"])

    def test_ai_classified_emergency_is_flagged(self):
        self.script_ai([REPLY_EMERGENCY])
        result = lm.process_interaction("I feel very dizzy and weak", chat=object())
        self.assertTrue(result["is_emergency"])
        self.assertEqual(result["urgency"], "emergency")

    def test_urgent_is_not_emergency(self):
        self.script_ai([REPLY_URGENT])
        result = lm.process_interaction("I have a swollen ankle", chat=object())
        self.assertEqual(result["urgency"], "urgent")
        self.assertFalse(result["is_emergency"])

    def test_high_risk_age_note_is_sent_to_ai_only(self):
        fake = self.script_ai([REPLY_NON_URGENT])
        result = lm.process_interaction("I have a fever", chat=object(), age=70)
        self.assertIn("High risk age group", fake.texts[0])
        self.assertEqual(result["age_risk"], "High risk age group")
        # The logged exchange keeps the user's original wording
        self.assertEqual(result["exchanges"][0]["user_input"], "I have a fever")

    def test_normal_age_note(self):
        fake = self.script_ai([REPLY_NON_URGENT])
        result = lm.process_interaction("I have a fever", chat=object(), age=30)
        self.assertIn("Not high risk age group", fake.texts[0])
        self.assertEqual(result["age_risk"], "Not high risk age group")

    def test_unknown_age_adds_no_note(self):
        fake = self.script_ai([REPLY_NON_URGENT])
        result = lm.process_interaction("I have a fever", chat=object(), age="abc")
        self.assertEqual(fake.texts[0], "I have a fever")
        self.assertEqual(result["age_risk"], "Unknown")

    def test_ai_failure_on_first_call(self):
        self.script_ai([None])
        result = lm.process_interaction("I have a fever", chat=object())
        self.assertIsNone(result["ai_response"])
        self.assertEqual(result["certainty"], 0.0)
        self.assertEqual(result["exchanges"], [])
        self.assertIn("[Error]", self.printed())


class TestFollowUps(LogicManagerTestCase):
    def test_follow_up_answered_then_resolved(self):
        fake = self.script_ai([REPLY_FOLLOW_UP, REPLY_NON_URGENT])
        self.mocks["get_additional_input"].return_value = "About three days"

        result = lm.process_interaction("I have a fever", chat=object())

        self.mocks["get_additional_input"].assert_called_once_with(
            "How long have you had these symptoms?"
        )
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(fake.texts[1], "About three days")
        self.assertEqual(len(result["exchanges"]), 2)
        self.assertEqual(result["urgency"], "non-urgent")
        self.assertFalse(result["has_follow_up"])

    def test_emergency_keyword_in_follow_up_answer_stops_loop(self):
        fake = self.script_ai([REPLY_FOLLOW_UP])
        self.mocks["get_additional_input"].return_value = "Actually I just collapsed"

        result = lm.process_interaction("I have a headache and feel dizzy", chat=object())

        self.assertEqual(len(fake.calls), 1)  # no second AI call
        self.assertTrue(result["is_emergency"])
        self.assertEqual(result["certainty"], 1.0)
        self.assertEqual(len(result["exchanges"]), 2)
        self.assertFalse(result["has_follow_up"])

    def test_ai_failure_during_follow_up(self):
        self.script_ai([REPLY_FOLLOW_UP, None])
        self.mocks["get_additional_input"].return_value = "three days"

        result = lm.process_interaction("I have a fever", chat=object())

        self.assertIsNone(result["ai_response"])
        self.assertEqual(len(result["exchanges"]), 1)  # only the first exchange
        self.assertIn("follow-up", self.printed())

    def test_follow_up_loop_is_capped(self):
        fake = self.script_ai([REPLY_FOLLOW_UP] * (lm.MAX_FOLLOW_UPS + 5))
        self.mocks["get_additional_input"].return_value = "no change"

        result = lm.process_interaction("I have a fever", chat=object())

        self.assertEqual(len(fake.calls), 1 + lm.MAX_FOLLOW_UPS)
        self.assertEqual(
            self.mocks["get_additional_input"].call_count, lm.MAX_FOLLOW_UPS
        )
        self.assertTrue(result["has_follow_up"])  # still asking when capped


class TestCaseRelevanceFlow(LogicManagerTestCase):
    def setUp(self):
        super().setUp()
        self.case = {
            "case_id": "case_001",
            "logs": [{"user_input": "I have had a headache since Monday", "ai_response": "x"}],
        }
        self.new_case = {"case_id": "case_002", "logs": []}
        self.mocks["create_new_case"].return_value = self.new_case

    def test_no_logs_skips_relevance_check(self):
        self.script_ai([REPLY_NON_URGENT])
        lm.process_interaction("I have a fever", chat=object(),
                               active_case={"case_id": "c", "logs": []})
        self.mocks["check_relevance"].assert_not_called()

    def test_relevant_input_keeps_case(self):
        self.script_ai([REPLY_NON_URGENT])
        lm.process_interaction("My headache is worse", chat=object(), active_case=self.case)
        self.mocks["check_relevance"].assert_called_once()
        self.mocks["close_case"].assert_not_called()
        self.mocks["create_new_case"].assert_not_called()

    def test_unrelated_and_user_says_not_related_starts_new_case(self):
        self.script_ai([REPLY_NON_URGENT])
        self.mocks["check_relevance"].return_value = False
        self.mocks["ask_yes_no"].return_value = False

        lm.process_interaction("My ankle hurts", chat=object(), active_case=self.case)

        self.mocks["close_case"].assert_called_once_with(self.case)
        self.mocks["create_new_case"].assert_called_once()
        self.mocks["create_chat"].assert_called_once_with(self.new_case)
        self.mocks["add_log"].assert_called_once_with(self.new_case, "My ankle hurts", "")

    def test_unrelated_but_user_says_related_continues_case(self):
        self.script_ai([REPLY_NON_URGENT])
        self.mocks["check_relevance"].return_value = False
        self.mocks["ask_yes_no"].return_value = True

        lm.process_interaction("My ankle hurts", chat=object(), active_case=self.case)

        self.mocks["close_case"].assert_not_called()
        self.mocks["create_new_case"].assert_not_called()
        self.assertIn("Continuing with case_001.json", self.printed())

    def test_falls_back_to_get_active_case(self):
        self.script_ai([REPLY_NON_URGENT])
        self.mocks["get_active_case"].return_value = self.case
        lm.process_interaction("My headache is worse", chat=object())
        self.mocks["check_relevance"].assert_called_once()


# ---------------------------------------------------------------------------
# menu_selection
# ---------------------------------------------------------------------------
class TestMenuSelection(LogicManagerTestCase):
    def setUp(self):
        super().setUp()
        self.case = {"case_id": "case_001", "logs": []}
        self.chat = object()

    def test_option_1_runs_assessment_and_logs(self):
        self.mocks["input_manager"].return_value = {"age": 40, "symptoms": "headache"}
        self.mocks["create_prompt"].return_value = "I have a bad headache"
        self.script_ai([REPLY_NON_URGENT])

        case, chat, should_exit = lm.menu_selection("1", self.case, self.chat)

        self.assertIs(case, self.case)
        self.assertIs(chat, self.chat)
        self.assertFalse(should_exit)
        self.mocks["add_log"].assert_called_once_with(
            self.case, "I have a bad headache", REPLY_NON_URGENT
        )
        out = self.printed()
        self.assertIn("=== Assessment Result ===", out)
        self.assertIn("Age Risk: Not high risk age group", out)
        self.assertIn(REPLY_NON_URGENT, out)

    def test_option_1_logs_every_follow_up_exchange(self):
        self.mocks["input_manager"].return_value = {"age": 40}
        self.mocks["create_prompt"].return_value = "I have a fever"
        self.mocks["get_additional_input"].return_value = "three days"
        self.script_ai([REPLY_FOLLOW_UP, REPLY_NON_URGENT])

        lm.menu_selection("1", self.case, self.chat)

        self.assertEqual(self.mocks["add_log"].call_count, 2)

    def test_option_1_ai_failure_logs_nothing(self):
        self.mocks["input_manager"].return_value = {"age": 40}
        self.mocks["create_prompt"].return_value = "I have a fever"
        self.script_ai([None])

        _, _, should_exit = lm.menu_selection("1", self.case, self.chat)

        self.assertFalse(should_exit)
        self.mocks["add_log"].assert_not_called()
        self.assertIn("Unable to complete the assessment", self.printed())

    def test_option_1_non_dict_patient_data(self):
        self.mocks["input_manager"].return_value = "free text"
        self.mocks["create_prompt"].return_value = "I have a fever"
        self.script_ai([REPLY_NON_URGENT])

        lm.menu_selection("1", self.case, self.chat)  # must not raise

        self.mocks["add_log"].assert_called_once()

    def test_option_2_prints_cases(self):
        result = lm.menu_selection("2", self.case, self.chat)
        self.mocks["print_cases"].assert_called_once()
        self.assertEqual(result, (self.case, self.chat, False))

    def test_option_3_no_results(self):
        self.mocks["keyword_input"].return_value = "fever"
        self.mocks["filter_records_by_keyword"].return_value = []

        result = lm.menu_selection("3", self.case, self.chat)

        self.assertEqual(result, (self.case, self.chat, False))
        self.mocks["show_history"].assert_not_called()
        self.assertIn("No matching records found for 'fever'", self.printed())

    def test_option_3_with_results(self):
        records = [{"case_id": "case_001"}]
        self.mocks["keyword_input"].return_value = "fever"
        self.mocks["filter_records_by_keyword"].return_value = records

        lm.menu_selection("3", self.case, self.chat)

        self.mocks["show_history"].assert_called_once_with(records)

    def test_option_4_converts_to_csv(self):
        result = lm.menu_selection("4", self.case, self.chat)
        self.mocks["convert_json_to_csv"].assert_called_once()
        self.assertEqual(result, (self.case, self.chat, False))

    def test_option_5_returns_normally_when_conversion_fails(self):
        self.mocks["convert_json_to_xlsx"].return_value = False
        result = lm.menu_selection("5", self.case, self.chat)
        self.mocks["convert_json_to_xlsx"].assert_called_once()
        self.assertEqual(result, (self.case, self.chat, False))

    def test_option_6_exits(self):
        result = lm.menu_selection("6", self.case, self.chat)
        self.assertEqual(result, (self.case, self.chat, True))

    def test_invalid_option(self):
        result = lm.menu_selection("99", self.case, self.chat)
        self.assertEqual(result, (self.case, self.chat, False))
        self.assertIn("Invalid menu option.", self.printed())


if __name__ == "__main__":
    unittest.main(verbosity=2)