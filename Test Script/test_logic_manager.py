"""
test_logic_manager.py - automated tests for the logic manager (Logic package).

HOW TO RUN (from the "Project Code" folder, or from this "Test Script" folder):

    python -m unittest discover -s "Test Script" -p "test_logic_manager.py" -v
    # or, if you use pytest:
    python -m pytest "Test Script/test_logic_manager.py" -v

These tests need NO internet, NO Gemini key and NO MongoDB. The modules that talk to
the outside world (AI.ai_manager, data_manager, input_output_manager) are replaced by
small fakes while the tests run, and put back afterwards.

What is covered
    1. Keyword detectors (health / emergency / memory) and the abstract TextDetector
    2. AIResponse parsing (urgency, certainty, follow-up, sections)
    3. Age risk and the AssessmentEngine (every branch of process())
    4. GuidelineRepository, UrgencyValidator, ServiceAdviceValidator (test data below)
    5. Guideline cross-check inside the engine (urgency only goes UP)
    6. MenuController (every menu option, emergency advice, guideline check output)
    7. CaseRepository and the logic_manager_oop wrapper functions
    8. Authentication: password hashers, AuthService, AuthController, user repositories
    9. Integrity of your real medical_data JSON files (skipped if the folder is missing)
"""

import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from datetime import date
from types import SimpleNamespace
from unittest import mock


# ---------------------------------------------------------------------------
# Find the project root (the folder that contains logic_manager_oop.py)
# ---------------------------------------------------------------------------

def _find_project_root():
    folder = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        candidates = (folder, os.path.join(folder, "Project Code"))
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "logic_manager_oop.py")):
                return candidate
        folder = os.path.dirname(folder)
    raise RuntimeError("Could not find logic_manager_oop.py. Keep this test file in "
                       "'Project Code' or in a folder alongside it.")


ROOT = _find_project_root()


# ---------------------------------------------------------------------------
# Fakes for the modules that touch the outside world
# ---------------------------------------------------------------------------

class _IOState:
    """What the fake input_output_manager prints / returns. Reset before every test."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.output = []                 # everything passed to print_output()
        self.yes_no = []                 # queued answers for ask_yes_no() (default: False)
        self.answers = []                # queued answers for get_additional_input()
        self.calls = []                  # (name, args...) of the calls that were made
        self.patient = {"age": 30, "symptoms": "headache"}
        self.prompt = "I have a headache"
        self.keyword = "fever"
        self.filter = ""
        self.chosen_cases = []

    def text(self):
        return "\n".join(str(line) for line in self.output)


class _DataState:
    """What the fake data_manager returns / records. Reset before every test."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = []
        self.records = []
        self.export_choices = []
        self.active_case = None
        self.stats_error = None
        self.created = 0


IO = _IOState()
DATA = _DataState()


def _install_fakes():
    noop = lambda *a, **k: None

    # --- AI.ai_manager -----------------------------------------------------
    ai_package = types.ModuleType("AI")
    ai_package.__path__ = []
    ai_manager = types.ModuleType("AI.ai_manager")
    ai_manager.ask_ai = lambda chat, text: None
    ai_manager.check_relevance = lambda text, case: True
    ai_manager.create_chat = lambda case: object()
    ai_package.ai_manager = ai_manager

    # --- input_output_manager ---------------------------------------------
    def ask_yes_no(prompt):
        IO.calls.append(("ask_yes_no", prompt))
        return IO.yes_no.pop(0) if IO.yes_no else False

    def get_additional_input(question):
        IO.calls.append(("get_additional_input", question))
        return IO.answers.pop(0) if IO.answers else "no"

    def input_manager(user_profile=None):
        IO.calls.append(("input_manager", user_profile))
        return IO.patient

    def create_prompt(patient_data):
        IO.calls.append(("create_prompt", patient_data))
        return IO.prompt

    def choose_cases(cases):
        IO.calls.append(("choose_cases", cases))
        return IO.chosen_cases

    io_module = types.ModuleType("input_output_manager")
    io_module.print_output = lambda text="": IO.output.append(text)
    io_module.ask_yes_no = ask_yes_no
    io_module.get_additional_input = get_additional_input
    io_module.input_manager = input_manager
    io_module.create_prompt = create_prompt
    io_module.choose_cases = choose_cases
    io_module.keyword_input = lambda: IO.keyword
    io_module.filter_input = lambda: IO.filter
    io_module.print_cases = lambda *a, **k: IO.calls.append(("print_cases",))

    # --- data_manager -------------------------------------------------------
    def create_new_case():
        DATA.created += 1
        return {"case_id": f"case_new_{DATA.created}", "logs": []}

    def show_stats(query="", per_case=False):
        DATA.calls.append(("show_stats", query, per_case))
        if DATA.stats_error:
            raise DATA.stats_error

    data_module = types.ModuleType("data_manager")
    data_module.add_log = lambda case, u, r: DATA.calls.append(("add_log", case, u, r))
    data_module.close_case = lambda case: DATA.calls.append(("close_case", case))
    data_module.create_new_case = create_new_case
    data_module.get_active_case = lambda: DATA.active_case
    data_module.filter_records_by_keyword = lambda keyword, records=None: (
        DATA.calls.append(("filter", keyword)) or DATA.records)
    data_module.show_history = lambda records, page_size=2: DATA.calls.append(("show_history", records))
    data_module.list_export_choices = lambda: DATA.export_choices
    data_module.convert_json_to_csv = lambda *a, **k: DATA.calls.append(("csv", a, k))
    data_module.convert_json_to_xlsx = lambda *a, **k: True
    data_module.open_file = noop
    data_module.show_stats = show_stats

    sys.modules.update({
        "AI": ai_package,
        "AI.ai_manager": ai_manager,
        "input_output_manager": io_module,
        "data_manager": data_module,
    })


# ---------------------------------------------------------------------------
# Test data for the guideline cross-check (written to a temporary folder)
# ---------------------------------------------------------------------------

def _source(name, extra=""):
    return {"source_name": "Test Ministry", "source_url": f"https://example.test/{name}{extra}",
            "last_updated": "2025-01-02", "last_verified": "2026-11-13"}


def _symptom(rec_id, topic, keywords, audience="general_public", review="needs_professional_review", **levels):
    return {"id": rec_id, "record_type": "symptom_guideline", "intended_audience": audience,
            "topic": topic, "keywords": keywords,
            "care_guidance": {level: {"conditions": conditions, "recommendations": ["Follow the advice."]}
                              for level, conditions in levels.items()},
            "source": _source(rec_id.lower()), "review_status": review}


SYMPTOM_DATA = [
    _symptom("T-HEADACHE", "Headaches", ["headache", "migraine"],
             self_care=["Mild headache."],
             emergency_department=["Severe headache.", "Weakness and/or numbness.",
                                   "Vomiting that does not subside."]),
    _symptom("T-ABDOMINAL", "Abdominal pain", ["abdominal pain"],
             emergency_department=["Sudden and severe abdominal pain.", "Blood in vomit."]),
    _symptom("T-CHEST", "Chest pain", ["chest pain"], emergency_department=["Chest pain."]),
    _symptom("T-SEIZURE", "Seizures", ["seizure"], emergency_response=["Seizures."]),
    _symptom("T-COUGH", "Cough", ["cough"], review="reviewed", self_care=["Dry cough."]),
    _symptom("T-PRO", "Professional headache guide", ["headache"],
             audience="healthcare_professionals", emergency_department=["Severe headache."]),
]

SERVICE_DATA = [
    {"id": "SCDF-EMS-001", "topic": "Calling 995", "urgency_level": "emergency",
     "recommendation": ["Call 995 only for life-threatening emergencies.",
                        "Give the address of the patient.", "Stay on the line."],
     "conditions_requiring_995": ["Seizures", "Stroke", "Loss of consciousness"],
     "source": _source("scdf-ems"), "review_status": "needs_professional_review"},
    {"id": "SCDF-NON-EMERGENCY-001", "topic": "Non-emergency options", "urgency_level": "non-emergency",
     "recommendation": ["Visit a GP."],
     "conditions_not_requiring_995": ["Toothaches", "Headaches", "Coughs"],
     "effective_changes": [{
         "effective_date": "2027-01-01",
         "description": "The SCDF 1777 non-emergency ambulance hotline will cease operation.",
         "replacement_service": "NurseFirst", "replacement_contact": "6262 6262"}],
     "source": _source("scdf-non"), "review_status": "needs_professional_review"},
]

GUIDELINE_DIR = None
_SAVED_MODULES = {}
_FAKED = ("AI", "AI.ai_manager", "input_output_manager", "data_manager")

# Filled in by setUpModule() once the fakes are installed
lm = None
AIResponse = AssessmentEngine = CaseRepository = MenuController = GuidelineRepository = None
EmergencyDetector = HealthDetector = MemoryQuestionDetector = TextDetector = None
UrgencyValidator = ServiceAdviceValidator = ResponseValidator = None
ScriptedAIService = AIService = None
keywords = None


def _project_modules():
    return [m for m in list(sys.modules) if m == "logic_manager_oop" or m == "Logic" or m.startswith("Logic.")]


