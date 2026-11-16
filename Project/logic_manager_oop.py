"""
logic_manager.py - entry point for the logic layer (contains no classes).

Wires the objects from the `logic` package together (build_menu) and keeps the
old function-based API so main.py and existing tests keep working.
"""

from AI.ai_manager import check_relevance

from Logic.ai_response import AIResponse
from Logic.assessment_engine import AssessmentEngine
from Logic.case_repository import CaseRepository
from Logic.emergency_detector import EmergencyDetector
from Logic.gemini_ai_service import GeminiAIService
from Logic.health_detector import HealthDetector
from Logic.keywords import (  # noqa: F401  (re-exported for old imports)
    EMERGENCY_KEYWORDS,
    HEALTH_KEYWORDS,
    MAX_FOLLOW_UPS,
    MEMORY_PHRASES,
)
from Logic.memory_question_detector import MemoryQuestionDetector
from Logic.menu_controller import MenuController


def build_menu(ai_service=None, repository=None, case=None, chat=None):
    """Factory that wires the default objects together."""
    ai_service = ai_service or GeminiAIService()
    repository = repository or CaseRepository()
    engine = AssessmentEngine(ai_service, repository, case, chat)
    return MenuController(engine, repository)


# ---------------------------------------------------------------------------
# Backward-compatible function API (thin wrappers around the classes)
# ---------------------------------------------------------------------------

_HEALTH = HealthDetector()
_EMERGENCY = EmergencyDetector()
_MEMORY = MemoryQuestionDetector()


def is_health_related(user_input):
    return _HEALTH.detect(user_input)


def contains_emergency_keywords(user_input):
    """Detect emergency keywords in the user input."""
    return _EMERGENCY.detect(user_input)


def is_memory_question(user_input):
    """Checks if the user input is asking about memory or past interactions."""
    return _MEMORY.detect(user_input)


def is_high_risk_age(age):
    return AssessmentEngine.assess_age_risk(age)


def extract_section(response_text, section_label, stop_labels=None):
    return AIResponse(response_text).section(section_label, stop_labels)


def extract_follow_up_question(response_text):
    return AIResponse(response_text).follow_up_question


def has_follow_up_question(ai_response):
    return AIResponse(ai_response).has_follow_up


def get_urgency(ai_response):
    return AIResponse(ai_response).urgency


def get_certainty(ai_response):
    return AIResponse(ai_response).certainty


def is_emergency(ai_response):
    """'urgent' is NOT treated as 'emergency'."""
    return AIResponse(ai_response).is_emergency


def is_answer_relevant(user_question, ai_response):
    """Demo relevance check using keyword overlap."""
    question_keywords = set(user_question.lower().split())
    response_keywords = set(ai_response.lower().split())
    return len(question_keywords & response_keywords) > 0


def is_case_related(user_input, active_case):
    if not active_case:
        return True
    if not active_case.get("logs", []):
        return True
    if is_memory_question(user_input):
        return True
    return check_relevance(user_input, active_case)


def process_interaction(user_input, chat, active_case=None, age=None):
    """Old entry point. Returns the result as a dict."""
    engine = AssessmentEngine(GeminiAIService(), CaseRepository(), active_case, chat)
    return engine.process(user_input, age)


def menu_selection(choice, active_case, chat):
    """Old entry point. Returns (active_case, chat, should_exit)."""
    menu = build_menu(case=active_case, chat=chat)
    should_exit = menu.handle(choice)
    return menu.engine.case, menu.engine.chat, should_exit
