from abc import ABC, abstractmethod


class AIService(ABC):
    """Interface: whatever talks to an AI model must provide these three operations."""

    @abstractmethod
    def create_chat(self, case):
        """Start a chat for the given case."""

    @abstractmethod
    def ask(self, chat, text):
        """Send text, return the reply string (or None on failure)."""

    @abstractmethod
    def is_relevant(self, text, case):
        """Is `text` related to what is already in `case`?"""