def setUpModule():
    global GUIDELINE_DIR, lm, keywords
    global AIResponse, AssessmentEngine, CaseRepository, MenuController, GuidelineRepository
    global EmergencyDetector, HealthDetector, MemoryQuestionDetector, TextDetector
    global UrgencyValidator, ServiceAdviceValidator, ResponseValidator, ScriptedAIService, AIService

    for name in _FAKED + tuple(_project_modules()):
        _SAVED_MODULES[name] = sys.modules.get(name)
    for name in _project_modules():
        del sys.modules[name]
    _install_fakes()
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    GUIDELINE_DIR = tempfile.mkdtemp(prefix="guidelines_")
    for filename, data in (("symptom_guidelines.json", SYMPTOM_DATA), ("care_recommendations.json", SERVICE_DATA)):
        with open(os.path.join(GUIDELINE_DIR, filename), "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    import logic_manager_oop as lm_module
    from Logic import keywords as keywords_module
    from Logic.ai_response import AIResponse as _AIResponse
    from Logic.ai_service import AIService as _AIService
    from Logic.assessment_engine import AssessmentEngine as _Engine
    from Logic.case_repository import CaseRepository as _CaseRepository
    from Logic.emergency_detector import EmergencyDetector as _Emergency
    from Logic.guideline_repository import GuidelineRepository as _Guidelines
    from Logic.health_detector import HealthDetector as _Health
    from Logic.memory_question_detector import MemoryQuestionDetector as _Memory
    from Logic.menu_controller import MenuController as _Menu
    from Logic.response_validator import ResponseValidator as _Validator
    from Logic.scripted_ai_service import ScriptedAIService as _Scripted
    from Logic.service_advice_validator import ServiceAdviceValidator as _Service
    from Logic.text_detector import TextDetector as _TextDetector
    from Logic.urgency_validator import UrgencyValidator as _Urgency

    lm, keywords = lm_module, keywords_module
    AIResponse, AIService, AssessmentEngine, CaseRepository = _AIResponse, _AIService, _Engine, _CaseRepository
    EmergencyDetector, GuidelineRepository, HealthDetector = _Emergency, _Guidelines, _Health
    MemoryQuestionDetector, MenuController, ResponseValidator = _Memory, _Menu, _Validator
    ScriptedAIService, ServiceAdviceValidator, TextDetector, UrgencyValidator = _Scripted, _Service, _TextDetector, _Urgency


def tearDownModule():
    shutil.rmtree(GUIDELINE_DIR, ignore_errors=True)
    for name in _project_modules():
        del sys.modules[name]
    for name, module in _SAVED_MODULES.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


# ---------------------------------------------------------------------------
# Small helpers used by many tests
# ---------------------------------------------------------------------------

def reply(urgency="non-urgent", certainty="80%", follow_up="None", guidance="Rest and drink water."):
    """A reply in the format the AI is asked to use."""
    return (f"Urgency classification: {urgency}\nCertainty: {certainty}\n\n"
            f"Follow-Up Questions:\n{follow_up}\n\nNext-Step Guidance:\n{guidance}")


class FakeRepository:
    """Stands in for CaseRepository and records every call."""

    def __init__(self, active=None, records=None, export_choices=None):
        self.active = active
        self.records = records if records is not None else []
        self._export_choices = export_choices if export_choices is not None else []
        self.stats_error = None
        self.calls = []
        self.created = []

    def get_active_case(self):
        return self.active

    def create_case(self):
        case = {"case_id": f"new_{len(self.created) + 1}", "logs": []}
        self.created.append(case)
        return case

    def close_case(self, case):
        self.calls.append(("close_case", case))

    def add_log(self, case, user_input, ai_response):
        self.calls.append(("add_log", case, user_input, ai_response))

    def search(self, keyword):
        self.calls.append(("search", keyword))
        return self.records

    def show_history(self, records):
        self.calls.append(("show_history", records))

    def export_choices(self):
        return self._export_choices

    def export_csv(self, case_ids=None):
        self.calls.append(("export_csv", case_ids))

    def show_stats(self, query, per_case=False):
        self.calls.append(("show_stats", query, per_case))
        if self.stats_error:
            raise self.stats_error

    def names(self):
        return [call[0] for call in self.calls]


class BaseTest(unittest.TestCase):
    def setUp(self):
        IO.reset()
        DATA.reset()


HEALTH_TEXT = "I have a headache and a fever"
EMERGENCY_TEXT = "he is unconscious"          # 'unconscious' is in EMERGENCY_KEYWORDS
NOT_HEALTH_TEXT = "what is the capital of France"


# ===========================================================================
# 1. Keyword detectors
# ===========================================================================

class TestDetectors(BaseTest):
    def test_text_detector_is_abstract(self):
        with self.assertRaises(TypeError):
            TextDetector()

    def test_health_detector_basic(self):
        detector = HealthDetector()
        self.assertTrue(detector.detect("I have a headache"))
        self.assertTrue(detector.detect("My CHILD has a FEVER"))          # case-insensitive
        self.assertFalse(detector.detect(NOT_HEALTH_TEXT))

    def test_health_detector_matches_whole_words_only(self):
        # 'arm' is a health keyword, but it must not match inside 'alarm'
        self.assertFalse(HealthDetector().detect("the alarm clock rang"))
        self.assertTrue(HealthDetector().detect("my arm hurts"))

    def test_every_health_keyword_is_detected(self):
        detector = HealthDetector()
        for keyword in keywords.HEALTH_KEYWORDS:
            with self.subTest(keyword=keyword):
                self.assertTrue(detector.detect(f"I have {keyword}"))

    def test_every_emergency_keyword_is_detected(self):
        detector = EmergencyDetector()
        for keyword in keywords.EMERGENCY_KEYWORDS:
            with self.subTest(keyword=keyword):
                self.assertTrue(detector.detect(f"please help, {keyword}"))

    def test_emergency_detector_ignores_mild_symptoms(self):
        self.assertFalse(EmergencyDetector().detect("I have a mild cough and a runny nose"))
        self.assertFalse(EmergencyDetector().detect("I have a headache"))

    def test_memory_detector(self):
        detector = MemoryQuestionDetector()
        self.assertTrue(detector.detect("What do you remember about my case?"))
        self.assertTrue(detector.detect("do you REMEMBER what I said"))
        self.assertFalse(detector.detect("I have a headache"))

    def test_every_memory_phrase_is_detected(self):
        for phrase in keywords.MEMORY_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertTrue(MemoryQuestionDetector().detect(f"hello, {phrase} please"))

    def test_detectors_never_raise_on_odd_input(self):
        for detector in (HealthDetector(), EmergencyDetector(), MemoryQuestionDetector()):
            for value in (None, 123, "", "   ", [], {}):
                with self.subTest(detector=type(detector).__name__, value=value):
                    self.assertFalse(detector.detect(value))


# ===========================================================================
# 2. AIResponse parsing
# ===========================================================================

class TestAIResponse(BaseTest):
    def test_urgency_values(self):
        for urgency in ("emergency", "urgent", "non-urgent", "insufficient information"):
            with self.subTest(urgency=urgency):
                self.assertEqual(AIResponse(reply(urgency)).urgency, urgency)

    def test_urgency_is_case_insensitive(self):
        self.assertEqual(AIResponse("URGENCY CLASSIFICATION: Urgent").urgency, "urgent")

    def test_urgency_defaults_when_missing_or_unknown(self):
        self.assertEqual(AIResponse("no label here").urgency, "insufficient information")
        self.assertEqual(AIResponse("Urgency classification: severe").urgency, "insufficient information")

    def test_certainty_formats(self):
        self.assertAlmostEqual(AIResponse(reply(certainty="80%")).certainty, 0.8)
        self.assertAlmostEqual(AIResponse(reply(certainty="0.9")).certainty, 0.9)
        self.assertAlmostEqual(AIResponse(reply(certainty="85")).certainty, 0.85)

    def test_certainty_is_clamped_and_defaults(self):
        self.assertEqual(AIResponse(reply(certainty="250%")).certainty, 1.0)
        self.assertEqual(AIResponse("nothing").certainty, 0.0)

    def test_follow_up_question(self):
        response = AIResponse(reply(follow_up="How long has it lasted?"))
        self.assertEqual(response.follow_up_question, "How long has it lasted?")
        self.assertTrue(response.has_follow_up)

    def test_no_follow_up_markers(self):
        for marker in ("None", "none.", "Not applicable"):
            with self.subTest(marker=marker):
                response = AIResponse(reply(follow_up=marker))
                self.assertIsNone(response.follow_up_question)
                self.assertFalse(response.has_follow_up)

    def test_section_extraction_stops_at_next_label(self):
        response = AIResponse(reply(guidance="See a doctor."))
        self.assertEqual(response.section("Next-Step Guidance:"), "See a doctor.")
        self.assertEqual(response.section("Certainty:"), "80%")
        self.assertIsNone(response.section("AI Response:"))

    def test_is_emergency_only_for_emergency(self):
        self.assertTrue(AIResponse(reply("emergency")).is_emergency)
        self.assertFalse(AIResponse(reply("urgent")).is_emergency)

    def test_emergency_factory(self):
        response = AIResponse.emergency("Call for help now.")
        self.assertEqual(response.urgency, "emergency")
        self.assertEqual(response.certainty, 1.0)
        self.assertIsNone(response.follow_up_question)
        self.assertEqual(response.section("Next-Step Guidance:"), "Call for help now.")

    def test_non_string_text_is_safe(self):
        response = AIResponse(None)
        self.assertEqual(response.urgency, "insufficient information")
        self.assertEqual(response.certainty, 0.0)
        self.assertIsNone(response.follow_up_question)
        self.assertIsNone(response.section("Next-Step Guidance:"))
        self.assertIsNone(response.text)


# ===========================================================================
# 3. Age risk + AssessmentEngine
# ===========================================================================

class TestAgeRisk(BaseTest):
    def test_age_groups(self):
        risk = AssessmentEngine.assess_age_risk
        self.assertEqual(risk(4), "High risk age group")
        self.assertEqual(risk(5), "Not high risk age group")
        self.assertEqual(risk(30), "Not high risk age group")
        self.assertEqual(risk(65), "Not high risk age group")
        self.assertEqual(risk(66), "High risk age group")
        self.assertEqual(risk("70"), "High risk age group")

    def test_unknown_age(self):
        for value in (None, "abc", "", [], {}):
            with self.subTest(value=value):
                self.assertEqual(AssessmentEngine.assess_age_risk(value), "Unknown")


class TestAssessmentEngine(BaseTest):
    RESULT_KEYS = {"ai_response", "urgency", "certainty", "is_relevant", "has_follow_up", "is_health_related",
                   "is_emergency", "exchanges", "validation", "urgency_classification"}

    def make(self, replies=(), relevant=True, repo=None, case=None, guidelines=None, **kwargs):
        self.ai = ScriptedAIService(list(replies), relevant=relevant)
        self.repo = repo or FakeRepository()
        return AssessmentEngine(self.ai, self.repo, case, "chat-object", guidelines=guidelines, **kwargs)

    # ---- input validation / short-circuits --------------------------------

    def test_invalid_input_returns_empty_result(self):
        engine = self.make()
        for value in ("", "   ", None, 123, []):
            with self.subTest(value=value):
                result = engine.process(value)
                self.assertIsNone(result["ai_response"])
                self.assertEqual(result["urgency"], "insufficient information")
                self.assertEqual(result["certainty"], 0.0)
                self.assertEqual(result["exchanges"], [])
        self.assertEqual(self.ai.received, [])

    def test_result_always_has_the_same_keys(self):
        engine = self.make([reply()])
        for text in ("", NOT_HEALTH_TEXT, EMERGENCY_TEXT, HEALTH_TEXT):
            with self.subTest(text=text):
                self.assertTrue(self.RESULT_KEYS <= set(engine.process(text)))

    def test_not_health_related(self):
        engine = self.make([reply()])
        result = engine.process(NOT_HEALTH_TEXT)
        self.assertFalse(result["is_health_related"])
        self.assertEqual(result["certainty"], 1.0)
        self.assertIn("not appear to be health-related", result["ai_response"])
        self.assertEqual(self.ai.received, [])             # the AI is never called

    def test_emergency_keyword_skips_the_ai(self):
        engine = self.make([reply()])
        result = engine.process(EMERGENCY_TEXT)
        self.assertTrue(result["is_emergency"])
        self.assertEqual(result["urgency"], "emergency")
        self.assertEqual(result["certainty"], 1.0)
        self.assertTrue(result["is_health_related"] and result["is_relevant"])
        self.assertIn("medical emergency", result["ai_response"])
        self.assertEqual(len(result["exchanges"]), 1)
        self.assertEqual(self.ai.received, [])

    def test_memory_question_is_sent_to_the_ai(self):
        engine = self.make([reply("non-urgent")])
        result = engine.process("what do you remember about my case")
        self.assertEqual(self.ai.received, ["what do you remember about my case"])
        self.assertTrue(result["is_relevant"])
        self.assertEqual(len(result["exchanges"]), 1)

    def test_memory_question_ai_failure(self):
        result = self.make([]).process("what do you remember about my case")
        self.assertIsNone(result["ai_response"])

    # ---- normal flow -------------------------------------------------------

    def test_normal_assessment(self):
        engine = self.make([reply("urgent", "70%", guidance="See a GP today.")])
        result = engine.process(HEALTH_TEXT)
        self.assertEqual(result["urgency"], "urgent")
        self.assertEqual(result["urgency_classification"], "urgent")
        self.assertAlmostEqual(result["certainty"], 0.7)
        self.assertTrue(result["is_health_related"] and result["is_relevant"])
        self.assertFalse(result["is_emergency"] or result["has_follow_up"])
        self.assertEqual(result["exchanges"][0]["user_input"], HEALTH_TEXT)
        self.assertIn("See a GP today.", result["ai_response"])
        self.assertIsNone(result["validation"])             # no guidelines given -> no cross-check

    def test_input_is_stripped(self):
        engine = self.make([reply()])
        engine.process("   " + HEALTH_TEXT + "  \n")
        self.assertEqual(self.ai.received, [HEALTH_TEXT])

    def test_emergency_from_the_ai(self):
        result = self.make([reply("emergency", "95%")]).process(HEALTH_TEXT)
        self.assertTrue(result["is_emergency"])
        self.assertEqual(result["urgency"], "emergency")

    def test_ai_failure(self):
        result = self.make([]).process(HEALTH_TEXT)
        self.assertIsNone(result["ai_response"])
        self.assertTrue(result["is_health_related"])
        self.assertIn("AI service could not respond", IO.text())

    # ---- follow-up questions ----------------------------------------------

    def test_follow_up_question_flow(self):
        IO.answers = ["two days"]
        engine = self.make([reply("urgent", follow_up="How long has it lasted?"),
                            reply("non-urgent", "90%")])
        result = engine.process(HEALTH_TEXT)
        self.assertIn(("get_additional_input", "How long has it lasted?"), IO.calls)
        self.assertEqual(self.ai.received[1], "two days")
        self.assertEqual(len(result["exchanges"]), 2)
        self.assertEqual(result["exchanges"][1]["user_input"], "two days")
        self.assertEqual(result["urgency"], "non-urgent")        # the LAST reply decides

    def test_emergency_in_a_follow_up_answer(self):
        IO.answers = ["now he is unconscious"]
        engine = self.make([reply("urgent", follow_up="Any other symptoms?"), reply()])
        result = engine.process(HEALTH_TEXT)
        self.assertTrue(result["is_emergency"])
        self.assertEqual(len(self.ai.received), 1)               # the AI is not asked again
        self.assertEqual(len(result["exchanges"]), 2)

    def test_follow_up_loop_is_capped(self):
        IO.answers = ["answer"] * 20
        always_asks = [reply("urgent", follow_up="Another question?")] * 20
        engine = self.make(always_asks, max_follow_ups=3)
        result = engine.process(HEALTH_TEXT)
        self.assertEqual(len(self.ai.received), 1 + 3)           # first answer + 3 follow-ups
        self.assertEqual(len(result["exchanges"]), 4)

    def test_default_follow_up_cap_comes_from_keywords(self):
        IO.answers = ["answer"] * 20
        engine = self.make([reply("urgent", follow_up="More?")] * 20)
        engine.process(HEALTH_TEXT)
        self.assertEqual(len(self.ai.received), 1 + keywords.MAX_FOLLOW_UPS)

    def test_ai_failure_during_follow_up(self):
        IO.answers = ["two days"]
        engine = self.make([reply("urgent", follow_up="How long?")])      # no second reply
        result = engine.process(HEALTH_TEXT)
        self.assertIsNone(result["ai_response"])
        self.assertEqual(len(result["exchanges"]), 1)                     # the first exchange is kept
        self.assertIn("could not process the follow-up", IO.text())

    # ---- age handling -------------------------------------------------------

    def test_age_note_is_sent_to_the_ai(self):
        engine = self.make([reply()])
        result = engine.process(HEALTH_TEXT, age=70)
        self.assertIn("High risk age group", self.ai.received[0])
        self.assertEqual(result["age_risk"], "High risk age group")

    def test_age_note_for_normal_age(self):
        engine = self.make([reply()])
        result = engine.process(HEALTH_TEXT, age=30)
        self.assertIn("Not high risk age group", self.ai.received[0])
        self.assertEqual(result["age_risk"], "Not high risk age group")

    def test_no_age_note_when_age_missing_or_invalid(self):
        for age in (None, "abc"):
            with self.subTest(age=age):
                engine = self.make([reply()])
                engine.process(HEALTH_TEXT, age=age)
                self.assertNotIn("Note:", self.ai.received[0])

    def test_logged_text_does_not_contain_the_age_note(self):
        engine = self.make([reply()])
        result = engine.process(HEALTH_TEXT, age=70)
        self.assertEqual(result["exchanges"][0]["user_input"], HEALTH_TEXT)

    # ---- saving ---------------------------------------------------------------

    def test_save_exchanges_logs_every_exchange_to_the_current_case(self):
        case = {"case_id": "case_1", "logs": []}
        engine = self.make(case=case)
        engine.save_exchanges([{"user_input": "a", "ai_response": "b"}, {"user_input": "c", "ai_response": "d"}])
        self.assertEqual(self.repo.calls, [("add_log", case, "a", "b"), ("add_log", case, "c", "d")])

    def test_engine_exposes_case_and_chat(self):
        case = {"case_id": "case_1", "logs": []}
        engine = self.make(case=case)
        self.assertIs(engine.case, case)
        self.assertEqual(engine.chat, "chat-object")

    # ---- case relevance / switching --------------------------------------------

    def old_case(self):
        return {"case_id": "case_old", "logs": [{"user_input": "old chest problem", "ai_response": "x"}]}

    def test_relevant_input_keeps_the_case(self):
        case = self.old_case()
        engine = self.make([reply()], relevant=True, case=case)
        engine.process(HEALTH_TEXT)
        self.assertIs(engine.case, case)
        self.assertNotIn("ask_yes_no", [call[0] for call in IO.calls])

    def test_unrelated_input_and_user_continues_the_case(self):
        case = self.old_case()
        IO.yes_no = [True]
        engine = self.make([reply()], relevant=False, case=case)
        engine.process(HEALTH_TEXT)
        self.assertIs(engine.case, case)
        self.assertEqual(self.repo.calls, [])
        self.assertIn("Continuing with case_old", IO.text())

    def test_unrelated_input_and_user_starts_a_new_case(self):
        case = self.old_case()
        IO.yes_no = [False]
        engine = self.make([reply()], relevant=False, case=case)
        engine.process(HEALTH_TEXT)
        new_case = self.repo.created[0]
        self.assertIs(engine.case, new_case)
        self.assertIn(("close_case", case), self.repo.calls)
        self.assertIn(("add_log", new_case, HEALTH_TEXT, ""), self.repo.calls)

    def test_case_objects_work_as_well_as_dicts(self):
        case = SimpleNamespace(case_id="case_obj", logs=[SimpleNamespace(user_input="old problem")])
        IO.yes_no = [False]
        engine = self.make([reply()], relevant=False, case=case)
        engine.process(HEALTH_TEXT)
        self.assertIn("case_obj", IO.text())
        self.assertIs(engine.case, self.repo.created[0])

    def test_case_without_logs_is_never_checked_for_relevance(self):
        engine = self.make([reply()], relevant=False, case={"case_id": "c", "logs": []})
        engine.process(HEALTH_TEXT)
        self.assertEqual(IO.calls, [])

    def test_active_case_from_the_repository_is_used_when_no_case_is_set(self):
        IO.yes_no = [False]
        repo = FakeRepository(active=self.old_case())
        engine = self.make([reply()], relevant=False, repo=repo)
        engine.process(HEALTH_TEXT)
        self.assertEqual(len(repo.created), 1)


# ===========================================================================
# 4. Guideline repository + validators
# ===========================================================================

class TestGuidelineRepository(BaseTest):
    def setUp(self):
        super().setUp()
        self.repo = GuidelineRepository(GUIDELINE_DIR)

    def ids(self, text):
        return sorted(record["id"] for record in self.repo.find_symptom_records(text))

    def test_loads_the_records(self):
        self.assertEqual(len(self.repo.symptom_records), len(SYMPTOM_DATA))
        self.assertEqual(self.repo.get_service_record("SCDF-EMS-001")["topic"], "Calling 995")
        self.assertIsNone(self.repo.get_service_record("DOES-NOT-EXIST"))

    def test_find_records_by_keyword(self):
        self.assertIn("T-HEADACHE", self.ids("I have a headache"))
        self.assertIn("T-COUGH", self.ids("a dry cough since Monday"))
        self.assertEqual(self.ids("my knee feels odd"), [])

    def test_records_for_professionals_are_excluded(self):
        self.assertNotIn("T-PRO", self.ids("headache"))
        found = self.repo.find_symptom_records("headache", audience="healthcare_professionals")
        self.assertEqual([r["id"] for r in found], ["T-PRO"])

    def test_negated_mentions_do_not_match(self):
        self.assertNotIn("T-CHEST", self.ids("I have no chest pain"))
        self.assertNotIn("T-CHEST", self.ids("denies chest pain or breathlessness"))
        self.assertIn("T-CHEST", self.ids("no fever but chest pain"))

    def test_word_forms_and_synonyms(self):
        self.assertIn("T-ABDOMINAL", self.ids("my stomach pain is bad"))          # stomach -> abdominal
        self.assertIn("T-HEADACHE", self.ids("recurring headaches"))               # plural
        self.assertEqual(self.repo.matched_phrases(["Blood in vomit."], "I vomited blood"), ["Blood in vomit."])

    def test_and_or_conditions_match_either_side(self):
        phrase = ["Weakness and/or numbness."]
        self.assertEqual(self.repo.matched_phrases(phrase, "numbness in my arm"), phrase)
        self.assertEqual(self.repo.matched_phrases(phrase, "weakness on one side"), phrase)

    def test_all_words_of_a_condition_are_required(self):
        phrase = ["Sudden and severe abdominal pain."]
        self.assertEqual(self.repo.matched_phrases(phrase, "mild stomach pain"), [])
        self.assertEqual(self.repo.matched_phrases(phrase, "sudden severe stomach pain"), phrase)

    def test_conditions_containing_a_negation_are_skipped(self):
        self.assertEqual(self.repo.matched_phrases(["Vomiting that does not subside."], "vomiting that does not subside"), [])

    def test_non_string_text_is_safe(self):
        self.assertEqual(self.repo.find_symptom_records(None), [])
        self.assertEqual(self.repo.matched_phrases(["Chest pain."], 42), [])
        self.assertFalse(self.repo.mentions(None, "995"))

    def test_mentions(self):
        self.assertTrue(self.repo.mentions("Please call 995 now", "995"))
        self.assertFalse(self.repo.mentions("You do not need to call 995", "995"))

    def test_record_helpers(self):
        record = SYMPTOM_DATA[0]
        self.assertIn("Severe headache.", self.repo.red_flag_conditions(record, "emergency_department"))
        self.assertEqual(self.repo.red_flag_conditions(record, "no_such_level"), [])
        self.assertTrue(self.repo.needs_review(record))
        self.assertFalse(self.repo.needs_review(SYMPTOM_DATA[4]))              # review_status 'reviewed'
        self.assertIn("T-HEADACHE", self.repo.source_label(record))
        self.assertIn("Test Ministry", self.repo.source_label(record))
        details = self.repo.source_details(record)
        self.assertEqual(details["id"], "T-HEADACHE")
        self.assertEqual(details["source_url"], "https://example.test/t-headache")

    def test_loading_problems_raise_clear_errors(self):
        with self.assertRaises(OSError):
            GuidelineRepository(os.path.join(GUIDELINE_DIR, "missing"))
        bad = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, bad, True)
        for name in ("symptom_guidelines.json", "care_recommendations.json"):
            with open(os.path.join(bad, name), "w") as handle:
                handle.write("{}")                                     # valid JSON, but not a list
        with self.assertRaises(ValueError):
            GuidelineRepository(bad)
        with open(os.path.join(bad, "symptom_guidelines.json"), "w") as handle:
            handle.write("not json")
        with self.assertRaises(ValueError):                           # JSONDecodeError is a ValueError
            GuidelineRepository(bad)


