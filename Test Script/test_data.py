"""
test_data_manager.py - unit tests for the `casedata` package and data_manager.py.

Place this file next to data_manager.py (the "data manager" folder) and run:

    python -m unittest test_data_manager -v
    # or, if you use pytest:
    python -m pytest test_data_manager.py -v

Notes
-----
* Only the standard library is needed (unittest, tempfile, unittest.mock).
* Every test writes to a temporary directory, so your real case/ folder,
  cases.db and case.csv are never touched.
* JSON, SQLite and MongoDB share one repository contract test suite.
* MongoDB tests use a throwaway database (named casedata_test_<random>) that is
  dropped afterwards; your real 'case_assessments' database is never touched.
  They connect to $CASE_MONGO_URI (default mongodb://localhost:27017) and are
  skipped automatically if pymongo is missing or the server can't be reached.
* `input_output_manager` is not part of the zip. If it can't be imported, a
  tiny stand-in module is registered so the package can still be loaded.
"""

import csv
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
import uuid
from datetime import date, datetime
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# --- stand-in for the project's own I/O helper, only if the real one is absent
try:
    import input_output_manager  # noqa: F401
except ImportError:
    _stub = types.ModuleType("input_output_manager")
    _stub.print_output = lambda *a, **k: None
    sys.modules["input_output_manager"] = _stub

import data_manager
from casedata import (AllOf, BACKENDS, Case, CaseManager, CaseNameFilter,
                      CsvExporter, DateRangeFilter, HistoryViewer,
                      JsonCaseRepository, KeywordFilter, LogEntry,
                      MongoCaseRepository,
                      PerCaseReport, SqliteCaseRepository, UrgencyClassifier,
                      UrgencyFilter, UrgencySummaryReport, build_filter,
                      case_number, create_repository)
from casedata.config import EXPORT_FIELDS
from casedata.exporters import BaseExporter
from casedata.repositories import CaseRepository


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def rec(case_id="case_1", user_input="hello", ai_response="Urgency classification: urgent",
        timestamp="2026-11-02T10:00:00"):
    """Build a record dict like CaseManager.load_all_logs() returns."""
    return {"case_id": case_id, "timestamp": timestamp,
            "user_input": user_input, "ai_response": ai_response}


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="casedata_test_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------
class TestConfig(unittest.TestCase):
    def test_case_number_parses_id(self):
        self.assertEqual(case_number("case_12"), 12)
        self.assertEqual(case_number("case_1"), 1)

    def test_case_number_invalid_returns_zero(self):
        for bad in ("", "case_", "case_x", "12", "case_1.json", None):
            with self.subTest(bad=bad):
                self.assertEqual(case_number(bad), 0)

    def test_export_fields(self):
        self.assertEqual(EXPORT_FIELDS, ["case_id", "timestamp", "user_input", "ai_response"])


# --------------------------------------------------------------------------
# LogEntry
# --------------------------------------------------------------------------
class TestLogEntry(unittest.TestCase):
    def test_timestamp_defaults_to_now_iso(self):
        entry = LogEntry("q", "a")
        datetime.fromisoformat(entry.timestamp)  # must not raise

    def test_explicit_timestamp_kept(self):
        self.assertEqual(LogEntry("q", "a", "2026-01-01T00:00:00").timestamp,
                         "2026-01-01T00:00:00")

    def test_content_is_editable_timestamp_is_not(self):
        entry = LogEntry("q", "a")
        entry.user_input = "q2"
        entry.ai_response = "a2"
        self.assertEqual((entry.user_input, entry.ai_response), ("q2", "a2"))
        with self.assertRaises(AttributeError):
            entry.timestamp = "x"

    def test_dict_style_access(self):
        entry = LogEntry("q", "a", "t")
        self.assertEqual(entry["user_input"], "q")
        self.assertEqual(entry.get("ai_response"), "a")
        self.assertEqual(entry.get("missing", "dflt"), "dflt")
        with self.assertRaises(KeyError):
            entry["missing"]

    def test_round_trip(self):
        entry = LogEntry("q", "a", "2026-01-01T00:00:00")
        clone = LogEntry.from_dict(entry.to_dict())
        self.assertEqual(clone.to_dict(), entry.to_dict())

    def test_from_dict_missing_fields_default_to_empty(self):
        entry = LogEntry.from_dict({})
        self.assertEqual((entry.user_input, entry.ai_response), ("", ""))


# --------------------------------------------------------------------------
# Case
# --------------------------------------------------------------------------
class TestCase(unittest.TestCase):
    def test_new_case_is_open(self):
        case = Case("case_1")
        self.assertTrue(case.is_open())
        self.assertEqual(case.status, Case.OPEN)
        self.assertIsNone(case.closed)
        self.assertEqual(case.logs, [])

    def test_close_sets_status_and_timestamp(self):
        case = Case("case_1")
        case.close()
        self.assertFalse(case.is_open())
        self.assertEqual(case.status, Case.CLOSED)
        datetime.fromisoformat(case.closed)

    def test_add_log_returns_entry_and_appends(self):
        case = Case("case_1")
        entry = case.add_log("q", "a")
        self.assertIsInstance(entry, LogEntry)
        self.assertEqual(len(case.logs), 1)

    def test_logs_property_returns_copy(self):
        case = Case("case_1")
        case.add_log("q", "a")
        case.logs.clear()
        self.assertEqual(len(case.logs), 1)

    def test_update_log_partial(self):
        case = Case("case_1")
        case.add_log("q", "a")
        case.update_log(0, user_input="q2")
        self.assertEqual((case.logs[0].user_input, case.logs[0].ai_response), ("q2", "a"))
        case.update_log(0, ai_response="a2")
        self.assertEqual((case.logs[0].user_input, case.logs[0].ai_response), ("q2", "a2"))

    def test_update_and_delete_invalid_index(self):
        case = Case("case_1")
        with self.assertRaises(IndexError):
            case.update_log(0, "x")
        with self.assertRaises(IndexError):
            case.delete_log(0)

    def test_delete_log(self):
        case = Case("case_1")
        case.add_log("q1", "a1")
        case.add_log("q2", "a2")
        removed = case.delete_log(0)
        self.assertEqual(removed.user_input, "q1")
        self.assertEqual([l.user_input for l in case.logs], ["q2"])

    def test_constructor_accepts_dict_logs(self):
        case = Case("case_1", logs=[{"user_input": "q", "ai_response": "a",
                                     "timestamp": "t"}])
        self.assertIsInstance(case.logs[0], LogEntry)

    def test_to_dict_omits_closed_until_closed(self):
        case = Case("case_1", created="2026-01-01", user_id="u1")
        self.assertNotIn("closed", case.to_dict())
        case.close()
        data = case.to_dict()
        self.assertIn("closed", data)
        self.assertEqual(data["user_id"], "u1")

    def test_round_trip(self):
        case = Case("case_3", created="2026-01-01", user_id="u1")
        case.add_log("q", "a")
        case.close()
        clone = Case.from_dict(case.to_dict())
        self.assertEqual(clone.to_dict(), case.to_dict())

    def test_from_dict_legacy_list_is_closed_case(self):
        case = Case.from_dict([{"user_input": "q", "ai_response": "a"}], "case_9")
        self.assertEqual(case.case_id, "case_9")
        self.assertFalse(case.is_open())
        self.assertEqual(len(case.logs), 1)

    def test_from_dict_missing_status_defaults_to_closed(self):
        self.assertEqual(Case.from_dict({"case_id": "case_1"}).status, Case.CLOSED)

    def test_from_dict_explicit_case_id_wins(self):
        self.assertEqual(Case.from_dict({"case_id": "case_1"}, "case_7").case_id, "case_7")

    def test_dict_style_access(self):
        case = Case("case_1", user_id="u")
        case.add_log("q", "a")
        self.assertEqual(case["case_id"], "case_1")
        self.assertEqual(case["user_id"], "u")
        self.assertIsInstance(case["logs"][0], dict)
        with self.assertRaises(KeyError):
            case["nope"]

    def test_get_returns_default_for_missing_or_none(self):
        case = Case("case_1")
        self.assertEqual(case.get("nope", 5), 5)
        self.assertEqual(case.get("closed", "dflt"), "dflt")  # None -> default
        self.assertEqual(case.get("status"), Case.OPEN)

    def test_repr(self):
        self.assertIn("case_1", repr(Case("case_1")))


