import importlib
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

# This test file is stored outside Project Code.
# Add Project Code so its application modules can be imported.
PROJECT_CODE = Path(__file__).resolve().parents[1] / "Project Code"
if str(PROJECT_CODE) not in sys.path:
    sys.path.insert(0, str(PROJECT_CODE))

# main.py creates AIManager() when it is imported. Replace that class before
# importing main so tests never need a Gemini API key or a live API connection.
from AI import ai_manager as ai_manager_module

with patch.object(ai_manager_module, "AIManager", return_value=Mock()):
    main_module = importlib.import_module("main")


class TestMainApplication(unittest.TestCase):

    def setUp(self):
        self.user = {
            "user_id": "test-user-001",
            "email": "patient@example.com"
        }
        self.case = SimpleNamespace(
            case_id="case_test_001",
            logs=[]
        )
        self.chat = Mock()

        # Replace external/application dependencies for each test.
        self.patches = [
            patch.object(main_module, "authenticate", return_value=self.user),
            patch.object(main_module, "set_current_user"),
            patch.object(main_module, "welcome_message"),
            patch.object(main_module, "get_active_case", return_value=self.case),
            patch.object(main_module, "get_backend_name", return_value="test"),
            patch.object(main_module, "create_new_case", return_value=self.case),
            patch.object(main_module, "close_case"),
            patch.object(main_module, "get_menu_input", return_value=1),
            patch.object(
                main_module,
                "print_output"
            ),
            patch.object(
                main_module,
                "ai_manager",
                Mock()
            ),
            patch.object(
                main_module,
                "menu_selection",
                return_value=(self.case, self.chat, True)
            )
        ]

        self.mocks = [p.start() for p in self.patches]
        self.addCleanup(self.stop_patches)

        (
            self.authenticate,
            self.set_current_user,
            self.welcome_message,
            self.get_active_case,
            self.get_backend_name,
            self.create_new_case,
            self.close_case,
            self.get_menu_input,
            self.print_output,
            self.ai_manager,
            self.menu_selection
        ) = self.mocks

        self.ai_manager.create_chat.return_value = self.chat

    def stop_patches(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_main_exits_when_authentication_returns_none(self):
        self.authenticate.return_value = None

        main_module.main()

        self.set_current_user.assert_not_called()
        self.welcome_message.assert_not_called()
        self.ai_manager.create_chat.assert_not_called()
        self.close_case.assert_not_called()
        self.print_output.assert_any_call(
            "\nExiting application. Stay healthy!"
        )

    def test_main_exits_when_authentication_is_interrupted(self):
        self.authenticate.side_effect = KeyboardInterrupt

        main_module.main()

        self.set_current_user.assert_not_called()
        self.welcome_message.assert_not_called()

    def test_main_exits_when_authentication_input_ends(self):
        self.authenticate.side_effect = EOFError

        main_module.main()

        self.set_current_user.assert_not_called()
        self.welcome_message.assert_not_called()

    def test_main_sets_current_user_after_successful_authentication(self):
        main_module.main()

        self.set_current_user.assert_called_once_with("test-user-001")

    def test_main_shows_welcome_message_after_sign_in(self):
        main_module.main()

        self.welcome_message.assert_called_once()

    def test_main_creates_chat_for_active_case(self):
        main_module.main()

        self.ai_manager.create_chat.assert_called_once_with(self.case)

    def test_main_displays_storage_backend(self):
        main_module.main()

        self.print_output.assert_any_call(
            "[System] Storage backend: test"
        )

    def test_main_creates_case_when_no_active_case_exists(self):
        self.get_active_case.return_value = None

        main_module.main()

        self.create_new_case.assert_called_once()
        self.ai_manager.create_chat.assert_called_once_with(self.case)

    def test_main_stops_if_application_initialisation_fails(self):
        self.get_active_case.side_effect = RuntimeError("storage unavailable")

        main_module.main()

        self.print_output.assert_any_call(
            "[Fatal Error] Could not initialise the application: storage unavailable"
        )
        self.get_menu_input.assert_not_called()
        self.menu_selection.assert_not_called()

    def test_main_routes_menu_choice_to_menu_selection(self):
        main_module.main()

        self.menu_selection.assert_called_once_with(
            1,
            self.case,
            self.chat,
            self.user
        )

    def test_main_closes_case_when_menu_requests_quit(self):
        main_module.main()

        self.close_case.assert_called_once_with(self.case)
        self.print_output.assert_any_call(
            "Exiting application. Stay healthy!"
        )

    def test_main_handles_keyboard_interrupt_in_main_loop(self):
        self.get_menu_input.side_effect = KeyboardInterrupt

        main_module.main()

        self.close_case.assert_called_once_with(self.case)
        self.print_output.assert_any_call(
            "\n\nExiting application. Stay healthy!"
        )

    def test_main_handles_eof_in_main_loop(self):
        self.get_menu_input.side_effect = EOFError

        main_module.main()

        self.close_case.assert_called_once_with(self.case)
        self.print_output.assert_any_call(
            "\n\nInput stream closed. Exiting application."
        )

    def test_main_returns_to_menu_after_unexpected_loop_error(self):
        self.get_menu_input.side_effect = [
            RuntimeError("temporary menu error"),
            1
        ]

        main_module.main()

        self.menu_selection.assert_called_once()
        self.assertTrue(
            any(
                call.args and "[Error] An unexpected error occurred:" in str(call.args[0])
                for call in self.print_output.call_args_list
            )
        )

    def test_start_new_case_closes_existing_case_and_creates_new_chat(self):
        old_case = SimpleNamespace(case_id="case_old")
        new_case = SimpleNamespace(case_id="case_new", logs=[])
        self.create_new_case.return_value = new_case
        self.ai_manager.create_chat.return_value = self.chat

        result_case, result_chat = main_module.start_new_case(old_case)

        self.close_case.assert_called_once_with(old_case)
        self.create_new_case.assert_called_once()
        self.ai_manager.create_chat.assert_called_once_with(new_case)
        self.assertIs(result_case, new_case)
        self.assertIs(result_chat, self.chat)

    def test_start_new_case_works_without_an_existing_case(self):
        new_case = SimpleNamespace(case_id="case_new", logs=[])
        self.create_new_case.return_value = new_case

        result_case, result_chat = main_module.start_new_case(None)

        self.close_case.assert_not_called()
        self.create_new_case.assert_called_once()
        self.assertIs(result_case, new_case)
        self.assertIs(result_chat, self.chat)


class TestBuildUserRepository(unittest.TestCase):

    def test_build_user_repository_uses_in_memory_when_database_url_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(main_module, "print_output") as output:
                repository = main_module.build_user_repository()

        from Logic.in_memory_user_repository import InMemoryUserRepository
        self.assertIsInstance(repository, InMemoryUserRepository)
        output.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