class TestValidators(BaseTest):
    def setUp(self):
        super().setUp()
        self.repo = GuidelineRepository(GUIDELINE_DIR)

    def test_response_validator_is_abstract(self):
        with self.assertRaises(TypeError):
            ResponseValidator(self.repo)

    # ---- UrgencyValidator ---------------------------------------------------

    def test_red_flag_in_emergency_department_list(self):
        findings = UrgencyValidator(self.repo).validate(AIResponse(reply("non-urgent")),
                                                        "severe headache and chest pain")
        flags = [f for f in findings if f["type"] == "red_flag"]
        self.assertTrue(flags)
        self.assertTrue(all(f["min_urgency"] == "urgent" for f in flags))
        self.assertTrue(all(f["source"] and f["needs_review"] for f in flags))
        self.assertEqual(flags[0]["validator"], "UrgencyValidator")
        self.assertIn("source_details", flags[0])

    def test_red_flag_in_emergency_response_list(self):
        findings = UrgencyValidator(self.repo).validate(AIResponse(reply("non-urgent")), "she had a seizure")
        self.assertIn("emergency", [f["min_urgency"] for f in findings])

    def test_consistent_when_no_warning_signs(self):
        findings = UrgencyValidator(self.repo).validate(AIResponse(reply()), "a mild headache for two days")
        self.assertEqual([f["type"] for f in findings], ["consistent"])
        self.assertIsNone(findings[0]["min_urgency"])

    def test_no_match(self):
        findings = UrgencyValidator(self.repo).validate(AIResponse(reply()), "my knee feels odd")
        self.assertEqual([f["type"] for f in findings], ["no_match"])
        self.assertIsNone(findings[0]["source"])

    def test_urgency_validator_never_raises_on_odd_text(self):
        for value in (None, 42, ""):
            with self.subTest(value=value):
                self.assertEqual(UrgencyValidator(self.repo).validate(AIResponse(reply()), value)[0]["type"], "no_match")

    # ---- ServiceAdviceValidator ------------------------------------------------

    def service(self, today=date(2026, 11, 16)):
        return ServiceAdviceValidator(self.repo, today=today)

    def test_995_for_a_non_emergency_is_flagged(self):
        findings = self.service().validate(AIResponse(reply("non-urgent", guidance="Call 995 for an ambulance.")),
                                           "I have a toothache")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["type"], "note")
        self.assertIn("non-emergency", findings[0]["message"])
        self.assertIsNone(findings[0]["min_urgency"])

    def test_995_is_fine_when_a_serious_sign_is_present(self):
        findings = self.service().validate(AIResponse(reply("non-urgent", guidance="Call 995.")),
                                           "loss of consciousness and a toothache")
        self.assertEqual(findings, [])

    def test_995_is_fine_when_the_ai_says_emergency(self):
        self.assertEqual(self.service().validate(AIResponse(reply("emergency", guidance="Call 995.")), "toothache"), [])

    def test_negated_995_mention_is_ignored(self):
        findings = self.service().validate(AIResponse(reply(guidance="You do not need to call 995.")), "toothache")
        self.assertEqual(findings, [])

    def test_1777_hotline_before_and_after_it_ends(self):
        advice = AIResponse(reply("urgent", guidance="Call the 1777 hotline."))
        before = self.service(date(2026, 11, 16)).validate(advice, "fever")
        self.assertIn("will cease on 2027-01-01", before[0]["message"])
        self.assertIn("6262 6262", before[0]["message"])
        after = self.service(date(2027, 2, 1)).validate(advice, "fever")
        self.assertIn("has ceased", after[0]["message"])

    def test_no_findings_for_ordinary_advice(self):
        self.assertEqual(self.service().validate(AIResponse(reply(guidance="Rest at home.")), "toothache"), [])


