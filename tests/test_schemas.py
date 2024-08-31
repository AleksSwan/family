import typing

import pytest

from app import schemas


def test_validate_username_alphanumeric_valid() -> None:
    username = "valid_username"
    assert schemas.validate_username_alphanumeric(username) == username


def test_validate_username_alphanumeric_invalid() -> None:
    username = "invalid_username!"
    with pytest.raises(ValueError, match="must be alphanumeric") as exc_info:
        schemas.validate_username_alphanumeric(username)
    assert str(exc_info.value) == "Username must be alphanumeric"


def test_validate_username_alphanumeric_empty() -> None:
    username = ""
    with pytest.raises(ValueError, match="must be alphanumeric") as exc_info:
        schemas.validate_username_alphanumeric(username)
    assert str(exc_info.value) == "Username must be alphanumeric"


def test_no_uppercase_letter() -> None:
    with pytest.raises(
        ValueError, match="Password must contain at least one uppercase letter"
    ):
        schemas.validate_password_strength("password123!")


def test_no_lowercase_letter() -> None:
    with pytest.raises(
        ValueError, match="Password must contain at least one lowercase letter"
    ):
        schemas.validate_password_strength("PASSWORD123!")


def test_no_digit() -> None:
    with pytest.raises(ValueError, match="Password must contain at least one digit"):
        schemas.validate_password_strength("Password!")


def test_no_special_character() -> None:
    with pytest.raises(
        ValueError, match="Password must contain at least one special character"
    ):
        schemas.validate_password_strength("Password123")


def test_all_required_characters() -> None:
    assert schemas.validate_password_strength("Password123!") == "Password123!"


def test_non_string_input() -> None:
    with pytest.raises(
        TypeError, match="expected string or bytes-like object, got 'int'"
    ):
        schemas.validate_password_strength(typing.cast(str, 123))
