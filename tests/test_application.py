import typing
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.application import AppBuilder


@pytest.fixture(name="app_builder")
def fixture_app_builder() -> AppBuilder:
    return AppBuilder()


@pytest.mark.asyncio
async def test_get_async_session_maker() -> None:
    app_builder = AppBuilder()
    mock_session_maker = MagicMock(spec=async_sessionmaker)
    app_builder.set_session_maker(mock_session_maker)

    result = await app_builder.get_async_session_maker()
    assert result == mock_session_maker


@pytest.mark.asyncio
async def test_get_session_returns_async_generator(app_builder: AppBuilder) -> None:
    session = app_builder.get_session()
    assert isinstance(session, typing.AsyncGenerator)


@pytest.mark.asyncio
async def test_get_session_yields_session_object(app_builder: AppBuilder) -> None:
    session = app_builder.get_session()
    assert session is not None
