"""CaseRepository: the storage interface (ABC) every backend implements."""


from abc import ABC, abstractmethod

from ..config import case_number


class CaseRepository(ABC):
    """
    INTERFACE / CONTRACT for any storage backend (full CRUD on cases).
    Concrete classes: JsonCaseRepository, SqliteCaseRepository, MongoCaseRepository.
    """

    # Create
    @abstractmethod
    def create(self, case):
        """Insert a new case. Raises ValueError if the id already exists."""

    # Read
    @abstractmethod
    def read(self, case_id):
        """Return the Case or None."""

    @abstractmethod
    def list_all(self):
        """Return all cases, oldest first (sorted by case number)."""

    # Update
    @abstractmethod
    def update(self, case):
        """Overwrite an existing case. Raises KeyError if it does not exist."""

    # Delete
    @abstractmethod
    def delete(self, case_id):
        """Remove a case. Returns True if something was deleted."""

    # Shared (non-abstract) behaviour available to every backend
    def exists(self, case_id):
        return self.read(case_id) is not None

    def next_case_id(self):
        numbers = [case_number(c.case_id) for c in self.list_all()]
        return f"case_{max(numbers, default=0) + 1}"
