
"""
input_output_manager.py - entry point for the IO layer.

Wires the objects from the IO package together and
preserves the old function-based API so main.py and
existing tests can continue working.
"""

from IO.patient_validator import PatientValidator
from IO.input_manager import InputManager
from IO.output_manager import OutputManager
from IO.prompt_generator import PromptGenerator
from IO.patient import Patient

# ==========================================
# Factory Function
# ==========================================

def build_io(validator=None, case_loader=None,
             input_func=input, output_func=print):
    """Factory that wires the IO objects together."""

    if validator is None:
        validator = PatientValidator()

    input_mgr = InputManager(
        validator,
        input_func=input_func,
        output_func=output_func
    )

    output_mgr = OutputManager(
        case_loader=case_loader,
        output_func=output_func
    )

    prompt_mgr = PromptGenerator()

    return input_mgr, output_mgr, prompt_mgr

_INPUT, _OUTPUT, _PROMPT = build_io()

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


def input_manager():
    return _INPUT.input_manager()


def create_prompt(patient_data):
    return _PROMPT.create_prompt(patient_data)


def get_additional_input(follow_up_question):
    return _INPUT.get_additional_input(
        follow_up_question
    )


def ask_yes_no(prompt):
    return _INPUT.ask_yes_no(prompt)


def print_cases():
    # Local import avoids circular dependencies
    from data_manager import list_cases

    # Use the existing output manager with a case loader
    output_mgr = OutputManager(case_loader=list_cases)

    return output_mgr.print_cases()


def print_output(output):
    return _OUTPUT.print_output(output)


def keyword_input():
    return _INPUT.keyword_input()


def filter_input():
    return _INPUT.filter_input()
