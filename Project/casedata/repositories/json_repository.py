"""JsonCaseRepository: one case_<n>.json file per case."""


import json
import os

import input_output_manager
from ..case import Case
from ..config import CASE_DIR, CASE_PATTERN
from .base import CaseRepository


class JsonCaseRepository(CaseRepository):
    """Original behaviour: one case_<n>.json file per case."""

    def __init__(self, directory=CASE_DIR):
        self._dir = directory

    def _path(self, case_id):
        return os.path.join(self._dir, f"{case_id}.json")

    def _write(self, case):
        os.makedirs(self._dir, exist_ok=True)
        path = self._path(case.case_id)
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(case.to_dict(), f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, path)  # temp file so a crash can't corrupt data
        except OSError as e:
            input_output_manager.print_output(f"[Warning] Failed to save '{path}': {e}")
            return False
        return True

    def create(self, case):
        if os.path.exists(self._path(case.case_id)):
            raise ValueError(f"{case.case_id} already exists")
        return self._write(case)

    def read(self, case_id):
        path = self._path(case_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            input_output_manager.print_output(f"[Warning] Could not load '{path}': {e}")
            return None
        if not isinstance(data, (dict, list)):
            return None
        return Case.from_dict(data, case_id)

    def list_all(self):
        if not os.path.isdir(self._dir):
            return []
        ids = []
        for name in os.listdir(self._dir):
            match = CASE_PATTERN.fullmatch(name)
            if match:
                ids.append((int(match.group(1)), f"case_{match.group(1)}"))
        cases = (self.read(cid) for _, cid in sorted(ids))
        return [c for c in cases if c]

    def update(self, case):
        if not os.path.exists(self._path(case.case_id)):
            raise KeyError(case.case_id)
        return self._write(case)

    def delete(self, case_id):
        try:
            os.remove(self._path(case_id))
            return True
        except FileNotFoundError:
            return False
