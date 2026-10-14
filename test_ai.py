"""
Offline tests for ai_manager.py

- No live AI / network calls: Gemini responses and API failures are
  simulated using unittest.mock, so tests do not consume API credits.
- Tests cover client creation, chat history preparation, chat creation,
  AI responses, invalid input, API failures, and case relevance checks.
- Uses unittest and unittest.mock from the Python standard library.
  The ai_manager module and its dependencies must still be importable.
- No valid Gemini API key is required to run the tests because the
  Gemini client and API calls are mocked where needed.

Run:
    python -m unittest -v test_ai

Test cases:
- AI-01: Checks that a Gemini client is created when an API key exists.
- AI-02: Checks that a missing API key raises a RuntimeError.
- AI-03: Checks that saved conversation logs are converted into chat history.
- AI-04: Checks that a chat is created with the existing case history.
- AI-05: Checks that a new chat is created with empty history.
- AI-06: Checks that valid user input returns the AI response.
"""

import unittest
from unittest.mock import Mock, patch
import ai_manager


class TestAIManager(unittest.TestCase):
    # AI-01: Client is created when the API key exists
    @patch("ai_manager.genai.Client")
    @patch.dict("os.environ", {"GENAI_API_KEY": "test-key"})
    def test_get_client_success(self, mock_client):
        result = ai_manager.get_client()

        mock_client.assert_called_once_with(api_key="test-key")
        self.assertIs(result, mock_client.return_value)

    # AI-02: Missing API key raises RuntimeError
    @patch.dict("os.environ", {}, clear=True)
    def test_get_client_missing_key(self):
        with self.assertRaises(RuntimeError):
            ai_manager.get_client()

    # AI-03: Conversation history is converted correctly
    def test_prepare_chat_history(self):
        logs = [
            {
                "user_input": "I have a headache",
                "ai_response": "How long have you had it?"
            },
            {
                "user_input": "For two days",
                "ai_response": "Do you have other symptoms?"
            }
        ]

        history = ai_manager.prepare_chat_history(logs)

        self.assertEqual(len(history), 4)
        self.assertEqual(history[0].role, "user")
        self.assertEqual(history[1].role, "model")
        self.assertEqual(history[2].role, "user")
        self.assertEqual(history[3].role, "model")

    
    # AI-04: Existing case history is used to create a chat
    @patch("ai_manager.client")
    def test_create_chat_with_case(self, mock_client):
        case = {
            "logs": [
                {
                    "user_input": "I have a headache",
                    "ai_response": "How long?"
                }
            ]
        }

        ai_manager.create_chat(case)

        mock_client.chats.create.assert_called_once()
        kwargs = mock_client.chats.create.call_args.kwargs

        self.assertEqual(kwargs["model"], ai_manager.CHAT_MODEL)
        self.assertEqual(len(kwargs["history"]), 2)


    # AI-05: New chat starts with empty history
    @patch("ai_manager.client")
    def test_create_chat_without_case(self, mock_client):
        ai_manager.create_chat()
        mock_client.chats.create.assert_called_once()
        kwargs = mock_client.chats.create.call_args.kwargs

        self.assertEqual(kwargs["model"], ai_manager.CHAT_MODEL)
        self.assertEqual(kwargs["history"], [])

    # AI-06: Valid input returns AI response text
    @patch("ai_manager.print_output")
    def test_ask_ai_success(self, mock_output):
        chat = Mock()
        chat.send_message.return_value.text = "Please describe your symptoms."

        result = ai_manager.ask_ai(chat, "I have a headache")

        self.assertEqual(result, "Please describe your symptoms.")
        chat.send_message.assert_called_once_with(message="I have a headache")

    # AI-07: Missing chat is handled
    @patch("ai_manager.print_output")
    def test_ask_ai_without_chat(self, mock_output):
        result = ai_manager.ask_ai(None, "I have a headache")

        self.assertIsNone(result)
        mock_output.assert_called()

    # AI-08: Empty input is rejected without calling the AI
    @patch("ai_manager.print_output")
    def test_ask_ai_empty_input(self, mock_output):
        chat = Mock()

        result = ai_manager.ask_ai(chat, "   ")

        self.assertIsNone(result)
        chat.send_message.assert_not_called()
        mock_output.assert_called()

    # AI-09: Empty AI response is handled
    @patch("ai_manager.print_output")
    def test_ask_ai_empty_response(self, mock_output):
        chat = Mock()
        chat.send_message.return_value.text = ""

        result = ai_manager.ask_ai(chat, "I have a headache")

        self.assertIsNone(result)
        mock_output.assert_called()

    # AI-10: API exception is caught
    @patch("ai_manager.print_output")
    def test_ask_ai_api_failure(self, mock_output):
        chat = Mock()
        chat.send_message.side_effect = Exception("API unavailable")

        result = ai_manager.ask_ai(chat, "I have a headache")

        self.assertIsNone(result)
        mock_output.assert_called()

    # AI-11: Related response returns True
    @patch("ai_manager.get_client")
    def test_check_relevance_yes(self, mock_get_client):
        mock_get_client.return_value.models.generate_content.return_value.text = "YES"

        case = {
            "logs": [
                {
                    "user_input": "I have a headache",
                    "ai_response": "How long?"
                }
            ]
        }

        result = ai_manager.check_relevance(
            "It started yesterday", case
        )

        self.assertTrue(result)

    # AI-12: Unrelated response returns False
    @patch("ai_manager.get_client")
    def test_check_relevance_no(self, mock_get_client):
        mock_get_client.return_value.models.generate_content.return_value.text = "NO"

        case = {
            "logs": [
                {
                    "user_input": "I have a headache",
                    "ai_response": "How long?"
                }
            ]
        }

        result = ai_manager.check_relevance(
            "I cut my finger", case
        )

        self.assertFalse(result)

    # AI-13: Relevance-check failure defaults to True
    @patch("ai_manager.print_output")
    @patch("ai_manager.get_client")
    def test_check_relevance_failure(
        self, mock_get_client, mock_output
    ):
        mock_get_client.side_effect = Exception("API unavailable")

        case = {
            "logs": [
                {
                    "user_input": "I have a headache",
                    "ai_response": "How long?"
                }
            ]
        }

        result = ai_manager.check_relevance(
            "It started yesterday", case
        )

        self.assertTrue(result)
        mock_output.assert_called()

    # AI-14: Empty case history skips the relevance check
    @patch("ai_manager.get_client")
    def test_check_relevance_empty_logs(self, mock_get_client):
        result = ai_manager.check_relevance(
            "I have a headache",
            {"logs": []}
        )

        self.assertTrue(result)
        mock_get_client.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
