"""Exceptions raised by the user package."""


class UserError(Exception):
    """Base class for all user-account errors."""


class UserExistsError(UserError):
    """An account with this email already exists."""


class InvalidUserDataError(UserError):
    """Signup details are missing or malformed."""