# ===========================================================================
# 5. Guideline cross-check inside the engine
# ===========================================================================

class TestEngineWithGuidelines(BaseTest):
    def setUp(self):
        super().setUp()
        self.guidelines = GuidelineRepository(GUIDELINE_DIR)

    def run_engine(self, urgency, symptoms):
        engine = AssessmentEngine(ScriptedAIService([reply(urgency)]), FakeRepository(), None, "chat",
                                  guidelines=self.guidelines)
        return engine.process("symptoms: " + symptoms)

    def test_urgency_is_raised_when_the_ai_is_too_low(self):
        result = self.run_engine("non-urgent", "severe headache and chest pain")
        self.assertEqual(result["urgency"], "urgent")
        self.assertEqual(result["urgency_classification"], "urgent")
        self.assertTrue(result["validation"]["escalated"])
        self.assertEqual(result["validation"]["urgency_before"], "non-urgent")
        self.assertEqual(result["validation"]["urgency_after"], "urgent")

    def test_the_ai_text_is_never_rewritten(self):
        result = self.run_engine("non-urgent", "severe headache and chest pain")
        self.assertIn("Urgency classification: non-urgent", result["ai_response"])

    def test_urgency_is_never_lowered(self):
        result = self.run_engine("emergency", "mild headache")
        self.assertEqual(result["urgency"], "emergency")
        self.assertFalse(result["validation"]["escalated"])

    def test_no_change_when_there_is_no_warning_sign(self):
        result = self.run_engine("non-urgent", "mild headache")
        self.assertEqual(result["urgency"], "non-urgent")
        self.assertFalse(result["validation"]["escalated"])

    def test_escalation_to_emergency_sets_is_emergency(self):
        result = self.run_engine("urgent", "she had a seizure")
        self.assertEqual(result["urgency"], "emergency")
        self.assertTrue(result["is_emergency"])

    def test_insufficient_information_is_also_raised(self):
        result = self.run_engine("insufficient information", "severe headache")
        self.assertEqual(result["urgency"], "urgent")

    def test_validation_summary_fields(self):
        validation = self.run_engine("non-urgent", "severe headache")["validation"]
        self.assertTrue(validation["needs_review"])
        self.assertTrue(validation["findings"])

    def test_findings_use_what_the_patient_said_in_follow_ups_too(self):
        IO.answers = ["it is severe"]
        engine = AssessmentEngine(
            ScriptedAIService([reply("non-urgent", follow_up="How bad is it?"), reply("non-urgent")]),
            FakeRepository(), None, "chat", guidelines=self.guidelines)
        result = engine.process("symptoms: headache")
        self.assertEqual(result["urgency"], "urgent")

    def test_emergency_service_guidance(self):
        engine = AssessmentEngine(ScriptedAIService([]), FakeRepository(), None, "chat", guidelines=self.guidelines)
        advice = engine.emergency_service_guidance()
        self.assertEqual(len(advice["recommendations"]), 3)
        self.assertTrue(advice["recommendations"][0].startswith("Call 995"))
        self.assertEqual(advice["source_url"], "https://example.test/scdf-ems")
        self.assertTrue(advice["needs_review"])

    def test_emergency_service_guidance_without_data(self):
        engine = AssessmentEngine(ScriptedAIService([]), FakeRepository(), None, "chat")
        self.assertIsNone(engine.emergency_service_guidance())

    def test_emergency_service_guidance_when_the_record_is_missing(self):
        empty = mock.Mock()
        empty.get_service_record.return_value = None
        engine = AssessmentEngine(ScriptedAIService([]), FakeRepository(), None, "chat", guidelines=empty)
        self.assertIsNone(engine.emergency_service_guidance())


