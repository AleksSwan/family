import datetime
import typing
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock

import pydantic
import pytest
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import exceptions, models, schemas
from app.repositories.payment import PaymentRepository


ADD_TRANSACTION_EXECUTE_CALLS = 2


@pytest.fixture(name="curl_test_user_data")
def fixture_curl_test_user_data() -> schemas.UserCreate:
    """Mock user data."""
    return schemas.UserCreate(
        id="curl_test_user_1",
        name="JohnDoe",
        email=None,
        full_name=None,
        password=None,
    )


@pytest.fixture(name="user")
def fixture_user(curl_test_user_data: schemas.UserCreate) -> models.User:

    def get_test_password_hash() -> str:
        return "hashed_password"

    user_data = curl_test_user_data.model_dump(exclude={"password"})
    user_data["id"] = 1
    user_data["created_at"] = datetime.datetime.now().astimezone()
    user_data["updated_at"] = datetime.datetime.now().astimezone()
    user_data["hashed_password"] = get_test_password_hash()
    user_data["balance"] = Decimal("0.00")
    return models.User(**user_data)


@pytest.fixture(name="db_session_mock")
def fixture_db_session_mock() -> tuple[MagicMock, AsyncMock]:
    session_mock = AsyncMock(spec=AsyncSession)

    cm_mock = AsyncMock()
    cm_mock.__aenter__.return_value = session_mock
    cm_mock.__aexit__.return_value = None

    db_session_mock = MagicMock(spec=async_sessionmaker)
    db_session_mock.return_value = cm_mock

    return db_session_mock, session_mock


@pytest.fixture(name="balance_history_mock")
def fixture_balance_history_mock() -> models.BalanceHistory:
    mock_balance_history = Mock(spec=models.BalanceHistory)
    mock_balance_history.id = "mock_balance_history_id"
    mock_balance_history.user_id = "mock_user_id"
    mock_balance_history.balance = Decimal("100.00")
    mock_balance_history.created_at = datetime.datetime(2022, 1, 1, tzinfo=datetime.UTC)
    return mock_balance_history


@pytest.fixture(name="transaction_create")
def fixture_transaction_create() -> schemas.TransactionCreate:
    return schemas.TransactionCreate(
        uid="mock_transaction_uid",
        user_id="mock_user_id",
        type="DEPOSIT",
        amount=Decimal("100.00"),
        created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.UTC),
    )


@pytest.fixture(name="transaction")
def fixture_transaction() -> models.Transaction:
    return models.Transaction(
        id=str(uuid.uuid4()),
        uid="test_uid",
        user_id="example_user_id",
        type="DEPOSIT",
        amount=Decimal("100.00"),
        created_at=datetime.datetime(2022, 1, 1, tzinfo=datetime.UTC),
    )


