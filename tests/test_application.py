import typing
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application import AppBuilder


EXPECTED_INIT_AWAIT_COUNT = 2
EXPECTED_TEARDOWN_AWAIT_COUNT = 2


@pytest.fixture(name="app_builder")
def fixture_app_builder() -> AppBuilder:
    builder = AppBuilder()
    builder.settings = Mock()
    return builder


@pytest.mark.asyncio
async def test_get_async_session_maker(app_builder: AppBuilder) -> None:
    mock_session_maker = Mock(spec=async_sessionmaker)
    app_builder.async_session_maker = mock_session_maker

    result = app_builder.async_session_maker
    assert result == mock_session_maker

    assert mock_session_maker == app_builder.get_async_session_maker()


@pytest.mark.asyncio
async def test_get_session_returns_async_generator(app_builder: AppBuilder) -> None:
    session_generator = app_builder.get_session()
    assert isinstance(session_generator, typing.AsyncGenerator)


@pytest.mark.asyncio
async def test_lifespan_manager(app_builder: AppBuilder) -> None:
    init_async_resources_mock = AsyncMock()
    tear_down_mock = AsyncMock()

    with patch.object(
        app_builder, "init_async_resources", init_async_resources_mock
    ), patch.object(app_builder, "tear_down", tear_down_mock):

        with pytest.raises(NotImplementedError):
            async with app_builder.lifespan_manager(AsyncMock()):
                raise NotImplementedError

        init_async_resources_mock.assert_awaited_once()

        async with app_builder.lifespan_manager(AsyncMock()):
            pass

        assert init_async_resources_mock.await_count == EXPECTED_INIT_AWAIT_COUNT
        assert tear_down_mock.await_count == EXPECTED_TEARDOWN_AWAIT_COUNT


@pytest.mark.asyncio
async def test_tear_down_disposes_async_engine(app_builder: AppBuilder) -> None:
    with patch.object(
        app_builder, "tear_down", new_callable=AsyncMock
    ) as mock_tear_down:
        await app_builder.tear_down()
        mock_tear_down.assert_awaited_once()


@pytest.mark.asyncio
async def test_tear_down_does_not_raise_exceptions(app_builder: AppBuilder) -> None:
    with patch.object(
        app_builder,
        "tear_down",
        new_callable=AsyncMock,
        side_effect=Exception("Mocked exception"),
    ) as mock_tear_down:
        with pytest.raises(Exception, match="Mocked exception") as exc_info:
            await app_builder.tear_down()
        assert str(exc_info.value) == "Mocked exception"
        mock_tear_down.assert_awaited_once()


@pytest.mark.asyncio
async def test_tear_down_called_successfully(app_builder: AppBuilder) -> None:
    with patch.object(
        app_builder, "tear_down", new_callable=AsyncMock
    ) as mock_tear_down:
        await app_builder.tear_down()
        mock_tear_down.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_engine_dispose_called(app_builder: AppBuilder) -> None:
    mock_async_engine = Mock(spec=AsyncEngine)
    mock_dispose = AsyncMock()
    mock_async_engine.dispose = mock_dispose
    app_builder.async_engine = mock_async_engine

    with patch.object(app_builder, "_async_engine", mock_async_engine):
        await app_builder.tear_down()

    mock_dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_init_async_resources(app_builder: AppBuilder) -> None:
    # Mocking the create_async_engine and async_sessionmaker functions
    mock_async_engine = Mock(spec=AsyncEngine)
    mock_session_maker = Mock(spec=async_sessionmaker)

    with patch(
        "app.application.create_async_engine", return_value=mock_async_engine
    ) as mock_create_engine, patch(
        "app.application.async_sessionmaker", return_value=mock_session_maker
    ) as mock_create_session_maker:

        await app_builder.init_async_resources()

        mock_create_engine.assert_called_once_with(
            app_builder.settings.db_dsn, echo=False
        )

        mock_create_session_maker.assert_called_once_with(
            bind=mock_async_engine, class_=AsyncSession, expire_on_commit=False
        )

        assert app_builder.async_engine == mock_async_engine
        assert app_builder.async_session_maker == mock_session_maker


@pytest.mark.asyncio
async def test_get_session(app_builder: AppBuilder) -> None:
    mock_engine = Mock(spec=AsyncEngine)

    mock_session = MagicMock(spec=AsyncSession)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = AsyncMock()

    mock_session_maker = MagicMock(return_value=mock_session)

    app_builder.async_engine = mock_engine
    app_builder.async_session_maker = mock_session_maker

    async for session in app_builder.get_session():
        assert isinstance(session, AsyncSession)
