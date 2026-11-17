
"""Offline unit tests for the Healthcare Chatbot Input/Output Manager.

Tests patient validation, data collection, signup/login inputs,
symptom collection, output formatting, and prompt generation.

No AI, MongoDB, network connection, or real patient data required.
Uses Python's standard-library unittest framework.

Run: python "Test Script/test_input_output.py"
"""

import os
import sys
import unittest
from datetime import date

PROJECT_CODE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "Project Code"
    )
)

sys.path.insert(0, PROJECT_CODE)

from IO.patient import Patient
from IO.patient_validator import PatientValidator
from IO.input_manager import InputManager
from IO.auth_input_manager import AuthInputManager
from IO.output_manager import OutputManager
from IO.prompt_generator import PromptGenerator


# =========================================================
# 1. PATIENT VALIDATION TESTS
# =========================================================

class TestPatientValidator(unittest.TestCase):

    def setUp(self):
        self.validator = PatientValidator()

    def test_valid_name(self):
        result = self.validator.validate_name("John Tan")
        self.assertEqual(result, "John Tan")

    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            self.validator.validate_name("John123")

    def test_valid_dob(self):
        result = self.validator.validate_dob("15/05/2003")
        self.assertEqual(result, date(2003, 5, 15))

    def test_future_dob(self):
        with self.assertRaises(ValueError):
            self.validator.validate_dob("01/01/2099")

    def test_valid_gender(self):
        self.assertEqual(
            self.validator.validate_gender("f"),
            "Female"
        )

    def test_invalid_gender(self):
        with self.assertRaises(ValueError):
            self.validator.validate_gender("unknown")

    def test_valid_symptoms(self):
        result = self.validator.validate_symptoms(
            "headache, fever"
        )
        self.assertEqual(
            result,
            ["headache", "fever"]
        )

    def test_empty_symptoms(self):
        with self.assertRaises(ValueError):
            self.validator.validate_symptoms("")

    def test_valid_duration(self):
        result = self.validator.validate_duration("2 days")
        self.assertEqual(result, "2 days")

    def test_invalid_duration(self):
        with self.assertRaises(ValueError):
            self.validator.validate_duration("yesterday")


# =========================================================
# 2. PATIENT MODEL TESTS
# =========================================================

class TestPatient(unittest.TestCase):

    def test_patient_to_dict(self):
        patient = Patient(
            name="John Tan",
            dob="2003-05-15",
            gender="Male",
            symptoms=["fever", "headache"],
            symptom_duration="2 days"
        )

        result = patient.to_dict()

        self.assertEqual(
            result["name"],
            "John Tan"
        )

        self.assertEqual(
            result["dob"],
            "2003-05-15"
        )

        self.assertEqual(
            result["gender"],
            "Male"
        )

        self.assertEqual(
            result["symptoms"],
            ["fever", "headache"]
        )

        self.assertEqual(
            result["symptom_duration"],
            "2 days"
        )

        self.assertTrue(result["has_symptoms"])

        self.assertIn("timestamp", result)

    def test_calculate_age(self):
        dob = date(2003, 5, 15)
        today = date.today()

        expected_age = (
            today.year - dob.year
            - (
                (today.month, today.day)
                < (dob.month, dob.day)
            )
        )

        result = Patient.calculate_age(dob)

        self.assertEqual(result, expected_age)


# =========================================================
# 3. INPUT MANAGER TESTS
# =========================================================

class TestInputManager(unittest.TestCase):

    def setUp(self):
        self.profile = {
            "full_name": "John Tan",
            "dob": "2003-05-15",
            "gender": "Male"
        }

    def test_collect_symptoms(self):
        answers = iter([
            "headache, fever",
            "3 days"
        ])

        manager = InputManager(
            input_func=lambda prompt: next(answers),
            output_func=lambda message: None
        )

        result = manager.input_manager(self.profile)

        self.assertEqual(
            result["symptoms"],
            ["headache", "fever"]
        )

        self.assertEqual(
            result["symptom_duration"],
            "3 days"
        )

    def test_no_personal_info_prompted(self):
        prompts = []

        answers = iter([
            "fever",
            "2 days"
        ])

        def fake_input(prompt):
            prompts.append(prompt)
            return next(answers)

        manager = InputManager(
            input_func=fake_input,
            output_func=lambda message: None
        )

        result = manager.input_manager(self.profile)

        self.assertEqual(len(prompts), 2)

        self.assertIn(
            "symptoms",
            prompts[0].lower()
        )

        self.assertIn(
            "how long",
            prompts[1].lower()
        )

        self.assertEqual(
            result["name"],
            "John Tan"
        )

    def test_invalid_symptoms_retry(self):
        answers = iter([
            "",
            "headache",
            "2 days"
        ])

        messages = []

        manager = InputManager(
            input_func=lambda prompt: next(answers),
            output_func=messages.append
        )

        result = manager.input_manager(self.profile)

        self.assertEqual(
            result["symptoms"],
            ["headache"]
        )

        self.assertTrue(len(messages) > 0)

    def test_invalid_duration_retry(self):
        answers = iter([
            "fever",
            "yesterday",
            "3 days"
        ])

        manager = InputManager(
            input_func=lambda prompt: next(answers),
            output_func=lambda message: None
        )

        result = manager.input_manager(self.profile)

        self.assertEqual(
            result["symptom_duration"],
            "3 days"
        )

    def test_missing_profile(self):
        manager = InputManager(
            input_func=lambda prompt: "",
            output_func=lambda message: None
        )

        with self.assertRaises(ValueError):
            manager.input_manager({})

    def test_menu_input(self):
        manager = InputManager(
            input_func=lambda prompt: "1",
            output_func=lambda message: None
        )

        self.assertEqual(
            manager.get_menu_input(),
            "1"
        )