@pytest.mark.asyncio
async def test_create_user_success(
    db_session_mock: tuple[MagicMock, AsyncMock],
    curl_test_user_data: schemas.UserCreate,
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_mock = AsyncMock()
    session_mock.execute.return_value = execute_result_mock
    execute_result_mock.scalar_one_or_none = Mock(return_value=None)

    repo = PaymentRepository(db_session=db_session)

    result = await repo.create_user(curl_test_user_data)

    assert result.model_dump().keys() == user.model_dump().keys()
    db_session.assert_called_once()
    session_mock.execute.assert_called()


@pytest.mark.asyncio
async def test_create_user_existing_user(
    db_session_mock: tuple[MagicMock, AsyncMock],
    curl_test_user_data: schemas.UserCreate,
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_mock = AsyncMock()
    session_mock.execute.return_value = execute_result_mock
    execute_result_mock.scalar_one_or_none = Mock(return_value=user)

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(exceptions.UserExistsError):
        await repo.create_user(curl_test_user_data)


@pytest.mark.asyncio
async def test_create_user_database_error(
    db_session_mock: tuple[MagicMock, AsyncMock],
    curl_test_user_data: schemas.UserCreate,
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_mock = AsyncMock()
    session_mock.execute.return_value = execute_result_mock
    execute_result_mock.scalar_one_or_none = Mock(return_value=None)

    repo = PaymentRepository(db_session=db_session)

    session_mock.commit.side_effect = IntegrityError(
        "Database error", params=None, orig=Exception("Underlying exception")
    )
    with pytest.raises(
        exceptions.UserExistsError, match="User with this information already exists"
    ):
        await repo.create_user(curl_test_user_data)

    session_mock.commit.side_effect = SQLAlchemyError("Database error")
    with pytest.raises(
        exceptions.UserExistsError, match="User with this information already exists"
    ):
        await repo.create_user(curl_test_user_data)


@pytest.mark.asyncio
async def test_get_user_balance_valid_user_id(
    db_session_mock: tuple[MagicMock, AsyncMock],
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_mock = AsyncMock()
    session_mock.execute.return_value = execute_result_mock
    expected_result = Decimal("100.00")
    execute_result_mock.scalar_one_or_none = Mock(return_value=expected_result)

    repo = PaymentRepository(db_session=db_session)

    result = await repo.get_user_balance(user_id=user.id)
    assert result == expected_result


@pytest.mark.asyncio
async def test_get_user_balance_valid_user_id_and_timestamp(
    db_session_mock: tuple[MagicMock, AsyncMock],
    user: models.User,
    balance_history_mock: models.BalanceHistory,
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_mock = AsyncMock()
    session_mock.execute.return_value = execute_result_mock
    expexted_result = balance_history_mock.balance
    execute_result_mock.scalar_one_or_none = Mock(return_value=expexted_result)

    repo = PaymentRepository(db_session=db_session)

    result = await repo.get_user_balance(
        user_id=user.id,
        ts=typing.cast(datetime.datetime, balance_history_mock.created_at),
    )
    assert result == balance_history_mock.balance


@pytest.mark.asyncio
async def test_get_user_balance_non_existent_user_id(
    db_session_mock: tuple[MagicMock, AsyncMock],
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_mock = AsyncMock()
    session_mock.execute.return_value = execute_result_mock
    execute_result_mock.scalar_one_or_none = Mock(return_value=None)

    repo = PaymentRepository(db_session=db_session)

    result = await repo.get_user_balance(user_id="non_existent_user")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_balance_database_error(
    db_session_mock: tuple[MagicMock, AsyncMock],
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock

    repo = PaymentRepository(db_session=db_session)

    session_mock.execute.side_effect = SQLAlchemyError("Database error")
    with pytest.raises(exceptions.PaymentError, match="Database error occurred"):
        await repo.get_user_balance(user_id=user.id)


@pytest.mark.asyncio
async def test_add_transaction_deposit(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    execute_result_user_mock = AsyncMock()
    execute_result_user_mock.scalar_one_or_none = Mock(return_value=user)

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        execute_result_user_mock,
    ]

    def side_effect_add(
        item: models.Transaction | models.User,
    ) -> models.Transaction | models.User:
        item.id = str(uuid.uuid4())
        return item

    session_mock.add.side_effect = side_effect_add
    session_mock.commit.return_value = None
    session_mock.refresh.return_value = None

    repo = PaymentRepository(db_session=db_session)
    transaction = await repo.add_transaction(data=data)

    assert transaction is not None
    assert transaction.id is not None
    assert transaction.user_id == data.user_id
    assert transaction.type == data.type
    assert transaction.amount == data.amount
    assert transaction.created_at == data.created_at
    db_session.assert_called_once()
    assert session_mock.execute.call_count == ADD_TRANSACTION_EXECUTE_CALLS
    session_mock.add.assert_called()
    session_mock.commit.assert_called_once()
    session_mock.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_add_transaction_withdraw(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create
    data.type = "WITHDRAW"
    user.balance = Decimal("1000.00")

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    execute_result_user_mock = AsyncMock()
    execute_result_user_mock.scalar_one_or_none = Mock(return_value=user)

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        execute_result_user_mock,
    ]

    def side_effect_add(
        item: models.Transaction | models.User,
    ) -> models.Transaction | models.User:
        item.id = str(uuid.uuid4())
        return item

    session_mock.add.side_effect = side_effect_add
    session_mock.commit.return_value = None
    session_mock.refresh.return_value = None

    repo = PaymentRepository(db_session=db_session)
    transaction = await repo.add_transaction(data=data)

    assert transaction is not None
    assert transaction.id is not None
    assert transaction.user_id == data.user_id
    assert transaction.type == data.type
    assert transaction.amount == data.amount
    assert transaction.created_at == data.created_at
    db_session.assert_called_once()
    assert session_mock.execute.call_count == ADD_TRANSACTION_EXECUTE_CALLS
    session_mock.add.assert_called()
    session_mock.commit.assert_called_once()
    session_mock.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_add_transaction_invalid_type(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create
    data.type = "INVALID"

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    execute_result_user_mock = AsyncMock()
    execute_result_user_mock.scalar_one_or_none = Mock(return_value=user)

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        execute_result_user_mock,
    ]

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(exceptions.PaymentError, match="Invalid transaction type"):
        await repo.add_transaction(data=data)


@pytest.mark.asyncio
async def test_add_transaction_insufficient_funds(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
    user: models.User,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create
    data.type = "WITHDRAW"
    data.amount = Decimal("1000.00")
    user.balance = Decimal("0.00")

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    execute_result_user_mock = AsyncMock()
    execute_result_user_mock.scalar_one_or_none = Mock(return_value=user)

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        execute_result_user_mock,
    ]

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(exceptions.PaymentError, match="Insufficient funds"):
        await repo.add_transaction(data=data)


@pytest.mark.asyncio
async def test_add_transaction_user_not_found(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    execute_result_user_mock = AsyncMock()
    execute_result_user_mock.scalar_one_or_none = Mock(return_value=None)

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        execute_result_user_mock,
    ]

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(exceptions.PaymentError, match="User not found"):
        await repo.add_transaction(data=data)


@pytest.mark.asyncio
async def test_add_transaction_database_error_fetching_transaction(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create

    session_mock.execute.side_effect = SQLAlchemyError("Database error")

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(
        exceptions.PaymentError, match="Error while fetching transaction"
    ):
        await repo.add_transaction(data=data)


@pytest.mark.asyncio
async def test_add_transaction_database_error_fetching_user(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        SQLAlchemyError("Database error"),
    ]

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(exceptions.PaymentError, match="Error while fetching user"):
        await repo.add_transaction(data=data)


@pytest.mark.asyncio
async def test_add_transaction_duplicate_uid(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create
    existing_transaction: models.Transaction = models.Transaction(
        **data.model_dump(mode="json"),
        id=str(uuid.uuid4()),
    )

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=existing_transaction
    )

    session_mock.execute = AsyncMock(
        return_value=execute_result_existing_transaction_mock
    )

    repo = PaymentRepository(db_session=db_session)
    transaction = await repo.add_transaction(data=data)

    assert transaction is not None
    assert transaction.id is not None
    assert transaction.user_id == transaction.user_id
    assert transaction.type == transaction.type
    assert transaction.amount == transaction.amount
    assert transaction.created_at == transaction.created_at
    db_session.assert_called_once()
    assert session_mock.execute.call_count == 1
    session_mock.add.assert_not_called()
    session_mock.commit.assert_not_called()
    session_mock.refresh.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        (
            "amount",
            "-100.0",
            "Input should be greater than 0",
        ),
        (
            "amount",
            "invalid amount",
            "Input should be a valid decimal",
        ),
        (
            "created_at",
            "invalid",
            "Input should be a valid datetime or date",
        ),
    ],
)
async def test_add_transaction_invalid_inputs(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
    field: str,
    value: str,
    expected_error: str,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create
    if field == "amount":
        data.amount = typing.cast(Decimal, value)
    elif field == "created_at":
        data.created_at = typing.cast(datetime.datetime, value)

    repo = PaymentRepository(db_session=db_session)

    with pytest.warns() as record:
        with pytest.raises(pydantic.ValidationError, match=expected_error):
            await repo.add_transaction(data=data)

        assert len(record) == 1
        assert "but got `str`" in str(record[0].message)


@pytest.mark.parametrize(
    ("commit_side_effect", "refresh_side_effect"),
    [
        (None, SQLAlchemyError("Database error")),
        (SQLAlchemyError("Database error"), None),
    ],
)
@pytest.mark.asyncio
async def test_add_transaction_database_error_committing_transaction(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
    user: models.User,
    commit_side_effect: Exception | None,
    refresh_side_effect: Exception | None,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    execute_result_user_mock = AsyncMock()
    execute_result_user_mock.scalar_one_or_none = Mock(return_value=user)

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        execute_result_user_mock,
    ]

    session_mock.commit.side_effect = commit_side_effect
    session_mock.refresh.side_effect = refresh_side_effect

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(
        exceptions.PaymentError,
        match="An error occurred while processing the transaction",
    ):
        await repo.add_transaction(data)


@pytest.mark.parametrize(
    "rollback_side_effect",
    [
        SQLAlchemyError("Database error"),
        OperationalError(
            "An error occurred", params=None, orig=Exception("Underlying exception")
        ),
    ],
)
@pytest.mark.asyncio
async def test_add_transaction_database_error_rolling_back_transaction(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction_create: schemas.TransactionCreate,
    user: models.User,
    rollback_side_effect: Exception | None,
) -> None:
    db_session, session_mock = db_session_mock
    data = transaction_create

    execute_result_existing_transaction_mock = AsyncMock()
    execute_result_existing_transaction_mock.scalar_one_or_none = Mock(
        return_value=None
    )

    execute_result_user_mock = AsyncMock()
    execute_result_user_mock.scalar_one_or_none = Mock(return_value=user)

    session_mock.execute.side_effect = [
        execute_result_existing_transaction_mock,
        execute_result_user_mock,
    ]

    session_mock.commit.side_effect = None
    session_mock.refresh.side_effect = SQLAlchemyError("Database error")

    session_mock.rollback.side_effect = rollback_side_effect

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(
        exceptions.PaymentError,
        match="An error occurred during rollback",
    ):
        await repo.add_transaction(data)


@pytest.mark.asyncio
async def test_get_transaction_success(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction: models.Transaction,
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_transaction_mock = AsyncMock()
    execute_result_transaction_mock.scalar_one_or_none = Mock(return_value=transaction)

    session_mock.execute = AsyncMock(return_value=execute_result_transaction_mock)

    repo = PaymentRepository(db_session=db_session)

    result = await repo.get_transaction(transaction_id=transaction.uid)

    assert result is not None
    assert result.uid == transaction.uid


@pytest.mark.asyncio
async def test_get_transaction_not_found(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction: models.Transaction,
) -> None:
    db_session, session_mock = db_session_mock

    execute_result_transaction_mock = AsyncMock()
    execute_result_transaction_mock.scalar_one_or_none = Mock(return_value=None)

    session_mock.execute = AsyncMock(return_value=execute_result_transaction_mock)

    repo = PaymentRepository(db_session=db_session)

    result = await repo.get_transaction(transaction_id=transaction.uid)

    assert result is None


@pytest.mark.asyncio
async def test_get_transaction_database_error(
    db_session_mock: tuple[MagicMock, AsyncMock],
    transaction: models.Transaction,
) -> None:
    db_session, session_mock = db_session_mock

    session_mock.execute.side_effect = Exception("Database error")

    repo = PaymentRepository(db_session=db_session)

    with pytest.raises(exceptions.PaymentError):
        await repo.get_transaction(transaction_id=transaction.uid)

    session_mock.commit.assert_not_called()
    session_mock.refresh.assert_not_called()
    session_mock.rollback.assert_called_once()