# --------------------------------------------------------------------------
# UrgencyClassifier
# --------------------------------------------------------------------------
class TestUrgencyClassifier(unittest.TestCase):
    def test_known_labels(self):
        for label in UrgencyClassifier.LABELS:
            with self.subTest(label=label):
                self.assertEqual(
                    UrgencyClassifier.classify(f"Urgency classification: {label}\nrest"), label)

    def test_case_insensitive_and_leading_whitespace(self):
        self.assertEqual(
            UrgencyClassifier.classify("   \n URGENCY CLASSIFICATION:   Emergency"), "emergency")

    def test_unknown_label_is_unclassified(self):
        self.assertEqual(UrgencyClassifier.classify("Urgency classification: banana"),
                         UrgencyClassifier.UNCLASSIFIED)

    def test_no_prefix_is_unclassified(self):
        self.assertEqual(UrgencyClassifier.classify("Some answer. urgency classification: urgent"),
                         UrgencyClassifier.UNCLASSIFIED)

    def test_none_and_empty(self):
        self.assertEqual(UrgencyClassifier.classify(None), UrgencyClassifier.UNCLASSIFIED)
        self.assertEqual(UrgencyClassifier.classify(""), UrgencyClassifier.UNCLASSIFIED)


# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------
class TestKeywordFilter(unittest.TestCase):
    def test_matches_input_or_response_case_insensitively(self):
        f = KeywordFilter("FEVER")
        self.assertTrue(f.matches(rec(user_input="high fever")))
        self.assertTrue(f.matches(rec(user_input="x", ai_response="Fever noted")))
        self.assertFalse(f.matches(rec(user_input="cough", ai_response="rest")))

    def test_apply_filters_list(self):
        records = [rec(user_input="fever"), rec(user_input="cough")]
        self.assertEqual(len(KeywordFilter("fever").apply(records)), 1)


class TestDateRangeFilter(unittest.TestCase):
    def test_inclusive_bounds(self):
        f = DateRangeFilter("2026-11-01", "2026-11-03")
        self.assertTrue(f.matches(rec(timestamp="2026-11-01T00:00:00")))
        self.assertTrue(f.matches(rec(timestamp="2026-11-03T23:59:59")))
        self.assertFalse(f.matches(rec(timestamp="2026-11-04T00:00:00")))
        self.assertFalse(f.matches(rec(timestamp="2026-10-31T23:59:59")))

    def test_open_ended_ranges(self):
        self.assertTrue(DateRangeFilter(start="2026-11-01").matches(rec(timestamp="2030-01-01T00:00:00")))
        self.assertTrue(DateRangeFilter(end="2026-11-01").matches(rec(timestamp="2000-01-01T00:00:00")))

    def test_today_keyword(self):
        f = DateRangeFilter("today", "today")
        self.assertTrue(f.matches(rec(timestamp=datetime.now().isoformat())))

    def test_accepts_date_objects(self):
        f = DateRangeFilter(date(2026, 11, 1), date(2026, 11, 1))
        self.assertTrue(f.matches(rec(timestamp="2026-11-01T12:00:00")))

    def test_start_after_end_raises(self):
        with self.assertRaises(ValueError):
            DateRangeFilter("2026-11-05", "2026-11-01")

    def test_bad_date_raises(self):
        with self.assertRaises(ValueError):
            DateRangeFilter("11/05/2026")

    def test_unparseable_timestamp_does_not_match(self):
        self.assertFalse(DateRangeFilter("2026-01-01").matches(rec(timestamp="garbage")))
        self.assertFalse(DateRangeFilter("2026-01-01").matches({"user_input": "x"}))


class TestCaseNameFilter(unittest.TestCase):
    def test_digit_means_exact_case(self):
        f = CaseNameFilter("3")
        self.assertTrue(f.matches(rec(case_id="case_3")))
        self.assertFalse(f.matches(rec(case_id="case_30")))
        self.assertFalse(f.matches(rec(case_id="case_13")))

    def test_full_name_is_partial_match(self):
        f = CaseNameFilter("case_3")
        self.assertTrue(f.matches(rec(case_id="case_3")))
        self.assertTrue(f.matches(rec(case_id="case_30")))  # documented: partial

    def test_case_and_whitespace_insensitive(self):
        self.assertTrue(CaseNameFilter("  CASE_2 ").matches(rec(case_id="case_2")))


class TestUrgencyFilter(unittest.TestCase):
    def test_matches_label(self):
        f = UrgencyFilter("Urgent")
        self.assertTrue(f.matches(rec(ai_response="Urgency classification: urgent")))
        self.assertFalse(f.matches(rec(ai_response="Urgency classification: emergency")))

    def test_unclassified_is_valid(self):
        self.assertTrue(UrgencyFilter("unclassified").matches(rec(ai_response="no label")))

    def test_unknown_label_raises(self):
        with self.assertRaises(ValueError):
            UrgencyFilter("severe")


