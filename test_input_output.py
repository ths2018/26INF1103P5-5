"""Offline unit tests for input_output_manager.py.

No AI, network, or real case files required. Uses standard-library unittest.
Run: python -m unittest -v test_input_output_manager
"""
import os
import sys
import types
import unittest
from datetime import date, datetime, timedelta
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, os.path.dirname(_HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Stub external dependencies before importing the module under test.
if 'data_manager' not in sys.modules:
    _stub = types.ModuleType('data_manager')
    _stub.list_case_files = mock.MagicMock(name='list_case_files')
    _stub.load_case = mock.MagicMock(name='load_case')
    sys.modules['data_manager'] = _stub

import input_output_manager as io


class InputTestCase(unittest.TestCase):
    def run_inputs(self, func, values):
        with mock.patch('builtins.input', side_effect=values) as user_input, \
             mock.patch('builtins.print') as output:
            result = func()
        self.assertEqual(user_input.call_count, len(values))
        return result, '\n'.join(' '.join(str(x) for x in call.args) for call in output.call_args_list)


class TestWelcomeAndMenu(InputTestCase):
    def test_welcome_message(self):
        with mock.patch('builtins.print') as printer:
            io.welcome_message()
        self.assertIn('HEALTHCARE ASSESSMENT CHATBOT', str(printer.call_args_list))

    def test_menu_all_valid_options(self):
        for option in '123456':
            with self.subTest(option=option):
                result, _ = self.run_inputs(io.get_menu_input, [option])
                self.assertEqual(result, option)

    def test_menu_invalid_then_valid(self):
        for invalid in ('7', 'abc', '', '0'):
            with self.subTest(invalid=invalid):
                result, printed = self.run_inputs(io.get_menu_input, [invalid, '2'])
                self.assertEqual(result, '2')
                self.assertIn('Invalid input', printed)

    def test_menu_trims_whitespace(self):
        result, _ = self.run_inputs(io.get_menu_input, [' 4 '])
        self.assertEqual(result, '4')


class TestName(InputTestCase):
    def test_valid_names(self):
        for name in ('John Tan', 'Mary-Jane', "O'Connor", 'Émilie'):
            with self.subTest(name=name):
                result, _ = self.run_inputs(io.get_name, [name])
                self.assertEqual(result, name)

    def test_invalid_then_valid(self):
        for invalid in ('', '   ', 'John123', 'Alex@'):
            with self.subTest(invalid=invalid):
                result, printed = self.run_inputs(io.get_name, [invalid, 'John Tan'])
                self.assertEqual(result, 'John Tan')
                self.assertIn('Name', printed)

    def test_trims_name(self):
        result, _ = self.run_inputs(io.get_name, ['  John Tan  '])
        self.assertEqual(result, 'John Tan')


class TestDateAndAge(InputTestCase):
    def test_valid_dob(self):
        result, _ = self.run_inputs(io.get_dob, ['15/06/2005'])
        self.assertEqual(result, date(2005, 6, 15))

    def test_leap_day(self):
        result, _ = self.run_inputs(io.get_dob, ['29/02/2004'])
        self.assertEqual(result, date(2004, 2, 29))

    def test_invalid_dates_then_valid(self):
        invalids = ('31/02/2005', '2005-06-15', '29/02/2025', '')
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                result, printed = self.run_inputs(io.get_dob, [invalid, '15/06/2005'])
                self.assertEqual(result, date(2005, 6, 15))
                self.assertIn('Invalid date', printed)

    def test_future_dob_rejected(self):
        tomorrow = (date.today() + timedelta(days=1)).strftime('%d/%m/%Y')
        result, printed = self.run_inputs(io.get_dob, [tomorrow, '15/06/2005'])
        self.assertEqual(result, date(2005, 6, 15))
        self.assertIn('future', printed)

    def test_age_birthday_today(self):
        today = date.today()
        dob = today.replace(year=today.year - 20)
        self.assertEqual(io.calculate_age(dob), 20)

    def test_age_birthday_not_yet_occurred(self):
        today = date.today()
        dob = today - timedelta(days=365 * 20 - 15)
        expected = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        self.assertEqual(io.calculate_age(dob), expected)

    def test_age_newborn(self):
        self.assertEqual(io.calculate_age(date.today()), 0)


class TestGenderAndSymptoms(InputTestCase):
    def test_gender_valid_variants(self):
        for value, expected in [('Male', 'Male'), ('female', 'Female'), ('m', 'Male'), ('F', 'Female')]:
            with self.subTest(value=value):
                result, _ = self.run_inputs(io.get_gender, [value])
                self.assertEqual(result, expected)

    def test_gender_invalid_then_valid(self):
        result, printed = self.run_inputs(io.get_gender, ['Other', '', 'f'])
        self.assertEqual(result, 'Female')
        self.assertIn('valid option', printed)

    def test_has_symptoms_yes_no(self):
        for answer, expected in [('Yes', True), ('NO', False)]:
            with self.subTest(answer=answer):
                result, _ = self.run_inputs(io.has_symptoms, [answer])
                self.assertIs(result, expected)

    def test_has_symptoms_invalid_then_valid(self):
        result, printed = self.run_inputs(io.has_symptoms, ['maybe', 'yes'])
        self.assertTrue(result)
        self.assertIn('Invalid input', printed)

    def test_single_and_multiple_symptoms(self):
        for value, expected in [('Headache', ['Headache']), ('Fever, Cough', ['Fever', 'Cough']),
                                (' fever, , cough, ', ['fever', 'cough'])]:
            with self.subTest(value=value):
                result, _ = self.run_inputs(io.get_symptoms, [value])
                self.assertEqual(result, expected)

    def test_empty_symptoms_reprompt(self):
        result, printed = self.run_inputs(io.get_symptoms, ['', ', ,', 'Headache'])
        self.assertEqual(result, ['Headache'])
        self.assertIn('at least one symptom', printed)


class TestDuration(InputTestCase):
    def test_valid_units(self):
        for value in ('1 minute', '2 hours', '3 days', '4 weeks', '5 months', '1 year'):
            with self.subTest(value=value):
                result, _ = self.run_inputs(io.get_symptom_duration, [value])
                self.assertEqual(result, value)

    def test_invalid_duration_then_valid(self):
        for invalid in ('0 days', '-2 days', 'abc days', '3 decades', '3', '1.5 days', ''):
            with self.subTest(invalid=invalid):
                result, printed = self.run_inputs(io.get_symptom_duration, [invalid, '3 days'])
                self.assertEqual(result, '3 days')
                self.assertTrue(printed)

    def test_duration_lowercase_and_whitespace(self):
        result, _ = self.run_inputs(io.get_symptom_duration, ['  2 WEEKS  '])
        self.assertEqual(result, '2 weeks')


class TestPatientManager(unittest.TestCase):
    def test_patient_with_symptoms(self):
        with mock.patch.object(io, 'get_name', return_value='Jane'), \
             mock.patch.object(io, 'get_dob', return_value=date(2000, 1, 1)), \
             mock.patch.object(io, 'get_gender', return_value='Female'), \
             mock.patch.object(io, 'has_symptoms', return_value=True), \
             mock.patch.object(io, 'get_symptoms', return_value=['fever', 'cough']), \
             mock.patch.object(io, 'get_symptom_duration', return_value='3 days'):
            data = io.input_manager()
        self.assertEqual(data['name'], 'Jane')
        self.assertEqual(data['dob'], '2000-01-01')
        self.assertEqual(data['gender'], 'Female')
        self.assertTrue(data['has_symptoms'])
        self.assertEqual(data['symptoms'], ['fever', 'cough'])
        self.assertEqual(data['symptom_duration'], '3 days')
        self.assertEqual(data['age'], io.calculate_age(date(2000, 1, 1)))
        self.assertIsInstance(datetime.fromisoformat(data['timestamp']), datetime)

    def test_patient_without_symptoms_skips_questions(self):
        with mock.patch.object(io, 'get_name', return_value='Jane'), \
             mock.patch.object(io, 'get_dob', return_value=date(2000, 1, 1)), \
             mock.patch.object(io, 'get_gender', return_value='Female'), \
             mock.patch.object(io, 'has_symptoms', return_value=False), \
             mock.patch.object(io, 'get_symptoms') as symptoms, \
             mock.patch.object(io, 'get_symptom_duration') as duration:
            data = io.input_manager()
        self.assertEqual(data['symptoms'], [])
        self.assertEqual(data['symptom_duration'], 'None')
        symptoms.assert_not_called()
        duration.assert_not_called()


class TestPrompt(unittest.TestCase):
    def setUp(self):
        self.patient = {'name': 'Jane', 'age': 26, 'gender': 'Female',
                        'symptoms': ['fever', 'cough'], 'symptom_duration': '3 days'}

    def test_prompt_includes_patient_information(self):
        prompt = io.create_prompt(self.patient)
        for value in ('Jane', '26', 'Female', 'fever, cough', '3 days', 'warning signs'):
            self.assertIn(value, prompt)

    def test_prompt_with_no_symptoms(self):
        patient = dict(self.patient, symptoms=[], symptom_duration='None')
        self.assertIn('No current symptoms.', io.create_prompt(patient))

    def test_prompt_with_string_symptoms(self):
        patient = dict(self.patient, symptoms='headache')
        self.assertIn('headache', io.create_prompt(patient))


class TestFollowUpAndYesNo(InputTestCase):
    def test_additional_input_valid(self):
        result, _ = self.run_inputs(lambda: io.get_additional_input('How long?'), ['Three days'])
        self.assertEqual(result, 'Three days')

    def test_additional_input_empty_then_valid(self):
        result, printed = self.run_inputs(lambda: io.get_additional_input('How long?'), ['', '  ', 'Three days'])
        self.assertEqual(result, 'Three days')
        self.assertIn('How long?', printed)

    def test_yes_no_variants(self):
        for answer, expected in [('y', True), ('yes', True), ('n', False), ('no', False), ('YES', True)]:
            with self.subTest(answer=answer):
                result, _ = self.run_inputs(lambda: io.ask_yes_no('Continue? '), [answer])
                self.assertIs(result, expected)

    def test_yes_no_invalid_then_valid(self):
        result, printed = self.run_inputs(lambda: io.ask_yes_no('Continue? '), ['maybe', 'y'])
        self.assertTrue(result)
        self.assertIn("Please enter 'y' or 'n'", printed)


class TestOutput(unittest.TestCase):
    def test_print_output(self):
        with mock.patch('builtins.print') as printer:
            io.print_output('Low Risk')
        printer.assert_called_once_with('Low Risk')

    def test_print_output_empty(self):
        with mock.patch('builtins.print') as printer:
            io.print_output('')
        printer.assert_called_once_with('')

    def test_keyword_valid(self):
        with mock.patch('builtins.input', return_value=' fever '):
            self.assertEqual(io.keyword_input(), 'fever')

    def test_keyword_empty_then_valid(self):
        with mock.patch('builtins.input', side_effect=['', '  ', 'fever']), \
             mock.patch('builtins.print') as printer:
            self.assertEqual(io.keyword_input(), 'fever')
        self.assertIn('Keyword cannot be empty', str(printer.call_args_list))

    def test_no_saved_cases(self):
        with mock.patch.object(io, 'list_case_files', return_value=[]), \
             mock.patch('builtins.print') as printer:
            io.print_cases()
        self.assertIn('No cases saved yet.', str(printer.call_args_list))

    def test_active_and_closed_cases(self):
        cases = {'active.json': {'case_id': 'active', 'status': 'open', 'logs': [{'user_input': 'headache'}]},
                 'closed.json': {'case_id': 'closed', 'status': 'closed', 'logs': []}}
        with mock.patch.object(io, 'list_case_files', return_value=list(cases)), \
             mock.patch.object(io, 'load_case', side_effect=lambda path: cases[path]), \
             mock.patch('builtins.print') as printer:
            io.print_cases()
        output = str(printer.call_args_list)
        for value in ('ACTIVE', 'CLOSED', 'headache', 'Empty', 'Saved Cases (2)'):
            self.assertIn(value, output)

    def test_invalid_case_is_skipped(self):
        with mock.patch.object(io, 'list_case_files', return_value=['bad.json']), \
             mock.patch.object(io, 'load_case', return_value=None), \
             mock.patch('builtins.print') as printer:
            io.print_cases()
        self.assertNotIn('ACTIVE', str(printer.call_args_list))


if __name__ == '__main__':
    unittest.main(verbosity=2)
