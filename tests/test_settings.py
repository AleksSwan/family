import typing

import pytest
from pydantic import ValidationError
from sqlalchemy.engine.url import URL

from app.settings import Settings


@pytest.fixture(name="settings")
def fixsture_settings() -> Settings:
    return Settings()


@pytest.fixture(name="mypassword")
def fixsture_mypassword() -> str:
    return "mypassword"


@pytest.fixture(name="custom_password")
def fixsture_custom_password() -> str:
    return "custompassword"


def test_default_db_settings(settings: Settings, mypassword: str) -> None:
    expected_dsn = URL.create(
        drivername="postgresql+asyncpg",
        username="myuser",
        password=mypassword,
        host="postgres-family",
        port=5432,
        database="family",
    )
    assert settings.db_dsn == expected_dsn


def test_custom_db_settings(custom_password: str) -> None:
    settings = Settings(
        db_driver="mysql",
        db_user="customuser",
        db_password=custom_password,
        db_host="customhost",
        db_port=3306,
        db_name="customdatabase",
    )
    expected_dsn = URL.create(
        drivername="mysql",
        username="customuser",
        password=custom_password,
        host="customhost",
        port=3306,
        database="customdatabase",
    )
    assert settings.db_dsn == expected_dsn


def test_invalid_db_settings() -> None:
    with pytest.raises(ValidationError):
        Settings(db_driver=typing.cast(str, None))