# ===========================================================================
# 6. MenuController
# ===========================================================================

class FakeEngine:
    """Stands in for AssessmentEngine so the menu can be tested on its own."""

    def __init__(self, result=None, advice=None):
        self.result = result
        self.advice = advice
        self.process_calls = []
        self.saved = []
        self.case = None
        self.chat = None

    def process(self, prompt, age=None):
        self.process_calls.append((prompt, age))
        return self.result

    def save_exchanges(self, exchanges):
        self.saved.append(exchanges)

    def emergency_service_guidance(self):
        return self.advice


def make_result(**overrides):
    result = {"ai_response": reply(), "urgency": "non-urgent", "certainty": 0.8, "is_relevant": True,
              "has_follow_up": False, "is_health_related": True, "is_emergency": False,
              "exchanges": [{"user_input": "u", "ai_response": "a"}], "validation": None,
              "urgency_classification": "non-urgent"}
    result.update(overrides)
    return result


def make_finding(**overrides):
    finding = {"validator": "UrgencyValidator", "type": "red_flag", "message": "Chest pain needs care.",
               "source": "Test Ministry - T-1, last updated 2025-01-02", "min_urgency": "urgent",
               "needs_review": True,
               "source_details": {"id": "T-1", "source_name": "Test Ministry", "source_url": "https://example.test/t1"}}
    finding.update(overrides)
    return finding


