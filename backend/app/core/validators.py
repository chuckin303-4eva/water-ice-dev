"""Shared Pydantic field validators used across more than one schema.

A plain-`str` email field with a light format check, not `EmailStr` --
avoids pulling in the `email-validator` dependency for a check that has
nothing to bounce against anyway (no email is ever sent, see ADR-0012).
"""


def validate_email_format(value: str) -> str:
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError("invalid email address")
    return value
