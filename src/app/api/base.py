from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories import PaymentRepository
from app.settings import Settings


def get_settings() -> Settings:
    return Settings()


def get_db() -> async_sessionmaker[AsyncSessionType]:
    raise NotImplementedError


def get_payment_repo(
    db: async_sessionmaker[AsyncSessionType] = Depends(get_db),
) -> PaymentRepository:
    return PaymentRepository(
        db_session=db,
    )
