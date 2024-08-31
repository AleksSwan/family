import typing
from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession as AsyncSessionType
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select

from app import exceptions, models, schemas, security


class PaymentRepository:

    def __init__(self, db_session: async_sessionmaker[AsyncSessionType]):
        self.db_session = db_session

    def _raise_payment_error(self, msg: str) -> typing.Never:
        raise exceptions.PaymentError(msg)

    async def create_user(self, data: schemas.UserCreate) -> models.User:
        async with self.db_session() as session:
            try:
                existing_user = await session.execute(
                    select(models.User).where(models.User.name == data.name)
                )
                if existing_user.scalar_one_or_none():
                    msg = "User with this username already exists"
                    raise exceptions.UserExistsError(msg)

                # Create new user
                user_data = data.model_dump(exclude={"password"})
                user_data["hashed_password"] = (
                    security.get_password_hash(data.password) if data.password else None
                )
                user = models.User(**user_data)

                session.add(user)
                await session.commit()
                await session.refresh(user)
            except (SQLAlchemyError, IntegrityError) as e:
                await session.rollback()
                msg = "User with this information already exists"
                raise exceptions.UserExistsError(msg) from e
            else:
                return user

    async def get_user_balance(
        self, user_id: str, ts: datetime | None = None
    ) -> Decimal | None:
        async with self.db_session() as session:
            # fetch balance
            try:
                if ts:
                    query = (
                        select(models.BalanceHistory.balance)
                        .filter(
                            models.BalanceHistory.user_id == user_id,
                            models.BalanceHistory.created_at <= ts,
                        )
                        .order_by(models.BalanceHistory.created_at.desc())
                        .limit(1)
                    )
                    result = await session.execute(query)
                    balance = result.scalar_one_or_none()

                    if balance is not None:
                        return balance

                query = select(models.User.balance).filter(models.User.id == user_id)
                result = await session.execute(query)
                return result.scalar_one_or_none()

            except SQLAlchemyError as e:
                self._raise_payment_error(msg=f"Database error occurred: {e}")

    async def add_transaction(
        self, data: schemas.TransactionCreate
    ) -> models.Transaction | None:
        async with self.db_session() as session:
            validated_data = schemas.TransactionCreate(**data.model_dump())
            data = validated_data
            user_id = data.user_id

            # Fetch the transaction
            existing_transaction = await self._fetch_transaction(
                session=session, uid=data.uid
            )
            if existing_transaction:
                return existing_transaction

            # Fetch the user
            user = await self._fetch_user(
                session=session,
                user_id=user_id,
            )
            if not user:
                msg = "User not found"
                raise exceptions.PaymentError(msg)

            self._update_balance(user=user, data=data)

            new_transaction = self._create_transaction(data=data, user_id=user_id)
            balance_history = self._create_balance_history(
                user=user, created_at=data.created_at
            )

            session.add(new_transaction)
            session.add(balance_history)

            # Commit the transaction and refresh
            try:
                await session.commit()
                await session.refresh(user)
            except (SQLAlchemyError, IntegrityError) as e:
                try:
                    await session.rollback()
                except (SQLAlchemyError, OperationalError) as rollback_error:
                    self._raise_payment_error(
                        msg=f"An error occurred during rollback: {rollback_error}"
                    )
                self._raise_payment_error(
                    msg=f"An error occurred while processing the transaction: {e}"
                )

            return new_transaction

    async def _fetch_transaction(
        self,
        session: AsyncSessionType,
        uid: str,
    ) -> models.Transaction | None:
        try:
            result = await session.execute(
                select(models.Transaction).filter(models.Transaction.uid == uid)
            )
        except SQLAlchemyError as e:
            self._raise_payment_error(f"Error while fetching transaction: {e}")
        return result.scalar_one_or_none()

    async def _fetch_user(
        self,
        session: AsyncSessionType,
        user_id: str,
    ) -> models.User | None:
        try:
            result = await session.execute(
                select(models.User).filter(models.User.id == user_id).with_for_update()
            )
        except SQLAlchemyError as e:
            self._raise_payment_error(f"Error while fetching user: {e}")
        else:
            user = result.scalar_one_or_none()
        return user

    def _update_balance(
        self,
        user: models.User,
        data: schemas.TransactionCreate,
    ) -> None:
        if data.type == "DEPOSIT":
            user.balance += data.amount
        elif data.type == "WITHDRAW":
            if user.balance < data.amount:
                self._raise_payment_error("Insufficient funds")
            user.balance -= data.amount
        else:
            self._raise_payment_error("Invalid transaction type")

    def _create_transaction(
        self, data: schemas.TransactionCreate, user_id: str
    ) -> models.Transaction:
        return models.Transaction(
            uid=data.uid,
            user_id=user_id,
            type=data.type,
            amount=data.amount,
            created_at=data.created_at,
        )

    def _create_balance_history(
        self, user: models.User, created_at: datetime
    ) -> models.BalanceHistory:
        return models.BalanceHistory(
            user_id=user.id,
            balance=user.balance,
            created_at=created_at,
        )

    async def get_transaction(self, transaction_id: str) -> models.Transaction | None:
        async with self.db_session() as session:
            try:
                result = await session.execute(
                    select(models.Transaction).filter(
                        models.Transaction.uid == transaction_id
                    )
                )
                transaction = result.scalar_one_or_none()
            except Exception as e:
                await session.rollback()
                msg = "Error while getting transaction"
                raise exceptions.PaymentError(msg) from e
            else:
                return transaction