class TestMenuController(BaseTest):
    def menu(self, engine=None, repo=None, profile=None):
        self.engine = engine or FakeEngine(make_result())
        self.repo = repo or FakeRepository()
        return MenuController(self.engine, self.repo, profile)

    # ---- dispatch -------------------------------------------------------------

    def test_invalid_option(self):
        self.assertFalse(self.menu().handle("99"))
        self.assertIn("Invalid menu option.", IO.output)
        self.assertFalse(self.menu().handle(""))

    def test_only_the_exit_option_returns_true(self):
        self.assertTrue(self.menu().handle("6"))
        for choice in ("1", "2", "3", "4", "5"):
            with self.subTest(choice=choice):
                IO.reset()
                self.assertFalse(self.menu().handle(choice))

    def test_engine_property(self):
        menu = self.menu()
        self.assertIs(menu.engine, self.engine)

    # ---- option 1: assessment -----------------------------------------------------

    def test_assessment_passes_the_user_profile_and_age(self):
        IO.patient = {"age": 41, "symptoms": "fever"}
        IO.prompt = "PROMPT TEXT"
        profile = {"email": "ann@example.com", "full_name": "Ann"}
        menu = self.menu(profile=profile)
        menu.handle("1")
        self.assertIn(("input_manager", profile), IO.calls)
        self.assertEqual(self.engine.process_calls, [("PROMPT TEXT", 41)])

    def test_assessment_age_is_none_when_patient_data_is_not_a_dict(self):
        IO.patient = SimpleNamespace(age=41)
        self.menu().handle("1")
        self.assertEqual(self.engine.process_calls[0][1], None)

    def test_assessment_failure_message(self):
        menu = self.menu(FakeEngine(make_result(ai_response=None)))
        menu.handle("1")
        self.assertIn("Unable to complete the assessment", IO.text())
        self.assertEqual(self.engine.saved, [])

    def test_assessment_saves_and_prints_the_result(self):
        menu = self.menu(FakeEngine(make_result(ai_response=reply("urgent", "70%", guidance="See a GP today."),
                                                 urgency_classification="urgent", certainty=0.7)))
        menu.handle("1")
        text = IO.text()
        self.assertEqual(self.engine.saved, [[{"user_input": "u", "ai_response": "a"}]])
        self.assertIn("=== Assessment Result ===", text)
        self.assertIn("Urgency classification: urgent - certainty 70%", text)
        self.assertIn("See a GP today.", IO.output)
        self.assertNotIn("Emergency Advice", text)

    def test_assessment_shows_age_risk_and_skips_zero_certainty(self):
        menu = self.menu(FakeEngine(make_result(age_risk="High risk age group", certainty=0.0)))
        menu.handle("1")
        self.assertIn("Age Risk: High risk age group", IO.output)
        self.assertIn("Urgency classification: non-urgent", IO.output)         # no ' - certainty'

    def test_whole_reply_is_shown_when_there_is_no_guidance_section(self):
        message = "I'm sorry, but that question does not appear to be health-related."
        menu = self.menu(FakeEngine(make_result(ai_response=message, is_health_related=False)))
        menu.handle("1")
        self.assertIn(message, IO.output)
        self.assertNotIn("None", IO.output)
        self.assertNotIn("Urgency classification", IO.text())                   # only for health questions

    def test_raised_urgency_is_mentioned(self):
        validation = {"urgency_before": "non-urgent", "urgency_after": "urgent", "escalated": True,
                      "findings": [make_finding()], "needs_review": True}
        menu = self.menu(FakeEngine(make_result(urgency_classification="urgent", validation=validation)))
        menu.handle("1")
        text = IO.text()
        self.assertIn("raised after the guideline check", text)
        self.assertIn("Urgency raised from 'non-urgent' to 'urgent'", text)

    def test_non_emergency_guideline_check_shows_a_short_citation(self):
        validation = {"urgency_before": "non-urgent", "urgency_after": "non-urgent", "escalated": False,
                      "findings": [make_finding()], "needs_review": True}
        menu = self.menu(FakeEngine(make_result(validation=validation)))
        menu.handle("1")
        text = IO.text()
        self.assertIn("=== Guideline Check ===", text)
        self.assertIn("T-1 | Test Ministry | https://example.test/t1", text)
        self.assertNotIn("Chest pain needs care.", text)                       # message only for emergencies
        self.assertIn("professional review", text)

    def test_emergency_guideline_check_shows_the_findings(self):
        validation = {"urgency_before": "emergency", "urgency_after": "emergency", "escalated": False,
                      "findings": [make_finding()], "needs_review": False}
        menu = self.menu(FakeEngine(make_result(is_emergency=True, validation=validation)))
        menu.handle("1")
        self.assertIn("- Chest pain needs care. [Test Ministry - T-1, last updated 2025-01-02]", IO.output)
        self.assertNotIn("professional review", IO.text())

    def test_guideline_check_is_hidden_when_there_is_nothing_to_show(self):
        for validation in (None, {"findings": []}):
            with self.subTest(validation=validation):
                IO.reset()
                self.menu(FakeEngine(make_result(validation=validation))).handle("1")
                self.assertNotIn("Guideline Check", IO.text())

    def test_emergency_advice_is_printed(self):
        advice = {"recommendations": ["Call 995 now.", "Stay on the line."],
                  "source_url": "https://example.test/scdf", "needs_review": True}
        menu = self.menu(FakeEngine(make_result(is_emergency=True), advice=advice))
        menu.handle("1")
        text = IO.text()
        self.assertIn("=== Emergency Advice (Singapore) ===", text)
        self.assertIn("call 995", text)
        self.assertIn("- Call 995 now.", IO.output)
        self.assertIn("- Stay on the line.", IO.output)
        self.assertIn("Source: https://example.test/scdf", IO.output)
        self.assertIn("does not replace instructions from emergency responders", text)

    def test_emergency_advice_without_data_prints_no_block(self):
        self.menu(FakeEngine(make_result(is_emergency=True), advice=None)).handle("1")
        self.assertNotIn("Emergency Advice", IO.text())

    def test_emergency_advice_without_source_or_review_note(self):
        advice = {"recommendations": ["Call 995 now."], "source_url": None, "needs_review": False}
        self.menu(FakeEngine(make_result(is_emergency=True), advice=advice)).handle("1")
        self.assertNotIn("Source:", IO.text())
        self.assertNotIn("does not replace", IO.text())

    # ---- option 2: list cases ----------------------------------------------------------

    def test_list_cases(self):
        self.menu().handle("2")
        self.assertIn(("print_cases",), IO.calls)

    # ---- option 3: search -----------------------------------------------------------------

    def test_search_with_results(self):
        records = [{"case_id": "case_1"}]
        menu = self.menu(repo=FakeRepository(records=records))
        IO.keyword = "headache"
        menu.handle("3")
        self.assertEqual(self.repo.calls, [("search", "headache"), ("show_history", records)])

    def test_search_without_results(self):
        IO.keyword = "unicorn"
        self.menu().handle("3")
        self.assertIn("No matching records found for 'unicorn'.", IO.text())
        self.assertEqual(self.repo.names(), ["search"])

    # ---- option 4: export -----------------------------------------------------------------

    def test_export_with_zero_or_one_case_exports_everything_straight_away(self):
        for choices in ([], [{"case_id": "case_1"}]):
            with self.subTest(choices=choices):
                IO.reset()
                self.menu(repo=FakeRepository(export_choices=choices)).handle("4")
                self.assertEqual(self.repo.calls, [("export_csv", None)])
                self.assertNotIn("choose_cases", [c[0] for c in IO.calls])

    def test_export_with_several_cases_exports_the_chosen_ones(self):
        choices = [{"case_id": "case_1"}, {"case_id": "case_2"}]
        IO.chosen_cases = ["case_2"]
        self.menu(repo=FakeRepository(export_choices=choices)).handle("4")
        self.assertIn(("choose_cases", choices), IO.calls)
        self.assertEqual(self.repo.calls, [("export_csv", ["case_2"])])

    def test_export_can_be_cancelled(self):
        choices = [{"case_id": "case_1"}, {"case_id": "case_2"}]
        IO.chosen_cases = []
        self.menu(repo=FakeRepository(export_choices=choices)).handle("4")
        self.assertIn("Export cancelled.", IO.output)
        self.assertEqual(self.repo.calls, [])

    # ---- option 5: statistics ---------------------------------------------------------------

    def test_statistics_without_breakdown(self):
        IO.filter, IO.yes_no = "fever", [False]
        self.menu().handle("5")
        self.assertEqual(self.repo.calls, [("show_stats", "fever", False)])

    def test_statistics_with_per_case_breakdown(self):
        IO.filter, IO.yes_no = "fever", [True]
        self.menu().handle("5")
        self.assertEqual(self.repo.calls, [("show_stats", "fever", False), ("show_stats", "fever", True)])

    def test_statistics_error_is_reported_not_raised(self):
        repo = FakeRepository()
        repo.stats_error = ValueError("No data for that filter")
        self.assertFalse(self.menu(repo=repo).handle("5"))
        self.assertIn("\n[Stats] No data for that filter", IO.output)


# ===========================================================================
# 7. CaseRepository + logic_manager_oop wrapper functions
# ===========================================================================

class TestCaseRepository(BaseTest):
    def setUp(self):
        super().setUp()
        self.repo = CaseRepository()

    def test_cases_are_created_and_closed(self):
        self.assertEqual(self.repo.create_case(), {"case_id": "case_new_1", "logs": []})
        self.repo.close_case("the-case")
        self.assertIn(("close_case", "the-case"), DATA.calls)

    def test_active_case(self):
        self.assertIsNone(self.repo.get_active_case())
        DATA.active_case = {"case_id": "case_9"}
        self.assertEqual(self.repo.get_active_case(), {"case_id": "case_9"})

    def test_add_log(self):
        self.repo.add_log("case", "question", "answer")
        self.assertIn(("add_log", "case", "question", "answer"), DATA.calls)

    def test_search_and_history(self):
        DATA.records = [{"case_id": "c"}]
        self.assertEqual(self.repo.search("fever"), [{"case_id": "c"}])
        self.repo.show_history(DATA.records)
        self.assertIn(("show_history", DATA.records), DATA.calls)

    def test_export_choices_and_csv(self):
        DATA.export_choices = [{"case_id": "c"}]
        self.assertEqual(self.repo.export_choices(), [{"case_id": "c"}])
        self.repo.export_csv()
        self.repo.export_csv(["c"])
        self.assertEqual([c for c in DATA.calls if c[0] == "csv"],
                         [("csv", (), {"case_ids": None}), ("csv", (), {"case_ids": ["c"]})])

    def test_statistics_and_invalid_query_error(self):
        self.repo.show_stats("fever", per_case=True)
        self.assertIn(("show_stats", "fever", True), DATA.calls)
        DATA.stats_error = ValueError("bad query")
        with self.assertRaises(ValueError):
            self.repo.show_stats("???")


class TestLogicManagerFunctions(BaseTest):
    """The old function-style API kept in logic_manager_oop.py."""

    def setUp(self):
        super().setUp()
        lm._guidelines_cache.clear()
        self.addCleanup(lm._guidelines_cache.clear)

    def test_detector_wrappers(self):
        self.assertTrue(lm.is_health_related("I have a headache"))
        self.assertFalse(lm.is_health_related(NOT_HEALTH_TEXT))
        self.assertTrue(lm.contains_emergency_keywords(EMERGENCY_TEXT))
        self.assertFalse(lm.contains_emergency_keywords("a mild cough"))
        self.assertTrue(lm.is_memory_question("what do you remember"))
        self.assertFalse(lm.is_memory_question("I have a headache"))

    def test_age_wrapper(self):
        self.assertEqual(lm.is_high_risk_age(70), "High risk age group")
        self.assertEqual(lm.is_high_risk_age("x"), "Unknown")

    def test_parsing_wrappers(self):
        text = reply("urgent", "75%", "How long?", "See a doctor.")
        self.assertEqual(lm.get_urgency(text), "urgent")
        self.assertAlmostEqual(lm.get_certainty(text), 0.75)
        self.assertEqual(lm.extract_follow_up_question(text), "How long?")
        self.assertTrue(lm.has_follow_up_question(text))
        self.assertEqual(lm.extract_section(text, "Next-Step Guidance:"), "See a doctor.")

    def test_is_emergency_wrapper_does_not_treat_urgent_as_emergency(self):
        self.assertTrue(lm.is_emergency(reply("emergency")))
        self.assertFalse(lm.is_emergency(reply("urgent")))

    def test_is_answer_relevant(self):
        self.assertTrue(lm.is_answer_relevant("my head hurts", "head pain can have many causes"))
        self.assertFalse(lm.is_answer_relevant("my head hurts", "the weather is nice"))

    def test_is_case_related(self):
        self.assertTrue(lm.is_case_related("anything", None))
        self.assertTrue(lm.is_case_related("anything", {"logs": []}))
        case = {"logs": [{"user_input": "x"}]}
        self.assertTrue(lm.is_case_related("what do you remember", case))       # memory question
        with mock.patch.object(lm, "check_relevance", return_value=False) as check:
            self.assertFalse(lm.is_case_related("I have a headache", case))
            check.assert_called_once_with("I have a headache", case)

    def test_get_guidelines_loads_once_and_caches(self):
        with mock.patch.object(lm, "GuidelineRepository", return_value="repo") as factory:
            self.assertEqual(lm.get_guidelines(), "repo")
            self.assertEqual(lm.get_guidelines(), "repo")
            factory.assert_called_once()
            self.assertTrue(factory.call_args[0][0].endswith("medical_data"))

    def test_get_guidelines_warns_and_returns_none_when_files_are_missing(self):
        with mock.patch.object(lm, "GuidelineRepository", side_effect=FileNotFoundError("no file")):
            self.assertIsNone(lm.get_guidelines())
            self.assertIsNone(lm.get_guidelines())                              # cached: warns only once
        self.assertEqual(sum("could not be loaded" in str(o) for o in IO.output), 1)
        self.assertIn("will not be cross-checked", IO.text())

    def test_build_menu_wires_the_objects(self):
        ai = ScriptedAIService([])
        menu = lm.build_menu(ai_service=ai, repository=FakeRepository(), case={"case_id": "c", "logs": []},
                             chat="chat", user_profile={"email": "a@b.com"}, guidelines=False)
        self.assertIsInstance(menu, MenuController)
        self.assertEqual(menu.engine.case, {"case_id": "c", "logs": []})
        self.assertEqual(menu.engine.chat, "chat")
        self.assertIsNone(menu.engine.emergency_service_guidance())             # guidelines=False -> switched off

    def test_build_menu_uses_the_loaded_guidelines_by_default(self):
        with mock.patch.object(lm, "get_guidelines", return_value=GuidelineRepository(GUIDELINE_DIR)):
            menu = lm.build_menu(ai_service=ScriptedAIService([]), repository=FakeRepository())
        self.assertIsNotNone(menu.engine.emergency_service_guidance())

    def test_menu_selection_exit_and_invalid(self):
        with mock.patch.object(lm, "get_guidelines", return_value=None):
            self.assertEqual(lm.menu_selection("6", "case", "chat"), ("case", "chat", True))
            self.assertEqual(lm.menu_selection("99", "case", "chat", {"email": "a@b.com"}), ("case", "chat", False))
        self.assertIn("Invalid menu option.", IO.output)

    def test_menu_selection_passes_the_user_profile_to_the_assessment(self):
        profile = {"email": "ann@example.com"}
        with mock.patch.object(lm, "get_guidelines", return_value=None):
            lm.menu_selection("1", {"case_id": "c", "logs": []}, "chat", profile)
        self.assertIn(("input_manager", profile), IO.calls)

    def test_process_interaction(self):
        with mock.patch.object(lm, "get_guidelines", return_value=None):
            self.assertIsNone(lm.process_interaction("", "chat")["ai_response"])
            result = lm.process_interaction(EMERGENCY_TEXT, "chat")
        self.assertTrue(result["is_emergency"])