# =========================================================
# 4. SIGNUP AND LOGIN INPUT TESTS
# =========================================================

class TestAuthInputManager(unittest.TestCase):

    def test_valid_email(self):
        manager = AuthInputManager(
            input_func=lambda prompt: "TEST@EXAMPLE.COM",
            output_func=lambda message: None
        )

        result = manager.get_email()

        self.assertEqual(
            result,
            "test@example.com"
        )

    def test_invalid_email_retry(self):
        answers = iter([
            "invalid-email",
            "test@example.com"
        ])

        messages = []

        manager = AuthInputManager(
            input_func=lambda prompt: next(answers),
            output_func=messages.append
        )

        result = manager.get_email()

        self.assertEqual(
            result,
            "test@example.com"
        )

        self.assertTrue(len(messages) > 0)

    def test_signup_details(self):
        answers = iter([
            "John Tan",
            "15/05/2003",
            "M"
        ])

        passwords = iter([
            "SecurePassword123!",
            "SecurePassword123!"
        ])

        manager = AuthInputManager(
            input_func=lambda prompt: next(answers),
            password_func=lambda prompt: next(passwords),
            output_func=lambda message: None
        )

        result = manager.get_signup_details(
            "test@example.com"
        )

        self.assertEqual(
            result,
            {
                "email": "test@example.com",
                "full_name": "John Tan",
                "dob": "2003-05-15",
                "gender": "Male",
                "password": "SecurePassword123!"
            }
        )

    def test_password_mismatch_retry(self):
        answers = iter([
            "John Tan",
            "15/05/2003",
            "M"
        ])

        passwords = iter([
            "Password123!",
            "WrongPassword",
            "Password123!",
            "Password123!"
        ])

        messages = []

        manager = AuthInputManager(
            input_func=lambda prompt: next(answers),
            password_func=lambda prompt: next(passwords),
            output_func=messages.append
        )

        result = manager.get_signup_details(
            "test@example.com"
        )

        self.assertEqual(
            result["password"],
            "Password123!"
        )

        self.assertTrue(
            any(
                "do not match" in message.lower()
                for message in messages
            )
        )

    def test_login_password(self):
        manager = AuthInputManager(
            password_func=lambda prompt: "MyPassword123!"
        )

        result = manager.get_login_password()

        self.assertEqual(
            result,
            "MyPassword123!"
        )

    def test_signup_success_message(self):
        messages = []

        manager = AuthInputManager(
            output_func=messages.append
        )

        manager.display_signup_success()

        self.assertIn(
            "Account created successfully",
            messages[0]
        )

    def test_login_error_message(self):
        messages = []

        manager = AuthInputManager(
            output_func=messages.append
        )

        manager.display_login_error()

        self.assertIn(
            "Login failed",
            messages[0]
        )


# =========================================================
# 5. OUTPUT MANAGER TESTS
# =========================================================

class TestOutputManager(unittest.TestCase):

    def test_welcome_message(self):
        messages = []

        manager = OutputManager(
            output_func=messages.append
        )

        manager.welcome_message()

        self.assertIn(
            "Start a conversation",
            messages[0]
        )

    def test_no_saved_cases(self):
        messages = []

        manager = OutputManager(
            case_loader=lambda: [],
            output_func=messages.append
        )

        manager.print_cases()

        self.assertIn(
            "No saved cases found.",
            messages[0]
        )

    def test_saved_cases(self):
        messages = []

        cases = [
            {"symptoms": ["fever"]},
            {"symptoms": ["headache"]}
        ]

        manager = OutputManager(
            case_loader=lambda: cases,
            output_func=messages.append
        )

        manager.print_cases()

        self.assertEqual(len(messages), 2)

        self.assertIn(
            "Case 1",
            messages[0]
        )

        self.assertIn(
            "Case 2",
            messages[1]
        )


# =========================================================
# 6. PROMPT GENERATOR TESTS
# =========================================================

class TestPromptGenerator(unittest.TestCase):

    def test_create_prompt(self):
        generator = PromptGenerator()

        patient_data = {
            "name": "John Tan",
            "age": 23,
            "gender": "Male",
            "symptoms": ["headache", "fever"],
            "symptom_duration": "2 days"
        }

        result = generator.create_prompt(patient_data)

        self.assertIn("headache", result)
        self.assertIn("fever", result)
        self.assertIn("2 days", result)


# =========================================================
# RUN ALL TESTS
# =========================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
