"""BaseExporter: abstract class holding the shared export workflow."""


import os
from abc import ABC, abstractmethod

import input_output_manager
from ..config import EXPORT_FIELDS


class BaseExporter(ABC):
    """
    ABSTRACT BASE CLASS. Holds the shared export workflow (template method);
    subclasses only supply the file format via _write().
    """

    default_path = None
    dependency_hint = None  # message shown if an optional package is missing

    def export(self, records, path=None):
        path = path or self.default_path
        if not records:
            input_output_manager.print_output("No records to export yet.")
            return None
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            self._write(records, path)
        except ImportError:
            for line in (self.dependency_hint or "A required package is missing.").split("\n"):
                input_output_manager.print_output(line)
            return None
        except OSError as e:
            input_output_manager.print_output(f"Error: could not write '{path}': {e}")
            return None
        input_output_manager.print_output(f"Exported {len(records)} record(s) to '{path}'.")
        return len(records)

    @abstractmethod
    def _write(self, records, path):
        """Write the records to `path` in this exporter's format."""

    @staticmethod
    def _row(record):
        return [record.get(field, "") for field in EXPORT_FIELDS]
