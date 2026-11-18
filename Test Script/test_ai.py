import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

# Allow this test file to be run from the repository root:
# python -m unittest discover -s "Test Script" -p "test_ai.py" -v
PROJECT_CODE = Path(__file__).resolve().parents[1] / "Project Code"
if str(PROJECT_CODE) not in sys.path:
    sys.path.insert(0, str(PROJECT_CODE))

from AI.ai_manager import AIManager
from AI.response_validator import ResponseValidator


def valid_assessment(
    urgency="non-urgent",
    certainty=95,
    follow_up="",
    guidance="Arrange a visit with a healthcare professional."
):
    """Build a valid assessment response for tests."""
    return json.dumps({
        "urgency_classification": urgency,
        "certainty": certainty,
        "follow_up_question": follow_up,
        "next_step_guidance": guidance
    })


class TestResponseValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ResponseValidator()

    def test_valid_high_certainty_response(self):
        result = self.validator.validate(valid_assessment())
        self.assertEqual(result["urgency_classification"], "non-urgent")
        self.assertEqual(result["certainty"], 95)

    def test_valid_low_certainty_response(self):
        raw = valid_assessment(
            urgency="insufficient_information",
            certainty=70,
            follow_up="How long have you had these symptoms?",
            guidance="Not yet - more information needed"
        )
        result = self.validator.validate(raw)
        self.assertEqual(
            result["urgency_classification"],
            "insufficient_information"
        )


    def test_accepts_emergency_classification(self):
        raw = valid_assessment(
            urgency="emergency",
            certainty=95,
            guidance="Seek emergency medical help immediately."
        )
        result = self.validator.validate(raw)
        self.assertEqual(result["urgency_classification"], "emergency")

    def test_accepts_urgent_classification(self):
        raw = valid_assessment(
            urgency="urgent",
            certainty=96,
            guidance="Seek urgent medical assessment."
        )
        result = self.validator.validate(raw)
        self.assertEqual(result["urgency_classification"], "urgent")

    def test_accepts_certainty_at_exactly_95(self):
        result = self.validator.validate(valid_assessment(certainty=95))
        self.assertEqual(result["certainty"], 95)

    def test_accepts_certainty_at_100(self):
        result = self.validator.validate(valid_assessment(certainty=100))
        self.assertEqual(result["certainty"], 100)

    def test_rejects_certainty_just_below_95_with_final_classification(self):
        raw = valid_assessment(
            urgency="non-urgent",
            certainty=94.99,
            follow_up="What other symptoms do you have?",
            guidance="Not yet - more information needed"
        )
        with self.assertRaisesRegex(ValueError, "below 95"):
            self.validator.validate(raw)

    def test_accepts_decimal_certainty_below_95_with_follow_up(self):
        raw = valid_assessment(
            urgency="insufficient_information",
            certainty=94.99,
            follow_up="When did the symptoms begin?",
            guidance="Not yet - more information needed"
        )
        result = self.validator.validate(raw)
        self.assertEqual(result["certainty"], 94.99)

    def test_allows_additional_json_fields(self):
        data = json.loads(valid_assessment())
        data["additional_note"] = "Extra fields are currently permitted."
        result = self.validator.validate(json.dumps(data))
        self.assertEqual(
            result["additional_note"],
            "Extra fields are currently permitted."
        )
    def test_accepts_json_inside_markdown_code_fence(self):
        raw = "```json\n" + valid_assessment() + "\n```"
        result = self.validator.validate(raw)
        self.assertEqual(result["certainty"], 95)

    def test_rejects_empty_response(self):
        for raw in ("", "   ", None, 123):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    self.validator.validate(raw)

    def test_rejects_malformed_json(self):
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            self.validator.validate('{"urgency_classification": ')

    def test_rejects_json_that_is_not_an_object(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            self.validator.validate('["not", "an", "object"]')

    def test_rejects_missing_required_field(self):
        data = json.loads(valid_assessment())
        del data["certainty"]
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            self.validator.validate(json.dumps(data))

    def test_rejects_invalid_urgency_classification(self):
        raw = valid_assessment(urgency="moderate")
        with self.assertRaisesRegex(ValueError, "Invalid urgency"):
            self.validator.validate(raw)

    def test_rejects_certainty_outside_range(self):
        for certainty in (-1, 101):
            with self.subTest(certainty=certainty):
                raw = valid_assessment(certainty=certainty)
                with self.assertRaisesRegex(ValueError, "Certainty"):
                    self.validator.validate(raw)

    def test_rejects_boolean_certainty(self):
        data = json.loads(valid_assessment())
        data["certainty"] = True
        with self.assertRaisesRegex(ValueError, "Certainty"):
            self.validator.validate(json.dumps(data))

    def test_rejects_non_numeric_certainty(self):
        data = json.loads(valid_assessment())
        data["certainty"] = "95"
        with self.assertRaisesRegex(ValueError, "Certainty"):
            self.validator.validate(json.dumps(data))

    def test_rejects_non_string_text_fields(self):
        data = json.loads(valid_assessment())
        data["follow_up_question"] = None
        with self.assertRaisesRegex(ValueError, "Follow-up question"):
            self.validator.validate(json.dumps(data))

        data = json.loads(valid_assessment())
        data["next_step_guidance"] = 123
        with self.assertRaisesRegex(ValueError, "Next-step guidance"):
            self.validator.validate(json.dumps(data))

    def test_below_95_requires_insufficient_information(self):
        raw = valid_assessment(
            urgency="urgent",
            certainty=94,
            follow_up="What other symptoms do you have?",
            guidance="Not yet - more information needed"
        )
        with self.assertRaisesRegex(ValueError, "below 95"):
            self.validator.validate(raw)

    def test_below_95_requires_follow_up_question(self):
        raw = valid_assessment(
            urgency="insufficient_information",
            certainty=94,
            follow_up=" ",
            guidance="Not yet - more information needed"
        )
        with self.assertRaisesRegex(ValueError, "follow-up question"):
            self.validator.validate(raw)

    def test_below_95_rejects_guidance(self):
        raw = valid_assessment(
            urgency="insufficient_information",
            certainty=94,
            follow_up="What other symptoms do you have?",
            guidance="Take some medicine."
        )
        with self.assertRaisesRegex(ValueError, "Guidance"):
            self.validator.validate(raw)

    def test_95_or_above_rejects_insufficient_information(self):
        raw = valid_assessment(
            urgency="insufficient_information",
            certainty=95,
            follow_up="",
            guidance="Seek medical advice."
        )
        with self.assertRaisesRegex(ValueError, "final urgency"):
            self.validator.validate(raw)

    def test_95_or_above_rejects_follow_up_question(self):
        raw = valid_assessment(
            certainty=95,
            follow_up="Are you experiencing anything else?"
        )
        with self.assertRaisesRegex(ValueError, "Follow-up question"):
            self.validator.validate(raw)

    def test_95_or_above_requires_guidance(self):
        raw = valid_assessment(certainty=95, guidance=" ")
        with self.assertRaisesRegex(ValueError, "Next-step guidance"):
            self.validator.validate(raw)


class TestAIManager(unittest.TestCase):
    def setUp(self):
        # Inject a mock provider so tests never create a Gemini client
        # or make a live API request.
        self.provider = Mock()
        self.manager = AIManager(provider=self.provider)

    def test_prepare_chat_history_converts_user_and_ai_logs(self):
        logs = [
            {
                "user_input": "I have a headache.",
                "ai_response": "When did it start?"
            }
        ]

        history = self.manager.prepare_chat_history(logs)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].role, "user")
        self.assertEqual(history[0].parts[0].text, "I have a headache.")
        self.assertEqual(history[1].role, "model")
        self.assertEqual(history[1].parts[0].text, "When did it start?")


    def test_prepare_chat_history_handles_logs_with_missing_fields(self):
        history = self.manager.prepare_chat_history([
            {},
            {"user_input": "I have a cough."},
            {"ai_response": "How long have you had it?"}
        ])
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].role, "user")
        self.assertEqual(history[1].role, "model")

    def test_assess_rejects_provider_response_with_no_text(self):
        self.provider.send_message.return_value = None
        with self.assertRaisesRegex(ValueError, "empty response"):
            self.manager.assess(object(), "I have a headache.")

    def test_check_relevance_handles_logs_with_missing_fields(self):
        self.provider.generate_text.return_value = "YES"
        result = self.manager.check_relevance(
            "The pain is worse.",
            {"logs": [{}, {"user_input": "I have a headache."}]}
        )
        self.assertTrue(result)
        prompt = self.provider.generate_text.call_args.args[0]
        self.assertIn("I have a headache.", prompt)

    def test_check_relevance_handles_ai_only_logs(self):
        self.provider.generate_text.return_value = "YES"
        result = self.manager.check_relevance(
            "I have another symptom.",
            {"logs": [{"ai_response": "When did it begin?"}]}
        )
        self.assertTrue(result)
        prompt = self.provider.generate_text.call_args.args[0]
        self.assertIn("When did it begin?", prompt)
    def test_prepare_chat_history_handles_empty_logs(self):
        self.assertEqual(self.manager.prepare_chat_history([]), [])

    def test_prepare_chat_history_skips_empty_entries(self):
        history = self.manager.prepare_chat_history([
            {"user_input": "", "ai_response": "An earlier response."}
        ])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].role, "model")

    def test_create_chat_passes_instruction_and_history_to_provider(self):
        case = {
            "logs": [{
                "user_input": "My throat hurts.",
                "ai_response": "How long has it hurt?"
            }]
        }
        expected_chat = object()
        self.provider.create_chat.return_value = expected_chat

        result = self.manager.create_chat(case)

        self.assertIs(result, expected_chat)
        self.provider.create_chat.assert_called_once()
        args = self.provider.create_chat.call_args.args
        self.assertIn("healthcare symptom assessment assistant", args[0])
        self.assertEqual(len(args[1]), 2)

    def test_create_chat_without_case_uses_empty_history(self):
        self.manager.create_chat()
        args = self.provider.create_chat.call_args.args
        self.assertEqual(args[1], [])

    def test_build_prompt_returns_user_input(self):
        prompt = "I have a cough."
        self.assertEqual(self.manager.build_prompt(prompt), prompt)

    def test_assess_sends_message_and_validates_response(self):
        chat = object()
        raw = valid_assessment()
        self.provider.send_message.return_value = raw

        result = self.manager.assess(chat, "I have a mild headache.")

        self.provider.send_message.assert_called_once_with(
            chat, "I have a mild headache."
        )
        self.assertEqual(result["urgency_classification"], "non-urgent")

    def test_assess_rejects_missing_chat(self):
        with self.assertRaisesRegex(ValueError, "chat is not available"):
            self.manager.assess(None, "I have a headache.")

    def test_assess_rejects_empty_or_non_string_input(self):
        for user_input in ("", "   ", None, 123):
            with self.subTest(user_input=user_input):
                with self.assertRaisesRegex(ValueError, "empty message"):
                    self.manager.assess(object(), user_input)

    def test_assess_rejects_invalid_provider_response(self):
        self.provider.send_message.return_value = "not valid JSON"
        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            self.manager.assess(object(), "I have a headache.")

    def test_format_assessment_formats_all_fields(self):
        data = {
            "urgency_classification": "urgent",
            "certainty": 98,
            "follow_up_question": "",
            "next_step_guidance": "Seek medical attention."
        }

        result = self.manager.format_assessment(data)

        self.assertIn("Urgency classification: urgent", result)
        self.assertIn("Certainty: 98%", result)
        self.assertIn("Follow-Up Questions:\nNone", result)
        self.assertIn("Seek medical attention.", result)

    def test_format_assessment_uses_defaults_for_empty_text(self):
        data = {
            "urgency_classification": "non-urgent",
            "certainty": 95,
            "follow_up_question": "",
            "next_step_guidance": ""
        }
        result = self.manager.format_assessment(data)
        self.assertIn("None", result)
        self.assertIn("Not yet - more information needed", result)

    def test_ask_ai_returns_formatted_assessment(self):
        self.provider.send_message.return_value = valid_assessment()

        result = self.manager.ask_ai(object(), "I have a mild headache.")

        self.assertIsInstance(result, str)
        self.assertIn("Urgency classification: non-urgent", result)

    def test_ask_ai_returns_none_when_assessment_fails(self):
        self.provider.send_message.return_value = "invalid JSON"

        result = self.manager.ask_ai(object(), "I have a headache.")

        self.assertIsNone(result)

    def test_check_relevance_returns_true_without_active_case(self):
        self.assertTrue(self.manager.check_relevance("New symptoms", None))
        self.provider.generate_text.assert_not_called()

    def test_check_relevance_returns_true_for_case_without_logs(self):
        self.assertTrue(
            self.manager.check_relevance("New symptoms", {"logs": []})
        )
        self.provider.generate_text.assert_not_called()

    def test_check_relevance_accepts_yes(self):
        self.provider.generate_text.return_value = "YES"

        result = self.manager.check_relevance(
            "The pain is getting worse.",
            {"logs": [{"user_input": "I have a headache."}]}
        )

        self.assertTrue(result)
        self.provider.generate_text.assert_called_once()
        prompt = self.provider.generate_text.call_args.args[0]
        self.assertIn("I have a headache.", prompt)
        self.assertIn("The pain is getting worse.", prompt)

    def test_check_relevance_rejects_no(self):
        self.provider.generate_text.return_value = "NO"

        result = self.manager.check_relevance(
            "I have a completely different problem.",
            {"logs": [{"user_input": "I have a headache."}]}
        )

        self.assertFalse(result)

    def test_check_relevance_accepts_case_and_whitespace_variations(self):
        self.provider.generate_text.return_value = " yes \n"
        self.assertTrue(
            self.manager.check_relevance(
                "More details",
                {"logs": [{"user_input": "Original issue"}]}
            )
        )

    def test_check_relevance_defaults_to_true_for_invalid_response(self):
        self.provider.generate_text.return_value = "MAYBE"

        result = self.manager.check_relevance(
            "A new message",
            {"logs": [{"user_input": "Original issue"}]}
        )

        self.assertTrue(result)

    def test_check_relevance_defaults_to_true_for_empty_response(self):
        self.provider.generate_text.return_value = " "

        result = self.manager.check_relevance(
            "A new message",
            {"logs": [{"user_input": "Original issue"}]}
        )

        self.assertTrue(result)

    def test_check_relevance_defaults_to_true_when_provider_fails(self):
        self.provider.generate_text.side_effect = RuntimeError("API error")

        result = self.manager.check_relevance(
            "A new message",
            {"logs": [{"user_input": "Original issue"}]}
        )

        self.assertTrue(result)

    def test_check_relevance_uses_only_the_last_five_logs(self):
        logs = [
            {"user_input": f"Old message {i}"}
            for i in range(7)
        ]
        self.provider.generate_text.return_value = "YES"

        self.manager.check_relevance("Latest message", {"logs": logs})

        prompt = self.provider.generate_text.call_args.args[0]
        self.assertNotIn("Old message 0", prompt)
        self.assertNotIn("Old message 1", prompt)
        self.assertIn("Old message 2", prompt)
        self.assertIn("Old message 6", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
