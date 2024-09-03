import pytest

from app.api.base import get_db, get_payment_repo, get_settings
from app.repositories import PaymentRepository
from app.settings import Settings


@pytest.mark.asyncio
async def test_get_db_raises_not_implemented_error() -> None:
    with pytest.raises(NotImplementedError):
        get_db()


def test_get_settings_returns_instance_of_settings() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_get_settings_returns_same_instance_every_time() -> None:
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1.db_name == settings2.db_name


def test_get_payment_repo_returns_payment_repository_instance() -> None:
    repo = get_payment_repo()
    assert isinstance(repo, PaymentRepository)
