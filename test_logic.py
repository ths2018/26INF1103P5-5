"""
Offline tests for logic_manager.py (no classes, standard library only).

- No live AI / network: every AI reply is hardcoded.
- ai_manager, input_output_manager and data_manager are stubbed in sys.modules
  BEFORE logic_manager is imported, so no Gemini SDK / API key is needed.

Run:
    python test_logic_manager.py
(also works with:  python -m pytest -v test_logic_manager.py)
"""

import os
import sys
import traceback
import types
from contextlib import ExitStack, contextmanager
from unittest import mock

# Make logic_manager importable whether this file sits next to it or in tests/
_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, os.path.dirname(_HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ---------------------------------------------------------------------------
# Stub the three modules logic_manager imports from
# ---------------------------------------------------------------------------
_STUBS = {
    "ai_manager": ["ask_ai", "check_relevance", "create_chat"],
    "input_output_manager": [
        "input_manager", "create_prompt", "get_additional_input", "print_cases",
        "keyword_input", "print_output", "ask_yes_no",
    ],
    "data_manager": [
        "add_log", "close_case", "convert_json_to_csv", "convert_json_to_xlsx",
        "create_new_case", "filter_records_by_keyword", "get_active_case",
        "list_case_files", "load_case", "open_file", "show_history",
    ],
}

for _module_name, _names in _STUBS.items():
    _stub = types.ModuleType(_module_name)
    for _n in _names:
        setattr(_stub, _n, mock.MagicMock(name=f"{_module_name}.{_n}"))
    sys.modules[_module_name] = _stub

import logic_manager as lm  # noqa: E402  (must come after the stubs)

# ---------------------------------------------------------------------------
# Hardcoded AI replies
# ---------------------------------------------------------------------------
REPLY_NON_URGENT = (
    "Urgency classification: non-urgent\n"
    "Certainty: 85%\n\n"
    "Follow-Up Questions:\n"
    "None\n\n"
    "Next-Step Guidance:\n"
    "Rest, drink fluids and monitor your symptoms."
)

REPLY_URGENT = (
    "Urgency classification: urgent\n"
    "Certainty: 70%\n\n"
    "Follow-Up Questions:\n"
    "None\n\n"
    "Next-Step Guidance:\n"
    "See a doctor within 24 hours."
)

REPLY_EMERGENCY = (
    "Urgency classification: emergency\n"
    "Certainty: 95%\n\n"
    "Follow-Up Questions:\n"
    "None\n\n"
    "Next-Step Guidance:\n"
    "Call emergency services now."
)

REPLY_FOLLOW_UP = (
    "Urgency classification: insufficient information\n"
    "Certainty: 40%\n\n"
    "Follow-Up Questions:\n"
    "How long have you had these symptoms?\n\n"
    "Next-Step Guidance:\n"
    "More information is needed."
)

REPLY_MEMORY = (
    "Earlier you told me you had a headache and mild fever.\n"
    "Urgency classification: non-urgent\n"
    "Certainty: 60%"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_fake_ai(replies):
    """Return a stand-in for ask_ai that yields scripted replies in order."""
    remaining = list(replies)
    calls = []

    def fake_ask_ai(chat, text):
        calls.append((chat, text))
        if not remaining:
            raise AssertionError("ask_ai called more times than scripted")
        return remaining.pop(0)

    fake_ask_ai.calls = calls
    return fake_ask_ai


def sent_texts(fake):
    return [text for _, text in fake.calls]


@contextmanager
def patched():
    """Patch every external dependency on logic_manager; yield dict of mocks."""
    m = {}
    with ExitStack() as stack:
        for names in _STUBS.values():
            for name in names:
                m[name] = stack.enter_context(
                    mock.patch.object(lm, name, mock.MagicMock(name=name))
                )
        m["get_active_case"].return_value = None
        m["check_relevance"].return_value = True
        m["ask_yes_no"].return_value = True
        yield m


def script_ai(m, replies):
    fake = make_fake_ai(replies)
    m["ask_ai"].side_effect = fake
    return fake


def printed(m):
    """All text passed to print_output, joined together."""
    return "\n".join(
        str(c.args[0]) for c in m["print_output"].call_args_list if c.args
    )


def make_case():
    return {
        "case_id": "case_001",
        "logs": [{"user_input": "I have had a headache since Monday",
                  "ai_response": "x"}],
    }


# ---------------------------------------------------------------------------
# Keyword helpers
# ---------------------------------------------------------------------------
def test_phrase_matching_respects_word_boundaries():
    assert lm._containes_phrase("a cut on my finger", "cut")
    assert not lm._containes_phrase("execute the plan", "cut")
    assert lm._containes_phrase("I have a SORE THROAT", "sore throat")


def test_is_health_related():
    assert lm.is_health_related("I have a headache")
    assert lm.is_health_related("My knee hurts when I walk")
    assert not lm.is_health_related("What is the capital of France?")
    assert not lm.is_health_related("")
    assert not lm.is_health_related(None)
    assert not lm.is_health_related(123)


def test_contains_emergency_keywords():
    assert lm.contains_emergency_keywords("He is unconscious")
    assert lm.contains_emergency_keywords("I can't breathe")
    assert lm.contains_emergency_keywords("She had a SEIZURE")
    assert not lm.contains_emergency_keywords("I have a mild headache")
    assert not lm.contains_emergency_keywords("my chest pain is mild")
    assert not lm.contains_emergency_keywords(None)


def test_is_memory_question():
    assert lm.is_memory_question("What did we talk about earlier?")
    assert lm.is_memory_question("  Do you remember my symptoms?  ")
    assert not lm.is_memory_question("I have a headache")
    assert not lm.is_memory_question(None)


def test_is_high_risk_age():
    assert lm.is_high_risk_age(3) == "High risk age group"
    assert lm.is_high_risk_age(70) == "High risk age group"
    assert lm.is_high_risk_age("80") == "High risk age group"
    assert lm.is_high_risk_age(5) == "Not high risk age group"
    assert lm.is_high_risk_age(65) == "Not high risk age group"
    assert lm.is_high_risk_age(30) == "Not high risk age group"
    assert lm.is_high_risk_age("abc") == "Unknown"
    assert lm.is_high_risk_age(None) == "Unknown"


def test_is_answer_relevant():
    assert lm.is_answer_relevant("my headache", "a headache can be")
    assert not lm.is_answer_relevant("my headache", "unrelated words")


# ---------------------------------------------------------------------------
# Parsing of AI responses
# ---------------------------------------------------------------------------
def test_get_urgency():
    assert lm.get_urgency(REPLY_NON_URGENT) == "non-urgent"
    assert lm.get_urgency(REPLY_URGENT) == "urgent"
    assert lm.get_urgency(REPLY_EMERGENCY) == "emergency"
    assert lm.get_urgency(REPLY_FOLLOW_UP) == "insufficient information"
    assert lm.get_urgency("URGENCY CLASSIFICATION: Urgent") == "urgent"


def test_get_urgency_bad_input():
    assert lm.get_urgency("no label here") == "insufficient information"
    assert lm.get_urgency(None) == "insufficient information"


def test_get_certainty():
    assert abs(lm.get_certainty("Certainty: 85%") - 0.85) < 1e-9
    assert abs(lm.get_certainty("Certainty: 85") - 0.85) < 1e-9
    assert abs(lm.get_certainty("Certainty: 0.7") - 0.7) < 1e-9
    assert abs(lm.get_certainty("Certainty: 100%") - 1.0) < 1e-9
    assert abs(lm.get_certainty("Certainty: 150") - 1.0) < 1e-9  # clamped


def test_get_certainty_bad_input():
    assert lm.get_certainty("nothing here") == 0.0
    assert lm.get_certainty(None) == 0.0


def test_is_emergency_only_for_explicit_emergency():
    assert lm.is_emergency(REPLY_EMERGENCY)
    assert not lm.is_emergency(REPLY_URGENT)
    assert not lm.is_emergency(REPLY_NON_URGENT)


def test_extract_follow_up_question():
    assert (lm.extract_follow_up_question(REPLY_FOLLOW_UP)
            == "How long have you had these symptoms?")


def test_extract_follow_up_question_none_cases():
    assert lm.extract_follow_up_question(REPLY_NON_URGENT) is None
    assert lm.extract_follow_up_question(
        "Follow-Up Questions:\nNot applicable") is None
    assert lm.extract_follow_up_question("no sections at all") is None
    assert lm.extract_follow_up_question(None) is None


def test_has_follow_up_question():
    assert lm.has_follow_up_question(REPLY_FOLLOW_UP)
    assert not lm.has_follow_up_question(REPLY_NON_URGENT)


def test_extract_section_stops_at_next_label():
    guidance = lm.extract_section(REPLY_URGENT, "Next-Step Guidance:")
    assert guidance == "See a doctor within 24 hours."
    follow_up = lm.extract_section(REPLY_FOLLOW_UP, "Follow-Up Questions:")
    assert "Next-Step" not in follow_up


def test_extract_section_missing_or_invalid():
    assert lm.extract_section(REPLY_NON_URGENT, "Nonexistent:") is None
    assert lm.extract_section(None, "Follow-Up Questions:") is None


# ---------------------------------------------------------------------------
# is_case_related
# ---------------------------------------------------------------------------
def test_case_related_true_without_case_or_logs():
    with patched() as m:
        assert lm.is_case_related("anything", None)
        assert lm.is_case_related("anything", {"logs": []})
        m["check_relevance"].assert_not_called()


def test_case_related_memory_question_always_related():
    with patched() as m:
        assert lm.is_case_related("what did we talk about", make_case())
        m["check_relevance"].assert_not_called()


def test_case_related_delegates_to_check_relevance():
    with patched() as m:
        case = make_case()
        m["check_relevance"].return_value = False
        assert not lm.is_case_related("my ankle hurts", case)
        m["check_relevance"].assert_called_once_with("my ankle hurts", case)


# ---------------------------------------------------------------------------
# process_interaction: guards
# ---------------------------------------------------------------------------
def test_process_non_string_input():
    with patched() as m:
        fake = script_ai(m, [])
        result = lm.process_interaction(None, chat=object())
        assert result["ai_response"] is None
        assert not result["is_health_related"]
        assert fake.calls == []


def test_process_empty_and_whitespace_input():
    with patched() as m:
        fake = script_ai(m, [])
        for text in ("", "   \n\t"):
            result = lm.process_interaction(text, chat=object())
            assert result["ai_response"] is None
            assert result["exchanges"] == []
        assert fake.calls == []


def test_process_non_health_question_never_reaches_ai():
    with patched() as m:
        fake = script_ai(m, [])
        result = lm.process_interaction("What is the capital of France?",
                                        chat=object())
        assert not result["is_health_related"]
        assert not result["is_relevant"]
        assert result["exchanges"] == []
        assert "does not appear" in result["ai_response"]
        assert fake.calls == []


def test_process_emergency_keyword_overrides_ai():
    with patched() as m:
        fake = script_ai(m, [])
        result = lm.process_interaction(
            "My dad is unconscious and not breathing", chat=object())
        assert result["is_emergency"]
        assert result["urgency"] == "emergency"
        assert result["certainty"] == 1.0
        assert len(result["exchanges"]) == 1
        assert fake.calls == []  # AI is never consulted


def test_process_memory_question_goes_to_ai_once():
    with patched() as m:
        fake = script_ai(m, [REPLY_MEMORY])
        result = lm.process_interaction("What did we talk about earlier?",
                                        chat="CHAT")
        assert len(fake.calls) == 1
        assert fake.calls[0][0] == "CHAT"
        assert result["ai_response"] == REPLY_MEMORY
        assert result["urgency"] == "non-urgent"
        assert not result["has_follow_up"]
        assert len(result["exchanges"]) == 1


def test_process_memory_question_ai_failure():
    with patched() as m:
        script_ai(m, [None])
        result = lm.process_interaction("What did we talk about earlier?",
                                        chat=object())
        assert result["ai_response"] is None
        assert result["exchanges"] == []


# ---------------------------------------------------------------------------
# process_interaction: AI handling
# ---------------------------------------------------------------------------
def test_process_simple_assessment():
    with patched() as m:
        fake = script_ai(m, [REPLY_NON_URGENT])
        result = lm.process_interaction(
            "I have a headache and a mild fever", chat=object())
        assert len(fake.calls) == 1
        assert result["urgency"] == "non-urgent"
        assert abs(result["certainty"] - 0.85) < 1e-9
        assert not result["has_follow_up"]
        assert not result["is_emergency"]
        assert result["is_health_related"]
        assert len(result["exchanges"]) == 1
        assert result["age_risk"] is None


def test_process_ai_classified_emergency_is_flagged():
    with patched() as m:
        script_ai(m, [REPLY_EMERGENCY])
        result = lm.process_interaction("I feel very dizzy and weak",
                                        chat=object())
        assert result["is_emergency"]
        assert result["urgency"] == "emergency"


def test_process_urgent_is_not_emergency():
    with patched() as m:
        script_ai(m, [REPLY_URGENT])
        result = lm.process_interaction("I have a swollen ankle",
                                        chat=object())
        assert result["urgency"] == "urgent"
        assert not result["is_emergency"]


def test_process_high_risk_age_note_is_sent_to_ai_only():
    with patched() as m:
        fake = script_ai(m, [REPLY_NON_URGENT])
        result = lm.process_interaction("I have a fever", chat=object(), age=70)
        assert "High risk age group" in sent_texts(fake)[0]
        assert result["age_risk"] == "High risk age group"
        # The logged exchange keeps the user's original wording
        assert result["exchanges"][0]["user_input"] == "I have a fever"


def test_process_normal_age_note():
    with patched() as m:
        fake = script_ai(m, [REPLY_NON_URGENT])
        result = lm.process_interaction("I have a fever", chat=object(), age=30)
        assert "Not high risk age group" in sent_texts(fake)[0]
        assert result["age_risk"] == "Not high risk age group"


def test_process_unknown_age_adds_no_note():
    with patched() as m:
        fake = script_ai(m, [REPLY_NON_URGENT])
        result = lm.process_interaction("I have a fever", chat=object(),
                                        age="abc")
        assert sent_texts(fake)[0] == "I have a fever"
        assert result["age_risk"] == "Unknown"


def test_process_ai_failure_on_first_call():
    with patched() as m:
        script_ai(m, [None])
        result = lm.process_interaction("I have a fever", chat=object())
        assert result["ai_response"] is None
        assert result["certainty"] == 0.0
        assert result["exchanges"] == []
        assert "[Error]" in printed(m)


# ---------------------------------------------------------------------------
# Follow-up questions
# ---------------------------------------------------------------------------
def test_follow_up_answered_then_resolved():
    with patched() as m:
        fake = script_ai(m, [REPLY_FOLLOW_UP, REPLY_NON_URGENT])
        m["get_additional_input"].return_value = "About three days"

        result = lm.process_interaction("I have a fever", chat=object())

        m["get_additional_input"].assert_called_once_with(
            "How long have you had these symptoms?")
        assert len(fake.calls) == 2
        assert sent_texts(fake)[1] == "About three days"
        assert len(result["exchanges"]) == 2
        assert result["urgency"] == "non-urgent"
        assert not result["has_follow_up"]


def test_follow_up_emergency_keyword_stops_loop():
    with patched() as m:
        fake = script_ai(m, [REPLY_FOLLOW_UP])
        m["get_additional_input"].return_value = "Actually I just collapsed"

        result = lm.process_interaction(
            "I have a headache and feel dizzy", chat=object())

        assert len(fake.calls) == 1  # no second AI call
        assert result["is_emergency"]
        assert result["certainty"] == 1.0
        assert len(result["exchanges"]) == 2
        assert not result["has_follow_up"]


def test_follow_up_ai_failure():
    with patched() as m:
        script_ai(m, [REPLY_FOLLOW_UP, None])
        m["get_additional_input"].return_value = "three days"

        result = lm.process_interaction("I have a fever", chat=object())

        assert result["ai_response"] is None
        assert len(result["exchanges"]) == 1  # only the first exchange
        assert "follow-up" in printed(m)


def test_follow_up_loop_is_capped():
    with patched() as m:
        fake = script_ai(m, [REPLY_FOLLOW_UP] * (lm.MAX_FOLLOW_UPS + 5))
        m["get_additional_input"].return_value = "no change"

        result = lm.process_interaction("I have a fever", chat=object())

        assert len(fake.calls) == 1 + lm.MAX_FOLLOW_UPS
        assert m["get_additional_input"].call_count == lm.MAX_FOLLOW_UPS
        assert result["has_follow_up"]  # still asking when capped


# ---------------------------------------------------------------------------
# Case relevance flow
# ---------------------------------------------------------------------------
def test_relevance_no_logs_skips_check():
    with patched() as m:
        script_ai(m, [REPLY_NON_URGENT])
        lm.process_interaction("I have a fever", chat=object(),
                               active_case={"case_id": "c", "logs": []})
        m["check_relevance"].assert_not_called()


def test_relevance_relevant_input_keeps_case():
    with patched() as m:
        script_ai(m, [REPLY_NON_URGENT])
        lm.process_interaction("My headache is worse", chat=object(),
                               active_case=make_case())
        m["check_relevance"].assert_called_once()
        m["close_case"].assert_not_called()
        m["create_new_case"].assert_not_called()


def test_relevance_unrelated_and_not_related_starts_new_case():
    with patched() as m:
        case = make_case()
        new_case = {"case_id": "case_002", "logs": []}
        m["create_new_case"].return_value = new_case
        script_ai(m, [REPLY_NON_URGENT])
        m["check_relevance"].return_value = False
        m["ask_yes_no"].return_value = False

        lm.process_interaction("My ankle hurts", chat=object(),
                               active_case=case)

        m["close_case"].assert_called_once_with(case)
        m["create_new_case"].assert_called_once()
        m["create_chat"].assert_called_once_with(new_case)
        m["add_log"].assert_called_once_with(new_case, "My ankle hurts", "")


def test_relevance_unrelated_but_user_says_related_continues_case():
    with patched() as m:
        script_ai(m, [REPLY_NON_URGENT])
        m["check_relevance"].return_value = False
        m["ask_yes_no"].return_value = True

        lm.process_interaction("My ankle hurts", chat=object(),
                               active_case=make_case())

        m["close_case"].assert_not_called()
        m["create_new_case"].assert_not_called()
        assert "Continuing with case_001.json" in printed(m)


def test_relevance_falls_back_to_get_active_case():
    with patched() as m:
        script_ai(m, [REPLY_NON_URGENT])
        m["get_active_case"].return_value = make_case()
        lm.process_interaction("My headache is worse", chat=object())
        m["check_relevance"].assert_called_once()


# ---------------------------------------------------------------------------
# menu_selection
# ---------------------------------------------------------------------------
def test_menu_option_1_runs_assessment_and_logs():
    with patched() as m:
        case, chat = {"case_id": "case_001", "logs": []}, object()
        m["input_manager"].return_value = {"age": 40, "symptoms": "headache"}
        m["create_prompt"].return_value = "I have a bad headache"
        script_ai(m, [REPLY_NON_URGENT])

        result = lm.menu_selection("1", case, chat)

        assert result[0] is case and result[1] is chat and result[2] is False
        m["add_log"].assert_called_once_with(
            case, "I have a bad headache", REPLY_NON_URGENT)
        out = printed(m)
        assert "=== Assessment Result ===" in out
        assert "Age Risk: Not high risk age group" in out
        assert REPLY_NON_URGENT in out


def test_menu_option_1_logs_every_follow_up_exchange():
    with patched() as m:
        case = {"case_id": "case_001", "logs": []}
        m["input_manager"].return_value = {"age": 40}
        m["create_prompt"].return_value = "I have a fever"
        m["get_additional_input"].return_value = "three days"
        script_ai(m, [REPLY_FOLLOW_UP, REPLY_NON_URGENT])

        lm.menu_selection("1", case, object())

        assert m["add_log"].call_count == 2


def test_menu_option_1_ai_failure_logs_nothing():
    with patched() as m:
        case = {"case_id": "case_001", "logs": []}
        m["input_manager"].return_value = {"age": 40}
        m["create_prompt"].return_value = "I have a fever"
        script_ai(m, [None])

        result = lm.menu_selection("1", case, object())

        assert result[2] is False
        m["add_log"].assert_not_called()
        assert "Unable to complete the assessment" in printed(m)


def test_menu_option_1_non_dict_patient_data():
    with patched() as m:
        case = {"case_id": "case_001", "logs": []}
        m["input_manager"].return_value = "free text"
        m["create_prompt"].return_value = "I have a fever"
        script_ai(m, [REPLY_NON_URGENT])

        lm.menu_selection("1", case, object())  # must not raise

        m["add_log"].assert_called_once()


def test_menu_option_2_prints_cases():
    with patched() as m:
        case, chat = {"case_id": "c", "logs": []}, object()
        assert lm.menu_selection("2", case, chat) == (case, chat, False)
        m["print_cases"].assert_called_once()


def test_menu_option_3_no_results():
    with patched() as m:
        case, chat = {"case_id": "c", "logs": []}, object()
        m["keyword_input"].return_value = "fever"
        m["filter_records_by_keyword"].return_value = []

        assert lm.menu_selection("3", case, chat) == (case, chat, False)
        m["show_history"].assert_not_called()
        assert "No matching records found for 'fever'" in printed(m)


def test_menu_option_3_with_results():
    with patched() as m:
        records = [{"case_id": "case_001"}]
        m["keyword_input"].return_value = "fever"
        m["filter_records_by_keyword"].return_value = records

        lm.menu_selection("3", {"case_id": "c", "logs": []}, object())

        m["show_history"].assert_called_once_with(records)


def test_menu_option_4_converts_to_csv():
    with patched() as m:
        case, chat = {"case_id": "c", "logs": []}, object()
        assert lm.menu_selection("4", case, chat) == (case, chat, False)
        m["convert_json_to_csv"].assert_called_once()


def test_menu_option_5_returns_normally_when_conversion_fails():
    with patched() as m:
        case, chat = {"case_id": "c", "logs": []}, object()
        m["convert_json_to_xlsx"].return_value = False
        assert lm.menu_selection("5", case, chat) == (case, chat, False)
        m["convert_json_to_xlsx"].assert_called_once()


def test_menu_option_6_exits():
    with patched():
        case, chat = {"case_id": "c", "logs": []}, object()
        assert lm.menu_selection("6", case, chat) == (case, chat, True)


def test_menu_invalid_option():
    with patched() as m:
        case, chat = {"case_id": "c", "logs": []}, object()
        assert lm.menu_selection("99", case, chat) == (case, chat, False)
        assert "Invalid menu option." in printed(m)


# ---------------------------------------------------------------------------
# Tiny runner (so no pytest / unittest classes are needed)
# ---------------------------------------------------------------------------
def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failed = []

    for name, fn in tests:
        try:
            fn()
            print(f"{name} ... ok")
        except Exception:
            print(f"{name} ... FAIL")
            traceback.print_exc()
            failed.append(name)

    print("\n" + "-" * 70)
    print(f"Ran {len(tests)} tests")
    if failed:
        print(f"FAILED ({len(failed)}): {', '.join(failed)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(run_all())