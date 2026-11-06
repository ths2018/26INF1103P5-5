"""Chooses a repository implementation by name (default from CASE_BACKEND)."""


import os

from .json_repository import JsonCaseRepository
from .mongo_repository import MongoCaseRepository
from .sqlite_repository import SqliteCaseRepository


# Polymorphic factory: name -> class (no if/elif chain per backend)
BACKENDS = {
    "sqlite": SqliteCaseRepository,
    "json": JsonCaseRepository,
    "mongo": MongoCaseRepository,
}


def create_repository(kind=None):
    kind = (kind or os.environ.get("CASE_BACKEND", "sqlite")).lower()
    if kind not in BACKENDS:
        raise ValueError(f"Unknown backend '{kind}'. Choose from: {', '.join(BACKENDS)}")
    return BACKENDS[kind]()