# ===========================================================================
# 8. Authentication
# ===========================================================================

class TestPasswordHashers(BaseTest):
    def hashers(self):
        from Logic.pbkdf2_password_hasher import Pbkdf2PasswordHasher
        hashers = [Pbkdf2PasswordHasher(iterations=1000)]
        try:
            from Logic.argon2_password_hasher import Argon2PasswordHasher
            hashers.append(Argon2PasswordHasher())
        except ImportError:
            pass                                    # argon2-cffi not installed: test PBKDF2 only
        return hashers

    def test_password_hasher_is_abstract(self):
        from Logic.password_hasher import PasswordHasher
        with self.assertRaises(TypeError):
            PasswordHasher()

    def test_hash_and_verify(self):
        for hasher in self.hashers():
            with self.subTest(hasher=type(hasher).__name__):
                stored = hasher.hash_password("S3cret!pass")
                self.assertNotIn("S3cret!pass", stored)
                self.assertTrue(hasher.verify_password("S3cret!pass", stored))
                self.assertFalse(hasher.verify_password("wrong", stored))
                self.assertFalse(hasher.verify_password("", stored))

    def test_each_hash_uses_a_new_salt(self):
        for hasher in self.hashers():
            with self.subTest(hasher=type(hasher).__name__):
                self.assertNotEqual(hasher.hash_password("same"), hasher.hash_password("same"))

    def test_empty_or_non_string_passwords_are_refused(self):
        for hasher in self.hashers():
            for bad in ("", None, 123):
                with self.subTest(hasher=type(hasher).__name__, bad=bad):
                    with self.assertRaises(ValueError):
                        hasher.hash_password(bad)

    def test_verify_never_raises_on_bad_stored_values(self):
        for hasher in self.hashers():
            for stored in (None, "", "garbage", "md5$1$a$b", 123):
                with self.subTest(hasher=type(hasher).__name__, stored=stored):
                    self.assertFalse(hasher.verify_password("pw", stored))
            self.assertFalse(hasher.verify_password(None, "x"))

    def test_needs_rehash(self):
        for hasher in self.hashers():
            with self.subTest(hasher=type(hasher).__name__):
                self.assertFalse(hasher.needs_rehash(hasher.hash_password("pw")))
                self.assertTrue(hasher.needs_rehash("garbage"))

    def test_pbkdf2_hash_with_more_iterations_is_current_and_fewer_needs_rehash(self):
        from Logic.pbkdf2_password_hasher import Pbkdf2PasswordHasher
        weak, strong = Pbkdf2PasswordHasher(iterations=1000), Pbkdf2PasswordHasher(iterations=2000)
        self.assertTrue(strong.needs_rehash(weak.hash_password("pw")))
        self.assertFalse(weak.needs_rehash(strong.hash_password("pw")))
        self.assertTrue(strong.verify_password("pw", weak.hash_password("pw")))   # old hashes still work


class TestAuthService(BaseTest):
    def setUp(self):
        super().setUp()
        from Logic.auth_service import AuthService
        from Logic.in_memory_user_repository import InMemoryUserRepository
        from Logic.pbkdf2_password_hasher import Pbkdf2PasswordHasher
        self.users = InMemoryUserRepository()
        self.hasher = Pbkdf2PasswordHasher(iterations=1000)
        self.auth = AuthService(self.hasher, self.users)

    def test_register_and_sign_in(self):
        self.assertTrue(self.auth.register("ann@example.com", "Pw12345!", {"full_name": "Ann"}))
        self.assertTrue(self.auth.sign_in("ann@example.com", "Pw12345!"))
        self.assertFalse(self.auth.sign_in("ann@example.com", "wrong"))

    def test_unknown_user_cannot_sign_in(self):
        self.assertFalse(self.auth.sign_in("nobody@example.com", "Pw12345!"))

    def test_email_is_case_and_space_insensitive(self):
        self.auth.register("  Ann@Example.COM ", "Pw12345!")
        self.assertTrue(self.auth.sign_in("ann@example.com", "Pw12345!"))
        self.assertTrue(self.auth.sign_in(" ANN@example.com ", "Pw12345!"))

    def test_duplicate_email_is_refused(self):
        self.assertTrue(self.auth.register("ann@example.com", "Pw12345!"))
        self.assertFalse(self.auth.register("ANN@example.com", "other"))
        self.assertTrue(self.auth.sign_in("ann@example.com", "Pw12345!"))        # first password still works

    def test_register_rejects_empty_email_or_password(self):
        for email, password in (("", "pw"), ("   ", "pw"), (None, "pw"), ("a@b.com", ""), ("a@b.com", None)):
            with self.subTest(email=email, password=password):
                with self.assertRaises(ValueError):
                    self.auth.register(email, password)

    def test_the_password_is_stored_hashed(self):
        self.auth.register("ann@example.com", "Pw12345!")
        self.assertNotIn("Pw12345!", self.users.get_password_hash("ann@example.com"))

    def test_profile(self):
        self.auth.register("ann@example.com", "Pw12345!", {"full_name": "Ann", "dob": "2000-01-01"})
        self.assertEqual(self.auth.get_profile("ANN@example.com"), {"full_name": "Ann", "dob": "2000-01-01"})
        self.assertEqual(self.auth.get_profile("nobody@example.com"), {})

    def test_old_hashes_are_upgraded_after_a_good_sign_in(self):
        from Logic.auth_service import AuthService
        from Logic.pbkdf2_password_hasher import Pbkdf2PasswordHasher
        self.users.add_user("bob@example.com", Pbkdf2PasswordHasher(iterations=1000).hash_password("pw12345"))
        stronger = Pbkdf2PasswordHasher(iterations=2000)
        self.assertTrue(AuthService(stronger, self.users).sign_in("bob@example.com", "pw12345"))
        self.assertFalse(stronger.needs_rehash(self.users.get_password_hash("bob@example.com")))

    def test_failed_sign_in_does_not_change_the_stored_hash(self):
        self.auth.register("ann@example.com", "Pw12345!")
        before = self.users.get_password_hash("ann@example.com")
        self.auth.sign_in("ann@example.com", "wrong")
        self.assertEqual(self.users.get_password_hash("ann@example.com"), before)


