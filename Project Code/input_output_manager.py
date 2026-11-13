from IO.patient import Patient
from IO.patient_validator import PatientValidator
from IO.input_manager import InputManager
from IO.output_manager import OutputManager
from IO.prompt_generator import PromptGenerator
from IO.auth_input_manager import AuthInputManager


def build_io(
    validator=None,
    case_loader=None,
    input_func=None,
    output_func=None
):
    validator = (
        validator
        if validator is not None
        else PatientValidator()
    )

    inputs = InputManager(
        validator,
        input_func=input_func,
        output_func=output_func
    )

    outputs = OutputManager(
        case_loader=case_loader,
        output_func=output_func
    )

    return inputs, outputs, PromptGenerator()


_INPUT, _OUTPUT, _PROMPT = build_io()

_AUTH = AuthInputManager(
    input_manager=_INPUT
)


# ==========================================
# Existing Input/Output Functions
# ==========================================

def welcome_message():
    return _OUTPUT.welcome_message()


def get_menu_input():
    return _INPUT.get_menu_input()


def get_name():
    return _INPUT.get_name()


def get_dob():
    return _INPUT.get_dob()


def calculate_age(dob):
    return Patient.calculate_age(dob)


def get_gender():
    return _INPUT.get_gender()


def has_symptoms():
    return _INPUT.has_symptoms()


def get_symptoms():
    return _INPUT.get_symptoms()


def get_symptom_duration():
    return _INPUT.get_symptom_duration()


def input_manager(user_profile):
    return _INPUT.input_manager(user_profile)


def create_prompt(patient_data):
    return _PROMPT.create_prompt(patient_data)


def get_additional_input(question):
    return _INPUT.get_additional_input(question)


def ask_yes_no(prompt):
    return _INPUT.ask_yes_no(prompt)


def print_output(output):
    return _OUTPUT.print_output(output)


def keyword_input():
    return _INPUT.keyword_input()


def filter_input():
    return _INPUT.filter_input()


def print_cases(case_loader=None):
    """
    Pass a case loader already restricted
    to the authenticated user.
    """

    return OutputManager(
        case_loader=case_loader
    ).print_cases()


# ==========================================
# New Authentication Input/Output Functions
# ==========================================

def get_email():
    return _AUTH.get_email()


def get_signup_details(email):
    return _AUTH.get_signup_details(email)


def get_login_password():
    return _AUTH.get_login_password()


def display_auth_message(message):
    return _AUTH.display_auth_message(message)


def display_signup_success():
    return _AUTH.display_signup_success()


def display_login_success():
    return _AUTH.display_login_success()


def display_login_error():
    return _AUTH.display_login_error()