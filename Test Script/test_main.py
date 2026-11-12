
"""
Offline tests for main.py

- Tests the application's startup, menu loop, shutdown, and error handling.
- Uses unittest.mock to simulate other modules without making real AI calls
  or creating actual case files.

Test cases:
- MAIN-01: Checks startup when an active case already exists.
- MAIN-02: Checks that a new case is created when none exists.
- MAIN-03: Checks that an initialisation error is handled safely.
- MAIN-04: Checks that selecting Quit closes the active case.
- MAIN-05: Checks that KeyboardInterrupt closes the case and exits.
- MAIN-06: Checks that EOFError closes the case and exits.
- MAIN-07: Checks that unexpected errors return to the menu.
- MAIN-08: Checks that starting a new case closes the previous case.

Run:
    python -m unittest -v test_main
"""

import unittest
from unittest.mock import patch

import main


class TestMain(unittest.TestCase):

    def setUp(self):
        self.case = {
            "case_id": "CASE001",
            "logs": []
        }

    @patch("main.create_chat")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_startup_with_existing_case(
        self, mock_print, mock_welcome,
        mock_get_active, mock_create_chat
    ):
        """MAIN-01: Startup uses the existing active case."""
        mock_get_active.return_value = self.case
        mock_create_chat.return_value = "mock_chat"

        with patch("main.get_menu_input", return_value="quit"), \
             patch("main.menu_selection",
                   return_value=(self.case, "mock_chat", True)), \
             patch("main.close_case") as mock_close:
            main.main()

        mock_welcome.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)
        mock_close.assert_called_once_with(self.case)

    @patch("main.create_chat")
    @patch("main.create_new_case")
    @patch("main.get_active_case", return_value=None)
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_startup_without_active_case(
        self, mock_print, mock_welcome,
        mock_get_active, mock_new_case, mock_create_chat
    ):
        """MAIN-02: A new case is created if none exists."""
        mock_new_case.return_value = self.case
        mock_create_chat.return_value = "mock_chat"

        with patch("main.get_menu_input", return_value="quit"), \
             patch("main.menu_selection",
                   return_value=(self.case, "mock_chat", True)), \
             patch("main.close_case"):
            main.main()

        mock_new_case.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)

    @patch("main.get_active_case", side_effect=RuntimeError("Initialisation failed"))
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_initialisation_error(
        self, mock_print, mock_welcome, mock_get_active
    ):
        """MAIN-03: Startup errors are reported without crashing."""
        main.main()

        self.assertTrue(
            any(
                "[Fatal Error]" in str(call)
                for call in mock_print.call_args_list
            )
        )

    @patch("main.create_chat", return_value="mock_chat")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_quit_closes_active_case(
        self, mock_print, mock_welcome,
        mock_get_active, mock_create_chat
    ):
        """MAIN-04: Choosing Quit closes the active case."""
        mock_get_active.return_value = self.case

        with patch("main.get_menu_input", return_value="quit"), \
             patch("main.menu_selection",
                   return_value=(self.case, "mock_chat", True)), \
             patch("main.close_case") as mock_close:
            main.main()

        mock_close.assert_called_once_with(self.case)

    @patch("main.create_chat", return_value="mock_chat")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_keyboard_interrupt(
        self, mock_print, mock_welcome,
        mock_get_active, mock_create_chat
    ):
        """MAIN-05: Ctrl+C closes the case and exits."""
        mock_get_active.return_value = self.case

        with patch("main.get_menu_input", side_effect=KeyboardInterrupt), \
             patch("main.close_case") as mock_close:
            main.main()

        mock_close.assert_called_once_with(self.case)

    @patch("main.create_chat", return_value="mock_chat")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_eof_error(
        self, mock_print, mock_welcome,
        mock_get_active, mock_create_chat
    ):
        """MAIN-06: Closed input stream closes the case."""
        mock_get_active.return_value = self.case

        with patch("main.get_menu_input", side_effect=EOFError), \
             patch("main.close_case") as mock_close:
            main.main()

        mock_close.assert_called_once_with(self.case)

    @patch("main.create_chat", return_value="mock_chat")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_unexpected_error_returns_to_menu(
        self, mock_print, mock_welcome,
        mock_get_active, mock_create_chat
    ):
        """MAIN-07: Unexpected errors are handled and the loop continues."""
        mock_get_active.return_value = self.case

        with patch(
            "main.get_menu_input",
            side_effect=["invalid", "quit"]
        ), patch(
            "main.menu_selection",
            side_effect=[
                ValueError("Test error"),
                (self.case, "mock_chat", True)
            ]
        ), patch("main.close_case"):
            with patch("builtins.print") as mock_builtin_print:
                main.main()

        self.assertTrue(
            any(
                "unexpected error" in str(call).lower()
                for call in mock_builtin_print.call_args_list
            )
        )

    @patch("main.create_chat", return_value="mock_chat")
    @patch("main.create_new_case")
    @patch("main.close_case")
    @patch("main.print_output")
    def test_start_new_case(
        self, mock_print, mock_close,
        mock_new_case, mock_create_chat
    ):
        """MAIN-08: Starting a new case closes the previous case."""
        mock_new_case.return_value = {
            "case_id": "CASE002",
            "logs": []
        }

        new_case, chat = main.start_new_case(self.case)

        mock_close.assert_called_once_with(self.case)
        mock_new_case.assert_called_once()
        mock_create_chat.assert_called_once_with(new_case)
        self.assertEqual(new_case["case_id"], "CASE002")
        self.assertEqual(chat, "mock_chat")


if __name__ == "__main__":
    unittest.main()