class TestUserRepositories(BaseTest):
    def test_user_repository_is_abstract(self):
        from Logic.user_repository import UserRepository
        with self.assertRaises(TypeError):
            UserRepository()

    def test_in_memory_repository(self):
        from Logic.in_memory_user_repository import InMemoryUserRepository
        repo = InMemoryUserRepository()
        self.assertTrue(repo.add_user("a@b.com", "hash1", {"full_name": "A"}))
        self.assertFalse(repo.add_user("a@b.com", "hash2"))
        self.assertEqual(repo.get_password_hash("a@b.com"), "hash1")
        self.assertIsNone(repo.get_password_hash("none@b.com"))
        repo.update_password_hash("a@b.com", "hash3")
        self.assertEqual(repo.get_password_hash("a@b.com"), "hash3")
        profile = repo.get_profile("a@b.com")
        profile["full_name"] = "changed"                                         # a copy: cannot change the stored one
        self.assertEqual(repo.get_profile("a@b.com"), {"full_name": "A"})
        self.assertEqual(repo.get_profile("none@b.com"), {})
        repo.update_password_hash("none@b.com", "x")                             # unknown user: no error

    def test_mongo_repository_with_a_fake_collection(self):
        try:
            from Logic.mongo_user_repository import MongoUserRepository
        except ImportError:
            self.skipTest("pymongo is not installed")

        class FakeCollection:
            def __init__(self):
                self.docs = []

            def find_one(self, query, projection=None):
                for doc in self.docs:
                    if all(doc.get(k) == v for k, v in query.items()):
                        return dict(doc)
                return None

            def insert_one(self, doc):
                self.docs.append(dict(doc))

            def update_one(self, query, update):
                for doc in self.docs:
                    if all(doc.get(k) == v for k, v in query.items()):
                        doc.update(update["$set"])
                        return

        collection = FakeCollection()
        repo = MongoUserRepository(collection)
        self.assertTrue(repo.add_user("ann@example.com", "hash1", {"full_name": "Ann Lee", "dob": "2000-01-01",
                                                                  "gender": "Female", "directory": "hack", "_id": "x"}))
        stored = collection.docs[0]
        self.assertEqual(list(stored)[:2], ["_id", "email"])
        self.assertEqual(len(stored["_id"]), 32)                                  # same kind of _id as the other accounts
        self.assertEqual(stored["directory"], "ann_" + stored["_id"][:8])        # the profile cannot override it
        self.assertEqual(stored["password_hash"], "hash1")
        self.assertIn("created", stored)
        self.assertFalse(repo.add_user("ann@example.com", "hash2"))
        self.assertEqual(repo.get_password_hash("ann@example.com"), "hash1")
        self.assertIsNone(repo.get_password_hash("none@example.com"))
        profile = repo.get_profile("ann@example.com")
        self.assertNotIn("_id", profile)
        self.assertNotIn("password_hash", profile)
        self.assertEqual(profile["full_name"], "Ann Lee")
        repo.update_password_hash("ann@example.com", "hash9")
        self.assertEqual(repo.get_password_hash("ann@example.com"), "hash9")
        self.assertEqual(repo.get_profile("none@example.com"), {})


class FakeAuthView:
    """Scripted stand-in for the sign-in screens in input_output_manager."""

    def __init__(self, choices, emails=(), passwords=(), details=()):
        self.choices, self.emails = list(choices), list(emails)
        self.passwords, self.details = list(passwords), list(details)
        self.messages = []

    def get_auth_menu_choice(self):
        return self.choices.pop(0)

    def get_email(self):
        return self.emails.pop(0)

    def get_signup_details(self, email):
        return self.details.pop(0)

    def get_login_password(self):
        return self.passwords.pop(0)

    def display_auth_message(self, message):
        self.messages.append(message)

    def display_signup_success(self):
        self.messages.append("SIGNUP_OK")

    def display_login_success(self):
        self.messages.append("LOGIN_OK")

    def display_login_error(self):
        self.messages.append("LOGIN_ERROR")


class TestAuthController(BaseTest):
    def controller(self, view):
        from Logic.auth_controller import AuthController
        from Logic.auth_service import AuthService
        from Logic.in_memory_user_repository import InMemoryUserRepository
        from Logic.pbkdf2_password_hasher import Pbkdf2PasswordHasher
        service = AuthService(Pbkdf2PasswordHasher(iterations=1000), InMemoryUserRepository())
        return AuthController(service, view)

    def test_exit_returns_none(self):
        view = FakeAuthView(["3"])
        self.assertIsNone(self.controller(view).run())

    def test_sign_up_then_log_in(self):
        view = FakeAuthView(["2", "1"], emails=["Ann@Example.com", "ann@example.com"], passwords=["Pw12345!"],
                            details=[{"password": "Pw12345!", "full_name": "Ann", "dob": "2000-01-01"}])
        user = self.controller(view).run()
        self.assertEqual(user, {"full_name": "Ann", "dob": "2000-01-01", "email": "ann@example.com"})
        self.assertEqual(view.messages, ["SIGNUP_OK", "LOGIN_OK"])
        self.assertNotIn("password", user)

    def test_sign_up_with_a_plain_password_string(self):
        view = FakeAuthView(["2", "1"], emails=["a@b.com", "a@b.com"], passwords=["Pw12345!"], details=["Pw12345!"])
        self.assertEqual(self.controller(view).run(), {"email": "a@b.com"})

    def test_duplicate_sign_up_shows_a_message(self):
        view = FakeAuthView(["2", "2", "3"], emails=["a@b.com", "a@b.com"], details=["pw-one", "pw-two"])
        self.controller(view).run()
        self.assertEqual(view.messages[0], "SIGNUP_OK")
        self.assertIn("already exists", view.messages[1])

    def test_sign_up_with_an_empty_password_shows_a_message(self):
        view = FakeAuthView(["2", "3"], emails=["a@b.com"], details=[{"password": "", "full_name": "A"}])
        self.controller(view).run()
        self.assertTrue(any("non-empty" in m for m in view.messages))

    def test_three_wrong_passwords_return_to_the_menu(self):
        view = FakeAuthView(["2", "1", "3"], emails=["a@b.com"] * 4, passwords=["x", "y", "z"], details=["right-pw"])
        self.assertIsNone(self.controller(view).run())
        self.assertEqual(view.messages.count("LOGIN_ERROR"), 3)
        self.assertTrue(any("Too many failed attempts" in m for m in view.messages))

    def test_a_correct_password_on_the_second_try_works(self):
        view = FakeAuthView(["2", "1"], emails=["a@b.com"] * 3, passwords=["wrong", "right-pw"], details=["right-pw"])
        self.assertEqual(self.controller(view).run(), {"email": "a@b.com"})
        self.assertEqual(view.messages, ["SIGNUP_OK", "LOGIN_ERROR", "LOGIN_OK"])

    def test_unknown_email_cannot_log_in(self):
        view = FakeAuthView(["1", "3"], emails=["nobody@x.com"] * 3, passwords=["a", "b", "c"])
        self.assertIsNone(self.controller(view).run())

    def test_signup_details_splitting(self):
        from Logic.auth_controller import AuthController
        self.assertEqual(AuthController._split_details({"password": "p", "full_name": "A"}), ("p", {"full_name": "A"}))
        self.assertEqual(AuthController._split_details("plain"), ("plain", {}))
        self.assertEqual(AuthController._split_details(None), (None, {}))


# ===========================================================================
# 9. Your real medical data files (skipped when the folder is missing)
# ===========================================================================

class TestRealMedicalData(BaseTest):
    DATA_DIR = os.path.join(ROOT, "medical_data")
    LEVELS = ("self_care", "pharmacist", "gp", "emergency_department", "emergency_response")

    def setUp(self):
        super().setUp()
        if not os.path.isfile(os.path.join(self.DATA_DIR, "symptom_guidelines.json")):
            self.skipTest("medical_data folder not found next to logic_manager_oop.py")
        self.repo = GuidelineRepository(self.DATA_DIR)

    def test_symptom_records_are_complete(self):
        ids = set()
        for record in self.repo.symptom_records:
            with self.subTest(record=record.get("id")):
                self.assertTrue(record["id"])
                self.assertNotIn(record["id"], ids, "duplicate record id")
                ids.add(record["id"])
                self.assertTrue(record["keywords"], "a record without keywords can never be matched")
                self.assertIn(record["intended_audience"], ("general_public", "healthcare_professionals"))
                self.assertTrue(record["source"]["source_name"])
                self.assertTrue(record["review_status"])
                for level in record["care_guidance"]:
                    self.assertIn(level, self.LEVELS)
                    self.assertIsInstance(record["care_guidance"][level].get("conditions", []), list)

    def test_there_are_public_records_to_match(self):
        public = [r for r in self.repo.symptom_records if r["intended_audience"] == "general_public"]
        self.assertGreater(len(public), 0)

    def test_every_warning_sign_can_be_matched(self):
        """A condition that its own wording cannot match is dead weight in the cross-check."""
        unmatchable = []
        for record in self.repo.symptom_records:
            if record["intended_audience"] != "general_public":
                continue
            for level in ("emergency_department", "emergency_response"):
                for condition in self.repo.red_flag_conditions(record, level):
                    if not self.repo.matched_phrases([condition], condition):
                        unmatchable.append((record["id"], condition))
        # Conditions that contain a negation (for example 'does not stop') are skipped on purpose.
        unexpected = [item for item in unmatchable if not any(w in item[1].lower().split() for w in ("not", "no", "without"))]
        self.assertEqual(unexpected, [])

    def test_emergency_service_record_exists(self):
        record = self.repo.get_service_record("SCDF-EMS-001")
        self.assertIsNotNone(record, "the emergency advice screen needs the SCDF-EMS-001 record")
        self.assertTrue(record["recommendation"])
        self.assertTrue(record["source"]["source_url"])

    def test_non_emergency_record_exists(self):
        record = self.repo.get_service_record("SCDF-NON-EMERGENCY-001")
        self.assertIsNotNone(record)
        self.assertTrue(record["conditions_not_requiring_995"])

    def test_obvious_emergencies_are_never_downgraded(self):
        engine = AssessmentEngine(ScriptedAIService([reply("non-urgent")]), FakeRepository(), None, "chat",
                                  guidelines=self.repo)
        result = engine.process("symptoms: she had a seizure")
        self.assertEqual(result["urgency"], "emergency")


if __name__ == "__main__":
    unittest.main(verbosity=2)