class TestAllOfAndBuildFilter(unittest.TestCase):
    def setUp(self):
        self.records = [
            rec("case_1", "fever", "Urgency classification: urgent", "2026-11-01T09:00:00"),
            rec("case_1", "cough", "Urgency classification: non-urgent", "2026-11-02T09:00:00"),
            rec("case_2", "fever and chest pain", "Urgency classification: emergency", "2026-11-03T09:00:00"),
        ]

    def test_and_operator_builds_allof(self):
        combo = KeywordFilter("fever") & UrgencyFilter("urgent")
        self.assertIsInstance(combo, AllOf)
        self.assertEqual(len(combo.apply(self.records)), 1)

    def test_empty_allof_matches_everything(self):
        self.assertEqual(len(AllOf().apply(self.records)), 3)

    def test_build_filter_empty_query_matches_all(self):
        self.assertEqual(len(build_filter("").apply(self.records)), 3)
        self.assertEqual(len(build_filter(None).apply(self.records)), 3)

    def test_bare_words_are_keywords(self):
        self.assertEqual(len(build_filter("fever").apply(self.records)), 2)

    def test_keyword_key(self):
        self.assertEqual(len(build_filter("keyword:cough").apply(self.records)), 1)

    def test_case_and_name_keys(self):
        self.assertEqual(len(build_filter("case:1").apply(self.records)), 2)
        self.assertEqual(len(build_filter("name:2").apply(self.records)), 1)

    def test_urgency_key(self):
        self.assertEqual(len(build_filter("urgency:emergency").apply(self.records)), 1)

    def test_date_forms(self):
        self.assertEqual(len(build_filter("date:2026-11-02").apply(self.records)), 1)
        self.assertEqual(len(build_filter("date:2026-11-01..2026-11-02").apply(self.records)), 2)
        self.assertEqual(len(build_filter("date:2026-11-02..").apply(self.records)), 2)
        self.assertEqual(len(build_filter("date:..2026-11-01").apply(self.records)), 1)

    def test_combined_query(self):
        result = build_filter("fever date:2026-11-01..2026-11-02 urgency:urgent").apply(self.records)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["case_id"], "case_1")

    def test_quoted_phrase(self):
        records = [rec(user_input="chest pain"), rec(user_input="chest")]
        self.assertEqual(len(build_filter('"chest pain"').apply(records)), 1)

    def test_unmatched_quote_falls_back_to_split(self):
        records = [rec(user_input="the patient's fever")]
        # shlex would fail on the lone apostrophe; build_filter must not raise
        self.assertEqual(len(build_filter("patient's").apply(records)), 1)

    def test_unknown_key_is_treated_as_keyword(self):
        records = [rec(user_input="foo:bar baz")]
        self.assertEqual(len(build_filter("foo:bar").apply(records)), 1)

    def test_missing_value_raises(self):
        for q in ("date:", "case:", "urgency:", "keyword:"):
            with self.subTest(q=q):
                with self.assertRaises(ValueError):
                    build_filter(q)

    def test_invalid_values_raise(self):
        with self.assertRaises(ValueError):
            build_filter("urgency:banana")
        with self.assertRaises(ValueError):
            build_filter("date:not-a-date")


# --------------------------------------------------------------------------
# Reports
# --------------------------------------------------------------------------
class TestReports(unittest.TestCase):
    def setUp(self):
        self.records = [
            rec("case_1", ai_response="Urgency classification: urgent"),
            rec("case_1", ai_response="Urgency classification: urgent"),
            rec("case_2", ai_response="Urgency classification: emergency"),
            rec("case_10", ai_response="plain text"),
        ]

    def test_summary_empty(self):
        self.assertIn("No records", UrgencySummaryReport().generate([]))

    def test_summary_counts_and_percentages(self):
        text = UrgencySummaryReport().generate(self.records)
        self.assertIn("4 assessment(s) across 3 case(s)", text)
        urgent_line = next(l for l in text.splitlines() if l.strip().startswith("urgent"))
        self.assertIn("2", urgent_line)
        self.assertIn("(50%)", urgent_line)
        self.assertIn("unclassified", text)
        self.assertIn("Busiest case: case_1 (2 assessment(s))", text)

    def test_summary_skips_zero_count_labels(self):
        text = UrgencySummaryReport().generate(self.records)
        self.assertNotIn("non-urgent", text)
        self.assertNotIn("insufficient_information", text)

    def test_per_case_empty(self):
        self.assertIn("No records", PerCaseReport().generate([]))

    def test_per_case_sorted_numerically(self):
        lines = PerCaseReport().generate(self.records).splitlines()
        ids = [l.split(":")[0].strip() for l in lines[1:]]
        self.assertEqual(ids, ["case_1", "case_2", "case_10"])  # not case_1, case_10, case_2

    def test_per_case_breakdown(self):
        text = PerCaseReport().generate(self.records)
        self.assertIn("case_1: 2 assessment(s)  [urgent: 2]", text)


# --------------------------------------------------------------------------
# Exporters
# --------------------------------------------------------------------------
class TestCsvExporter(TempDirTestCase):
    def test_writes_header_and_rows_with_bom(self):
        path = os.path.join(self.tmp, "out.csv")
        records = [rec("case_1", "q1", "a1"), rec("case_2", "q2, with comma", 'a "quoted"')]
        with mock.patch("input_output_manager.print_output"):
            count = CsvExporter().export(records, path)
        self.assertEqual(count, 2)

        with open(path, "rb") as f:
            self.assertTrue(f.read(3) == b"\xef\xbb\xbf")  # utf-8-sig BOM
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0], EXPORT_FIELDS)
        self.assertEqual(rows[2][2], "q2, with comma")
        self.assertEqual(rows[2][3], 'a "quoted"')

    def test_unicode_survives(self):
        path = os.path.join(self.tmp, "u.csv")
        with mock.patch("input_output_manager.print_output"):
            CsvExporter().export([rec(user_input="café 你好")], path)
        with open(path, newline="", encoding="utf-8-sig") as f:
            self.assertEqual(list(csv.reader(f))[1][2], "café 你好")

    def test_no_records_returns_none_and_writes_nothing(self):
        path = os.path.join(self.tmp, "none.csv")
        with mock.patch("input_output_manager.print_output") as out:
            self.assertIsNone(CsvExporter().export([], path))
        self.assertFalse(os.path.exists(path))
        out.assert_called_once()

    def test_creates_missing_directory(self):
        path = os.path.join(self.tmp, "nested", "deeper", "out.csv")
        with mock.patch("input_output_manager.print_output"):
            CsvExporter().export([rec()], path)
        self.assertTrue(os.path.exists(path))

    def test_oserror_is_reported_not_raised(self):
        path = os.path.join(self.tmp, "out.csv")
        with mock.patch("input_output_manager.print_output") as out, \
                mock.patch("builtins.open", side_effect=OSError("disk full")):
            self.assertIsNone(CsvExporter().export([rec()], path))
        self.assertTrue(any("could not write" in str(c) for c in out.call_args_list))

    def test_missing_dependency_prints_hint(self):
        class NeedsPkg(BaseExporter):
            default_path = os.path.join(self.tmp, "x.bin")
            dependency_hint = "pip install foo\nthen retry"

            def _write(self, records, path):
                raise ImportError("foo")

        with mock.patch("input_output_manager.print_output") as out:
            self.assertIsNone(NeedsPkg().export([rec()]))
        printed = [c.args[0] for c in out.call_args_list]
        self.assertEqual(printed, ["pip install foo", "then retry"])

    def test_base_exporter_is_abstract(self):
        with self.assertRaises(TypeError):
            BaseExporter()

    def test_row_fills_missing_fields_with_blank(self):
        self.assertEqual(BaseExporter._row({"case_id": "case_1"}), ["case_1", "", "", ""])


