
"""
Offline tests for main.py

- Tests application startup, menu navigation, shutdown, and error handling.
- Uses unittest.mock to simulate dependencies without real AI calls or
  actual case-file creation.

Test cases:
- MAIN-01: Checks startup with an existing active case.
- MAIN-02: Checks creation of a new case when none exists.
- MAIN-03: Checks handling of initialisation errors.
- MAIN-04: Checks that quitting closes the active case.
- MAIN-05: Checks that KeyboardInterrupt closes the case.
- MAIN-06: Checks that EOFError closes the case.
- MAIN-07: Checks that unexpected errors return to the menu.
- MAIN-08: Checks that starting a new case closes the previous case.

Run:
    py -m unittest -v test_main
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
        mock_get_active.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)
        mock_print.assert_any_call(
            "[System] Active case: CASE001.json (0 saved entries)\n"
        )
        mock_close.assert_called_once_with(self.case)

    @patch("main.create_chat")
    @patch("main.create_new_case")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_startup_without_active_case(
        self, mock_print, mock_welcome,
        mock_get_active, mock_new_case, mock_create_chat
    ):
        """MAIN-02: Creates a case if no active case exists."""
        mock_get_active.return_value = None
        mock_new_case.return_value = self.case
        mock_create_chat.return_value = "mock_chat"

        with patch("main.get_menu_input", return_value="quit"), \
             patch("main.menu_selection",
                   return_value=(self.case, "mock_chat", True)), \
             patch("main.close_case") as mock_close:
            main.main()

        mock_welcome.assert_called_once()
        mock_get_active.assert_called_once()
        mock_new_case.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)
        mock_print.assert_any_call(
            "[System] Created active case: CASE001.json"
        )
        mock_close.assert_called_once_with(self.case)

    @patch("main.get_active_case",
           side_effect=RuntimeError("Initialisation failed"))
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_initialisation_error(
        self, mock_print, mock_welcome, mock_get_active
    ):
        """MAIN-03: Startup errors are reported safely."""
        main.main()

        mock_welcome.assert_called_once()
        mock_get_active.assert_called_once()
        mock_print.assert_any_call(
            "[Fatal Error] Could not initialise "
            "the application: Initialisation failed"
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

        mock_welcome.assert_called_once()
        mock_get_active.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)
        mock_close.assert_called_once_with(self.case)
        mock_print.assert_any_call(
            "\n[System] Closed CASE001.json."
        )
        mock_print.assert_any_call(
            "Exiting application. Stay healthy!"
        )

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

        with patch("main.get_menu_input",
                   side_effect=KeyboardInterrupt), \
             patch("main.close_case") as mock_close:
            main.main()

        mock_welcome.assert_called_once()
        mock_get_active.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)
        mock_close.assert_called_once_with(self.case)
        mock_print.assert_any_call(
            "\n\nExiting application. Stay healthy!"
        )

    @patch("main.create_chat", return_value="mock_chat")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_eof_error(
        self, mock_print, mock_welcome,
        mock_get_active, mock_create_chat
    ):
        """MAIN-06: EOFError closes the case and exits."""
        mock_get_active.return_value = self.case

        with patch("main.get_menu_input", side_effect=EOFError), \
             patch("main.close_case") as mock_close:
            main.main()

        mock_welcome.assert_called_once()
        mock_get_active.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)
        mock_close.assert_called_once_with(self.case)
        mock_print.assert_any_call(
            "\n\nInput stream closed. Exiting application."
        )

    @patch("main.create_chat", return_value="mock_chat")
    @patch("main.get_active_case")
    @patch("main.welcome_message")
    @patch("main.print_output")
    def test_unexpected_error_returns_to_menu(
        self, mock_print, mock_welcome,
        mock_get_active, mock_create_chat
    ):
        """MAIN-07: Unexpected errors are caught and the loop continues."""
        mock_get_active.return_value = self.case

        with patch(
            "main.get_menu_input",
            side_effect=["invalid", "quit"]
        ) as mock_input, patch(
            "main.menu_selection",
            side_effect=[
                ValueError("Test error"),
                (self.case, "mock_chat", True)
            ]
        ) as mock_menu, patch(
            "main.close_case"
        ) as mock_close, patch(
            "builtins.print"
        ) as mock_builtin_print:
            main.main()

        mock_welcome.assert_called_once()
        mock_get_active.assert_called_once()
        mock_create_chat.assert_called_once_with(self.case)
        self.assertEqual(mock_input.call_count, 2)
        self.assertEqual(mock_menu.call_count, 2)
        mock_close.assert_called_once_with(self.case)
        mock_builtin_print.assert_any_call(
            "\n[Error] An unexpected error occurred: "
            "ValueError: Test error"
        )
        mock_builtin_print.assert_any_call(
            "The application will return to the main menu."
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
        new_case = {
            "case_id": "CASE002",
            "logs": []
        }
        mock_new_case.return_value = new_case

        result_case, result_chat = main.start_new_case(self.case)

        mock_close.assert_called_once_with(self.case)
        mock_new_case.assert_called_once()
        mock_create_chat.assert_called_once_with(new_case)
        mock_print.assert_any_call(
            "[System] Closed CASE001.json."
        )
        mock_print.assert_any_call(
            "[System] Created new active case: CASE002.json\n"
        )
        self.assertEqual(result_case, new_case)
        self.assertEqual(result_chat, "mock_chat")


if __name__ == "__main__":
    unittest.main()
