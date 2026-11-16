import json
import os
import re


class GuidelineRepository:
    """Loads the medical guideline data (symptom_guidelines.json and
    care_recommendations.json) and answers two questions about a piece of text:

      * which guideline records does it match?   (find_symptom_records)
      * which listed phrases/conditions does it mention?   (matched_phrases)

    Matching is deliberately simple and deterministic: words are reduced to a
    rough stem, a few synonyms are mapped (stomach -> abdominal), and a phrase
    counts as present only if ALL its significant words are present. Words that
    come shortly after a negation ("no", "denies", "without") are ignored.
    """

    SYMPTOM_FILE = "symptom_guidelines.json"
    SERVICE_FILE = "care_recommendations.json"

    _STOP_WORDS = frozenset(
        "a an the and or of in on to for with that this is are be been it at by from as "
        "than more less any if you your has have had can may also which when after before "
        "does do did same some very just feel feeling felt".split()
    )
    _NEGATORS = frozenset(
        "no not without denies denied never none dont don't doesn't didn't isn't hasn't "
        "haven't negative".split()
    )
    _SYNONYMS = {
        "stomach": "abdominal", "belly": "abdominal", "tummy": "abdominal",
        "abdomen": "abdominal", "giddiness": "dizziness", "giddy": "dizziness",
        "dizzy": "dizziness",
    }
    _SUFFIXES = ("ness", "ing", "ful", "ed", "es", "ly", "s")
    _WORD = re.compile(r"[a-z0-9']+")
    _SEGMENT_BREAK = re.compile(r"[.;,!?:\n]|\bbut\b|\bhowever\b")
    # Only "and/or" and "/" mean "either"; a plain "or" is not split, because in
    # "diarrhoea following a bite or sting" it joins parts of ONE condition.
    _ALTERNATIVES = re.compile(r"\band/or\b|/")

    def __init__(self, data_dir="."):
        self.__symptoms = self._load(os.path.join(data_dir, self.SYMPTOM_FILE))
        self.__services = self._load(os.path.join(data_dir, self.SERVICE_FILE))

    # ---- records ----------------------------------------------------------

    @property
    def symptom_records(self):
        return list(self.__symptoms)

    def get_service_record(self, record_id):
        return next((r for r in self.__services if r.get("id") == record_id), None)

    def find_symptom_records(self, text, audience="general_public"):
        """Records for the public whose keywords appear in `text`."""
        affirmed = self._affirmed_stems(text)
        return [
            record
            for record in self.__symptoms
            if record.get("intended_audience") == audience
            and any(self._phrase_matches(k, affirmed) for k in record.get("keywords", []))
        ]

    @staticmethod
    def red_flag_conditions(record, level):
        """Conditions a record lists for a care level, e.g. 'emergency_department'."""
        return list(record.get("care_guidance", {}).get(level, {}).get("conditions", []))

    @staticmethod
    def needs_review(record):
        return record.get("review_status") == "needs_professional_review"

    @staticmethod
    def source_label(record):
        source = record.get("source", {})
        return (
            f"{source.get('source_name', 'Unknown source')} - {record.get('id', '?')}, "
            f"last updated {source.get('last_updated', 'unknown')}"
        )

    @staticmethod
    def source_details(record):
        source = record.get("source", {})
        return {
            "id": record.get("id", "?"),
            "source_name": source.get("source_name", "Unknown source"),
            "source_url": source.get("source_url"),
        }

    # ---- text matching ----------------------------------------------------

    def matched_phrases(self, phrases, text):
        """The phrases (from a list) that `text` affirmatively mentions."""
        affirmed = self._affirmed_stems(text)
        return [p for p in phrases if self._phrase_matches(p, affirmed)]

    def mentions(self, text, term):
        return self._stem(term.lower()) in self._affirmed_stems(text)

    # ---- protected helpers ------------------------------------------------

    @staticmethod
    def _load(path):
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a JSON list of records.")
        return data

    def _stem(self, token):
        token = self._SYNONYMS.get(token, token)
        for suffix in self._SUFFIXES:
            if (
                token.endswith(suffix)
                and len(token) - len(suffix) >= 3
                and not (suffix == "s" and token.endswith("ss"))
            ):
                token = token[: -len(suffix)]
                break
        return token[:5]

    def _affirmed_stems(self, text):
        """Stems of the words in `text` that are not negated."""
        stems = set()
        if not isinstance(text, str):
            return stems
        for segment in self._SEGMENT_BREAK.split(text.lower()):
            tokens = self._WORD.findall(segment)
            for index, token in enumerate(tokens):
                if token in self._NEGATORS:
                    continue
                if any(t in self._NEGATORS for t in tokens[max(0, index - 4):index]):
                    continue
                stems.add(self._stem(token))
        return stems

    def _phrase_matches(self, phrase, affirmed):
        lowered = phrase.lower()
        if any(t in self._NEGATORS for t in self._WORD.findall(lowered)):
            return False  # phrases like "does not subside" are too subtle to match by words
        for alternative in self._ALTERNATIVES.split(lowered):
            stems = {
                self._stem(t)
                for t in self._WORD.findall(alternative)
                if t not in self._STOP_WORDS
            }
            if stems and stems <= affirmed:
                return True
        return False