# --------------------------------------------------------------------------
# Repository contract (run against every offline backend)
# --------------------------------------------------------------------------
class RepositoryContract:
    """Mixin: subclasses provide make_repo(). Not collected on its own."""

    def make_repo(self):
        raise NotImplementedError

    def setUp(self):
        super().setUp()
        self.repo = self.make_repo()

    def _case(self, n=1, logs=1, **kw):
        case = Case(f"case_{n}", created="2026-11-01T08:00:00", **kw)
        for i in range(logs):
            case.add_log(f"question {i}", f"answer {i}")
        return case

    def test_is_a_case_repository(self):
        self.assertIsInstance(self.repo, CaseRepository)

    def test_read_missing_returns_none(self):
        self.assertIsNone(self.repo.read("case_99"))
        self.assertFalse(self.repo.exists("case_99"))

    def test_create_then_read_round_trip(self):
        original = self._case(1, logs=2, user_id="u1")
        self.repo.create(original)
        loaded = self.repo.read("case_1")
        self.assertEqual(loaded.to_dict(), original.to_dict())
        self.assertTrue(self.repo.exists("case_1"))

    def test_create_duplicate_raises(self):
        self.repo.create(self._case(1))
        with self.assertRaises(ValueError):
            self.repo.create(self._case(1))

    def test_update_overwrites(self):
        case = self._case(1)
        self.repo.create(case)
        case.add_log("extra", "extra")
        case.close()
        self.repo.update(case)
        loaded = self.repo.read("case_1")
        self.assertEqual(len(loaded.logs), 2)
        self.assertFalse(loaded.is_open())
        self.assertIsNotNone(loaded.closed)

    def test_update_missing_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.repo.update(self._case(5))

    def test_update_can_remove_logs(self):
        case = self._case(1, logs=3)
        self.repo.create(case)
        case.delete_log(1)
        self.repo.update(case)
        self.assertEqual([l.user_input for l in self.repo.read("case_1").logs],
                         ["question 0", "question 2"])

    def test_delete(self):
        self.repo.create(self._case(1))
        self.assertTrue(self.repo.delete("case_1"))
        self.assertIsNone(self.repo.read("case_1"))
        self.assertFalse(self.repo.delete("case_1"))

    def test_list_all_sorted_by_case_number(self):
        for n in (10, 2, 1):
            self.repo.create(self._case(n))
        self.assertEqual([c.case_id for c in self.repo.list_all()],
                         ["case_1", "case_2", "case_10"])

    def test_list_all_empty(self):
        self.assertEqual(self.repo.list_all(), [])

    def test_next_case_id(self):
        self.assertEqual(self.repo.next_case_id(), "case_1")
        self.repo.create(self._case(1))
        self.repo.create(self._case(7))
        self.assertEqual(self.repo.next_case_id(), "case_8")

    def test_unicode_content(self):
        case = Case("case_1")
        case.add_log("café ☕ 你好", "réponse — ok")
        self.repo.create(case)
        log = self.repo.read("case_1").logs[0]
        self.assertEqual((log.user_input, log.ai_response), ("café ☕ 你好", "réponse — ok"))


class TestJsonRepository(RepositoryContract, TempDirTestCase):
    def make_repo(self):
        return JsonCaseRepository(os.path.join(self.tmp, "json_cases"))

    def test_one_file_per_case_and_no_tmp_left_over(self):
        self.repo.create(self._case(1))
        names = os.listdir(os.path.join(self.tmp, "json_cases"))
        self.assertEqual(names, ["case_1.json"])

    def test_legacy_list_file_is_loaded_as_closed_case(self):
        directory = os.path.join(self.tmp, "json_cases")
        os.makedirs(directory)
        with open(os.path.join(directory, "case_4.json"), "w", encoding="utf-8") as f:
            json.dump([{"timestamp": "t", "user_input": "q", "ai_response": "a"}], f)
        case = self.repo.read("case_4")
        self.assertFalse(case.is_open())
        self.assertEqual(case.case_id, "case_4")
        self.assertEqual(len(case.logs), 1)

    def test_corrupt_file_returns_none_and_is_skipped_in_list(self):
        directory = os.path.join(self.tmp, "json_cases")
        self.repo.create(self._case(1))
        with open(os.path.join(directory, "case_2.json"), "w") as f:
            f.write("{not valid json")
        with mock.patch("input_output_manager.print_output"):
            self.assertIsNone(self.repo.read("case_2"))
            self.assertEqual([c.case_id for c in self.repo.list_all()], ["case_1"])

    def test_non_container_json_returns_none(self):
        directory = os.path.join(self.tmp, "json_cases")
        os.makedirs(directory)
        with open(os.path.join(directory, "case_1.json"), "w") as f:
            f.write('"just a string"')
        self.assertIsNone(self.repo.read("case_1"))

    def test_unrelated_files_ignored_by_list_all(self):
        directory = os.path.join(self.tmp, "json_cases")
        self.repo.create(self._case(1))
        for name in ("notes.txt", "case_x.json", "case_2.json.tmp", "case_3.json.bak"):
            open(os.path.join(directory, name), "w").close()
        self.assertEqual([c.case_id for c in self.repo.list_all()], ["case_1"])

    def test_list_all_when_directory_missing(self):
        self.assertEqual(JsonCaseRepository(os.path.join(self.tmp, "nope")).list_all(), [])

    def test_write_failure_returns_false(self):
        with mock.patch("input_output_manager.print_output"), \
                mock.patch("builtins.open", side_effect=OSError("read-only")):
            self.assertFalse(self.repo.create(self._case(1)))


