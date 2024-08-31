import contextlib
import typing

import fastapi
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType

from app.api.base import get_db
from app.api.payments import ROUTER
from app.settings import Settings


def include_routers(app: fastapi.FastAPI) -> None:
    app.include_router(ROUTER, prefix="/api")


class AppBuilder:
    _async_engine: AsyncEngine
    _session_maker: async_sessionmaker[AsyncSessionType]

    def __init__(self) -> None:
        self.settings = Settings()
        self.app: fastapi.FastAPI = fastapi.FastAPI(
            title=self.settings.service_name,
            debug=self.settings.debug,
            lifespan=self.lifespan_manager,
        )

        self.app.dependency_overrides[get_db] = self.get_async_session_maker
        include_routers(self.app)

    async def get_async_session_maker(self) -> async_sessionmaker[AsyncSessionType]:
        return self._session_maker

    def set_session_maker(
        self, session_maker: async_sessionmaker[AsyncSessionType]
    ) -> None:
        self._session_maker = session_maker

    async def get_session(self) -> typing.AsyncGenerator[AsyncSessionType, None]:
        async with self._session_maker() as session:
            yield session

    async def init_async_resources(self) -> None:
        self._async_engine = create_async_engine(self.settings.db_dsn, echo=True)
        self._session_maker = async_sessionmaker(
            bind=self._async_engine, class_=AsyncSessionType, expire_on_commit=False
        )

    async def tear_down(self) -> None:
        await self._async_engine.dispose()

    @contextlib.asynccontextmanager
    async def lifespan_manager(
        self, _: fastapi.FastAPI
    ) -> typing.AsyncIterator[dict[str, typing.Any]]:
        try:
            await self.init_async_resources()
            yield {}
        finally:
            await self.tear_down()


application = AppBuilder().app