class TestSqliteRepository(RepositoryContract, TempDirTestCase):
    def make_repo(self):
        return SqliteCaseRepository(os.path.join(self.tmp, "sub", "cases.db"))

    def test_creates_parent_directory_and_db(self):
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "sub", "cases.db")))

    def test_delete_case_cascades_to_logs(self):
        import sqlite3
        self.repo.create(self._case(1, logs=3))
        self.repo.delete("case_1")
        conn = sqlite3.connect(os.path.join(self.tmp, "sub", "cases.db"))
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0], 0)
        finally:
            conn.close()

    def test_log_order_preserved(self):
        self.repo.create(self._case(1, logs=5))
        self.assertEqual([l.user_input for l in self.repo.read("case_1").logs],
                         [f"question {i}" for i in range(5)])

    def test_migrates_old_schema_without_user_id(self):
        import sqlite3
        path = os.path.join(self.tmp, "old.db")
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE cases (case_id TEXT PRIMARY KEY, case_number INTEGER NOT NULL,
                                status TEXT NOT NULL, created TEXT, closed TEXT);
            CREATE TABLE logs (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL,
                               timestamp TEXT, user_input TEXT, ai_response TEXT);
            INSERT INTO cases VALUES ('case_1', 1, 'open', '2026-01-01', NULL);
        """)
        conn.commit()
        conn.close()
        repo = SqliteCaseRepository(path)  # should ALTER TABLE add user_id
        case = repo.read("case_1")
        self.assertIsNone(case.user_id)
        case.add_log("q", "a")
        repo.update(case)
        self.assertEqual(len(repo.read("case_1").logs), 1)


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------
class TestFactory(unittest.TestCase):
    def test_backend_registry(self):
        self.assertEqual(set(BACKENDS), {"sqlite", "json", "mongo"})

    def test_unknown_backend_raises(self):
        with self.assertRaises(ValueError) as ctx:
            create_repository("oracle")
        self.assertIn("Choose from", str(ctx.exception))

    def test_json_backend_by_name_case_insensitive(self):
        self.assertIsInstance(create_repository("JSON"), JsonCaseRepository)

    def test_env_var_selects_backend(self):
        with mock.patch.dict(os.environ, {"CASE_BACKEND": "json"}):
            self.assertIsInstance(create_repository(), JsonCaseRepository)

    def test_explicit_argument_beats_env_var(self):
        with mock.patch.dict(os.environ, {"CASE_BACKEND": "nonsense"}):
            self.assertIsInstance(create_repository("json"), JsonCaseRepository)


# --------------------------------------------------------------------------
# CaseManager
# --------------------------------------------------------------------------
class ManagerTestCase(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.repo = JsonCaseRepository(os.path.join(self.tmp, "cases"))
        self.mgr = CaseManager(self.repo)

    def _seed(self):
        """case_1 (closed, 2 logs), case_2 (open, 1 log)."""
        c1 = self.mgr.create_new_case()
        self.mgr.add_log(c1, "fever and cough", "Urgency classification: urgent\nSee a doctor")
        self.mgr.add_log(c1, "rash", "Urgency classification: non-urgent")
        self.mgr.close_case(c1)
        c2 = self.mgr.create_new_case()
        self.mgr.add_log(c2, "chest pain", "Urgency classification: emergency")
        return c1, c2


class TestCaseManagerCrud(ManagerTestCase):
    def test_create_new_case_persists_open_case_with_sequential_ids(self):
        c1 = self.mgr.create_new_case()
        c2 = self.mgr.create_new_case()
        self.assertEqual((c1.case_id, c2.case_id), ("case_1", "case_2"))
        self.assertTrue(self.repo.read("case_1").is_open())
        self.assertIsNotNone(c1.created)

    def test_add_log_persists(self):
        case = self.mgr.create_new_case()
        self.mgr.add_log(case, "q", "a")
        self.assertEqual(len(self.mgr.get_case(case.case_id).logs), 1)

    def test_update_and_delete_log_persist(self):
        case = self.mgr.create_new_case()
        self.mgr.add_log(case, "q1", "a1")
        self.mgr.add_log(case, "q2", "a2")
        self.mgr.update_log(case, 0, user_input="edited")
        self.mgr.delete_log(case, 1)
        stored = self.mgr.get_case(case.case_id)
        self.assertEqual([l.user_input for l in stored.logs], ["edited"])

    def test_close_case_persists(self):
        case = self.mgr.create_new_case()
        self.mgr.close_case(case)
        self.assertFalse(self.mgr.get_case(case.case_id).is_open())

    def test_get_case_missing(self):
        self.assertIsNone(self.mgr.get_case("case_404"))

    def test_delete_case(self):
        case = self.mgr.create_new_case()
        self.assertTrue(self.mgr.delete_case(case.case_id))
        self.assertFalse(self.mgr.delete_case(case.case_id))
        self.assertEqual(self.mgr.list_cases(), [])

    def test_get_active_case(self):
        self.assertIsNone(self.mgr.get_active_case())
        c1 = self.mgr.create_new_case()
        self.assertEqual(self.mgr.get_active_case().case_id, c1.case_id)
        self.mgr.close_case(c1)
        self.assertIsNone(self.mgr.get_active_case())

    def test_get_active_case_only_considers_newest(self):
        c1 = self.mgr.create_new_case()
        c2 = self.mgr.create_new_case()
        self.mgr.close_case(c2)
        self.assertIsNone(self.mgr.get_active_case())  # c1 still open, but not newest

    def test_repository_property(self):
        self.assertIs(self.mgr.repository, self.repo)


class TestCaseManagerUserScoping(ManagerTestCase):
    def setUp(self):
        super().setUp()
        self.alice = CaseManager(self.repo, user_id="alice")
        self.bob = CaseManager(self.repo, user_id="bob")

    def test_new_cases_are_stamped_with_user(self):
        self.assertEqual(self.alice.create_new_case().user_id, "alice")

    def test_users_only_see_their_own_cases(self):
        a = self.alice.create_new_case()
        b = self.bob.create_new_case()
        self.assertEqual([c.case_id for c in self.alice.list_cases()], [a.case_id])
        self.assertEqual([c.case_id for c in self.bob.list_cases()], [b.case_id])

    def test_cannot_read_or_delete_other_users_case(self):
        a = self.alice.create_new_case()
        self.assertIsNone(self.bob.get_case(a.case_id))
        self.assertFalse(self.bob.delete_case(a.case_id))
        self.assertIsNotNone(self.alice.get_case(a.case_id))

    def test_load_all_logs_is_scoped(self):
        a = self.alice.create_new_case()
        self.alice.add_log(a, "alice q", "alice a")
        b = self.bob.create_new_case()
        self.bob.add_log(b, "bob q", "bob a")
        self.assertEqual([r["user_input"] for r in self.bob.load_all_logs()], ["bob q"])

    def test_export_choices_are_scoped_to_the_current_user(self):
        alice_case = self.alice.create_new_case()
        self.alice.add_log(alice_case, "alice q", "alice a")
        bob_case = self.bob.create_new_case()
        self.bob.add_log(bob_case, "bob q", "bob a")

        self.assertEqual(
            [choice["case_id"] for choice in self.alice.export_choices()],
            [alice_case.case_id],
        )
        self.assertEqual(
            [choice["case_id"] for choice in self.bob.export_choices()],
            [bob_case.case_id],
        )

    def test_anonymous_manager_sees_everything(self):
        self.alice.create_new_case()
        self.bob.create_new_case()
        self.assertEqual(len(self.mgr.list_cases()), 2)

    def test_ids_stay_unique_across_users(self):
        a = self.alice.create_new_case()
        b = self.bob.create_new_case()
        self.assertNotEqual(a.case_id, b.case_id)


class TestCaseManagerQuerying(ManagerTestCase):
    def setUp(self):
        super().setUp()
        self._seed()

    def test_load_all_logs_tags_case_id(self):
        records = self.mgr.load_all_logs()
        self.assertEqual(len(records), 3)
        self.assertEqual({r["case_id"] for r in records}, {"case_1", "case_2"})
        for field in EXPORT_FIELDS:
            self.assertIn(field, records[0])

    def test_load_all_logs_limited_to_case_ids(self):
        records = self.mgr.load_all_logs(["case_2"])
        self.assertEqual([r["case_id"] for r in records], ["case_2"])
        self.assertEqual(self.mgr.load_all_logs([]), [])

    def test_filter_by_keyword(self):
        self.assertEqual(len(self.mgr.filter_records_by_keyword("chest")), 1)

    def test_filter_uses_supplied_records(self):
        subset = self.mgr.load_all_logs(["case_1"])
        self.assertEqual(len(self.mgr.filter_records(KeywordFilter("chest"), subset)), 0)

    def test_search_query(self):
        self.assertEqual(len(self.mgr.search("urgency:urgent")), 1)
        self.assertEqual(len(self.mgr.search("case:1 doctor")), 1)
        self.assertEqual(len(self.mgr.search("")), 3)

    def test_report_uses_all_records_by_default(self):
        text = self.mgr.report(UrgencySummaryReport())
        self.assertIn("3 assessment(s) across 2 case(s)", text)

    def test_report_with_explicit_records(self):
        text = self.mgr.report(PerCaseReport(), self.mgr.search("case:2"))
        self.assertIn("case_2", text)
        self.assertNotIn("case_1", text)


class TestCaseManagerExport(ManagerTestCase):
    def setUp(self):
        super().setUp()
        self._seed()
        self.mgr.create_new_case()  # case_3: open, empty

    def test_export_all(self):
        path = os.path.join(self.tmp, "all.csv")
        with mock.patch("input_output_manager.print_output"):
            self.assertEqual(self.mgr.export(CsvExporter(), path), 3)

    def test_export_selected_cases(self):
        path = os.path.join(self.tmp, "one.csv")
        with mock.patch("input_output_manager.print_output"):
            self.assertEqual(self.mgr.export(CsvExporter(), path, case_ids=["case_2"]), 1)
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["case_id"] for r in rows], ["case_2"])

    def test_export_choices_skip_empty_cases(self):
        choices = self.mgr.export_choices()
        self.assertEqual([c["case_id"] for c in choices], ["case_1", "case_2"])
        self.assertEqual(choices[0]["entries"], 2)
        self.assertEqual(choices[0]["status"], Case.CLOSED)
        self.assertEqual(set(choices[0]), {"case_id", "status", "entries", "created"})


class TestCaseManagerImport(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.src = JsonCaseRepository(os.path.join(self.tmp, "src"))
        self.dst = SqliteCaseRepository(os.path.join(self.tmp, "dst.db"))
        self.mgr = CaseManager(self.dst)
        for n in (1, 2):
            case = Case(f"case_{n}", created="2026-11-01T00:00:00")
            case.add_log(f"src q{n}", f"src a{n}")
            self.src.create(case)

    def test_copies_all_cases_between_backends(self):
        self.assertEqual(self.mgr.import_from(self.src), 2)
        self.assertEqual([c.case_id for c in self.dst.list_all()], ["case_1", "case_2"])
        self.assertEqual(self.dst.read("case_1").logs[0].user_input, "src q1")

    def test_existing_cases_skipped_by_default(self):
        existing = Case("case_1")
        existing.add_log("keep me", "keep")
        self.dst.create(existing)
        self.assertEqual(self.mgr.import_from(self.src), 1)
        self.assertEqual(self.dst.read("case_1").logs[0].user_input, "keep me")

    def test_overwrite_replaces_existing(self):
        existing = Case("case_1")
        existing.add_log("old", "old")
        self.dst.create(existing)
        self.assertEqual(self.mgr.import_from(self.src, overwrite=True), 2)
        self.assertEqual(self.dst.read("case_1").logs[0].user_input, "src q1")


# --------------------------------------------------------------------------
# HistoryViewer
# --------------------------------------------------------------------------
class TestHistoryViewer(unittest.TestCase):
    def setUp(self):
        self.records = [rec("case_1", f"question {i}", f"answer {i}") for i in range(5)]

    def _run(self, inputs, page_size=2):
        with mock.patch("builtins.input", side_effect=inputs) as fake_input, \
                mock.patch("input_output_manager.print_output") as out:
            HistoryViewer(self.records, page_size).show()
        text = "\n".join(str(c.args[0]) for c in out.call_args_list)
        return text, fake_input

    def test_quit_immediately_shows_first_page_only(self):
        text, _ = self._run(["q"])
        self.assertIn("Page 1 of 3", text)
        self.assertIn("question 0", text)
        self.assertIn("question 1", text)
        self.assertNotIn("question 2", text)
        self.assertIn("Exited history view.", text)

    def test_next_and_previous(self):
        text, _ = self._run(["n", "n", "p", "q"])
        self.assertIn("Page 2 of 3", text)
        self.assertIn("Page 3 of 3", text)
        self.assertIn("question 4", text)

    def test_cannot_go_before_first_or_after_last_page(self):
        text, _ = self._run(["p", "n", "n", "n", "q"])
        self.assertEqual(text.count("Invalid option or end of pages reached."), 2)

    def test_invalid_input_reprompts(self):
        text, fake_input = self._run(["zzz", "q"])
        self.assertIn("Invalid option", text)
        self.assertEqual(fake_input.call_count, 2)

    def test_exit_and_quit_aliases(self):
        for word in ("exit", "quit", "  Q  "):
            with self.subTest(word=word):
                text, _ = self._run([word])
                self.assertIn("Exited history view.", text)

    def test_navigation_prompt_reflects_position(self):
        _, fake_input = self._run(["q"])
        prompt = fake_input.call_args.args[0]
        self.assertIn("'n' for next page", prompt)
        self.assertNotIn("'p' for previous page", prompt)

    def test_shows_record_numbering(self):
        text, _ = self._run(["q"])
        self.assertIn("[Record #1/5]", text)
        self.assertIn("[Record #2/5]", text)


# --------------------------------------------------------------------------
# data_manager.py (backwards-compatible module-level API)
# --------------------------------------------------------------------------
class TestDataManagerModule(TempDirTestCase):
    def setUp(self):
        super().setUp()
        self.repo = JsonCaseRepository(os.path.join(self.tmp, "cases"))
        patcher = mock.patch.object(data_manager, "_manager", CaseManager(self.repo))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get_manager_returns_injected_manager(self):
        self.assertIs(data_manager.get_manager().repository, self.repo)
        self.assertEqual(data_manager.get_backend_name(), "JsonCaseRepository")

    def test_original_api_round_trip(self):
        case = data_manager.create_new_case()
        data_manager.add_log(case, "fever", "Urgency classification: urgent")
        self.assertEqual(data_manager.get_active_case().case_id, case.case_id)
        self.assertEqual(len(data_manager.load_all_logs()), 1)
        self.assertEqual(len(data_manager.filter_records_by_keyword("fever")), 1)
        data_manager.close_case(case)
        self.assertIsNone(data_manager.get_active_case())

    def test_crud_helpers(self):
        case = data_manager.create_new_case()
        data_manager.add_log(case, "q1", "a1")
        data_manager.add_log(case, "q2", "a2")
        data_manager.update_log(case, 0, user_input="edited")
        data_manager.delete_log(case, 1)
        self.assertEqual(data_manager.get_case(case.case_id).logs[0].user_input, "edited")
        self.assertEqual(len(data_manager.list_cases()), 1)
        self.assertTrue(data_manager.delete_case(case.case_id))

    def test_search_records(self):
        case = data_manager.create_new_case()
        data_manager.add_log(case, "fever", "Urgency classification: urgent")
        data_manager.add_log(case, "cough", "Urgency classification: non-urgent")
        self.assertEqual(len(data_manager.search_records("urgency:urgent")), 1)

    def test_convert_json_to_csv_and_export_choices(self):
        case = data_manager.create_new_case()
        data_manager.add_log(case, "q", "a")
        path = os.path.join(self.tmp, "export.csv")
        with mock.patch("input_output_manager.print_output"):
            self.assertEqual(data_manager.convert_json_to_csv(path), 1)
        self.assertTrue(os.path.exists(path))
        self.assertEqual(len(data_manager.list_export_choices()), 1)

    def test_show_stats_summary_and_per_case(self):
        case = data_manager.create_new_case()
        data_manager.add_log(case, "fever", "Urgency classification: urgent")
        with mock.patch("input_output_manager.print_output") as out:
            data_manager.show_stats()
            data_manager.show_stats("fever", per_case=True)
        printed = [c.args[0] for c in out.call_args_list]
        self.assertIn("Urgency summary", printed[0])
        self.assertIn("Per-case breakdown", printed[1])

    def test_show_stats_no_match(self):
        with mock.patch("input_output_manager.print_output") as out:
            data_manager.show_stats("nothing-here")
        self.assertIn("No records match", out.call_args.args[0])

    def test_show_history_delegates_to_viewer(self):
        with mock.patch("builtins.input", return_value="q"), \
                mock.patch("input_output_manager.print_output"):
            data_manager.show_history([rec()], page_size=1)

    def test_list_current_user_cases_requires_authenticated_user(self):
        with self.assertRaises(RuntimeError):
            data_manager.list_current_user_cases()

    def test_list_current_user_cases_with_user(self):
        user_mgr = CaseManager(self.repo, user_id="alice")
        user_mgr.create_new_case()
        with mock.patch.object(data_manager, "_manager", user_mgr):
            self.assertEqual(len(data_manager.list_current_user_cases()), 1)


class TestDataManagerLegacyMigration(TempDirTestCase):
    """First run on a database backend should pull in legacy JSON cases."""

    def setUp(self):
        super().setUp()
        json_dir = os.path.join(self.tmp, "legacy")
        legacy = JsonCaseRepository(json_dir)
        case = Case("case_1", created="2026-11-01T00:00:00")
        case.add_log("legacy q", "legacy a")
        legacy.create(case)

        class TmpJson(JsonCaseRepository):
            def __init__(self):
                super().__init__(json_dir)

        self.db_path = os.path.join(self.tmp, "new.db")
        for p in (
            mock.patch.object(data_manager, "JsonCaseRepository", TmpJson),
            mock.patch.object(data_manager, "create_repository",
                              lambda: SqliteCaseRepository(self.db_path)),
            mock.patch.object(data_manager, "_manager", None),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_get_manager_imports_legacy_json_once(self):
        with mock.patch("input_output_manager.print_output") as out:
            mgr = data_manager.get_manager()
        self.assertEqual(type(mgr.repository).__name__, "SqliteCaseRepository")
        self.assertEqual(len(mgr.list_cases()), 1)
        self.assertTrue(any("Imported 1" in str(c) for c in out.call_args_list))

        # Second call reuses the cached manager and must not re-import.
        with mock.patch("input_output_manager.print_output") as out:
            self.assertIs(data_manager.get_manager(), mgr)
        out.assert_not_called()

    def test_set_current_user_binds_user_and_imports(self):
        with mock.patch("input_output_manager.print_output"):
            data_manager.set_current_user("alice")
        mgr = data_manager.get_manager()
        self.assertEqual(mgr.user_id, "alice")
        # legacy case has no user_id, so alice (a scoped user) does not see it
        self.assertEqual(mgr.list_cases(), [])
        self.assertEqual(len(mgr.repository.list_all()), 1)


# --------------------------------------------------------------------------
# MongoDB backend
# --------------------------------------------------------------------------
MONGO_URI = os.environ.get("CASE_MONGO_URI", "mongodb://localhost:27017")


def _mongo_unavailable_reason():
    """None if a Mongo server is reachable, otherwise why the tests are skipped."""
    try:
        from pymongo import MongoClient
    except ImportError:
        return "pymongo is not installed (python -m pip install pymongo)"
    client = None
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        return None
    except Exception as e:  # noqa: BLE001 - any failure means "skip"
        return f"MongoDB not reachable ({type(e).__name__})"
    finally:
        if client is not None:
            client.close()


_MONGO_SKIP_REASON = _mongo_unavailable_reason()


class TestMongoPureHelpers(unittest.TestCase):
    """No server needed."""

    def test_hide_credentials(self):
        hide = MongoCaseRepository._hide_credentials
        self.assertEqual(hide("mongodb+srv://user:pass@host/db"), "mongodb+srv://***@host/db")
        self.assertEqual(hide("mongodb://localhost:27017"), "mongodb://localhost:27017")

    def test_to_doc_uses_case_id_as_underscore_id(self):
        case = Case("case_12", created="2026-11-01", user_id="u1")
        case.add_log("q", "a")
        doc = MongoCaseRepository._to_doc(case)
        self.assertEqual(doc["_id"], "case_12")
        self.assertNotIn("case_id", doc)
        self.assertEqual(doc["case_number"], 12)
        self.assertEqual(doc["user_id"], "u1")
        self.assertEqual(len(doc["logs"]), 1)

    def test_from_doc_round_trip(self):
        case = Case("case_3", created="2026-11-01", user_id="u1")
        case.add_log("q", "a")
        case.close()
        clone = MongoCaseRepository._from_doc(MongoCaseRepository._to_doc(case))
        self.assertEqual(clone.to_dict(), case.to_dict())

    def test_from_doc_defaults_status_to_closed(self):
        self.assertEqual(MongoCaseRepository._from_doc({"_id": "case_1"}).status, Case.CLOSED)

    def test_missing_pymongo_raises_runtime_error(self):
        with mock.patch.dict(sys.modules, {"pymongo": None, "pymongo.errors": None}):
            with self.assertRaises(RuntimeError) as ctx:
                MongoCaseRepository()
        self.assertIn("pymongo", str(ctx.exception))

    @unittest.skipIf(_MONGO_SKIP_REASON and "pymongo" in _MONGO_SKIP_REASON, "pymongo missing")
    def test_connection_failure_is_reported_without_password(self):
        from pymongo.errors import ServerSelectionTimeoutError
        fake_client = mock.MagicMock()
        fake_client.admin.command.side_effect = ServerSelectionTimeoutError("down")
        with mock.patch("pymongo.MongoClient", return_value=fake_client):
            with self.assertRaises(RuntimeError) as ctx:
                MongoCaseRepository(uri="mongodb://bob:s3cret@db.example.com:27017")
        message = str(ctx.exception)
        self.assertIn("Cannot connect to MongoDB", message)
        self.assertNotIn("s3cret", message)
        self.assertIn("***@db.example.com", message)
        fake_client.close.assert_called_once()


@unittest.skipIf(_MONGO_SKIP_REASON is not None, _MONGO_SKIP_REASON or "")
class TestMongoRepository(RepositoryContract, TempDirTestCase):
    """Runs the shared contract against a real server, in a throwaway database."""

    def make_repo(self):
        self.db_name = f"casedata_test_{uuid.uuid4().hex[:10]}"
        repo = MongoCaseRepository(uri=MONGO_URI, db_name=self.db_name)
        self.addCleanup(self._drop_db, repo)
        return repo

    @staticmethod
    def _drop_db(repo):
        repo._client.drop_database(repo._col.database.name)
        repo._client.close()

    def test_document_shape_in_collection(self):
        case = self._case(4, logs=2, user_id="u1")
        self.repo.create(case)
        doc = self.repo._col.find_one({"_id": "case_4"})
        self.assertEqual(doc["case_number"], 4)
        self.assertEqual(doc["user_id"], "u1")
        self.assertEqual(len(doc["logs"]), 2)  # logs embedded as an array

    def test_numeric_not_lexicographic_ordering(self):
        for n in (2, 10, 1, 100):
            self.repo.create(self._case(n))
        self.assertEqual([c.case_id for c in self.repo.list_all()],
                         ["case_1", "case_2", "case_10", "case_100"])

    def test_one_document_per_case(self):
        self.repo.create(self._case(1))
        self.repo.update(self._case(1, logs=3))
        self.assertEqual(self.repo._col.count_documents({}), 1)


@unittest.skipIf(_MONGO_SKIP_REASON is not None, _MONGO_SKIP_REASON or "")
class TestMongoWithManager(TempDirTestCase):
    """CaseManager on top of a real Mongo backend (user scoping + migration)."""

    def setUp(self):
        super().setUp()
        self.db_name = f"casedata_test_{uuid.uuid4().hex[:10]}"
        self.repo = MongoCaseRepository(uri=MONGO_URI, db_name=self.db_name)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.repo._client.drop_database(self.db_name)
        self.repo._client.close()

    def test_user_scoping(self):
        alice = CaseManager(self.repo, user_id="alice")
        bob = CaseManager(self.repo, user_id="bob")
        a = alice.create_new_case()
        alice.add_log(a, "fever", "Urgency classification: urgent")
        bob.create_new_case()
        self.assertEqual([c.case_id for c in alice.list_cases()], [a.case_id])
        self.assertEqual(len(alice.search("urgency:urgent")), 1)
        self.assertEqual(bob.load_all_logs(), [])
        self.assertFalse(bob.delete_case(a.case_id))

    def test_import_from_json(self):
        src = JsonCaseRepository(os.path.join(self.tmp, "src"))
        case = Case("case_1", created="2026-11-01T00:00:00")
        case.add_log("legacy q", "legacy a")
        src.create(case)
        self.assertEqual(CaseManager(self.repo).import_from(src), 1)
        self.assertEqual(self.repo.read("case_1").logs[0].user_input, "legacy q")

    def test_export_from_mongo(self):
        mgr = CaseManager(self.repo)
        case = mgr.create_new_case()
        mgr.add_log(case, "q", "a")
        path = os.path.join(self.tmp, "mongo.csv")
        with mock.patch("input_output_manager.print_output"):
            self.assertEqual(mgr.export(CsvExporter(), path), 1)

    def test_factory_builds_mongo_repository(self):
        with mock.patch.dict(os.environ, {"CASE_MONGO_URI": MONGO_URI}):
            repo = create_repository("mongo")
        try:
            self.assertIsInstance(repo, MongoCaseRepository)
        finally:
            repo._client.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
