import datetime
import secrets
import string
import typing
import unittest.mock as unittest_mock
from collections.abc import Awaitable, Callable, MutableMapping
from decimal import Decimal

import fastapi
import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app import exceptions, models, schemas, security
from app.api import payments
from app.api.base import get_payment_repo
from app.application import application as app
from app.repositories import PaymentRepository


ASGIApp = Callable[
    [
        MutableMapping[str, typing.Any],
        Callable[[], Awaitable[MutableMapping[str, typing.Any]]],
        Callable[[MutableMapping[str, typing.Any]], Awaitable[None]],
    ],
    Awaitable[None],
]


MIN_PASSWORD_LENGTH = 8
DEFAULT_PASSWORD_LENGTH = 12
DEFAULT_PREFIX = "TEST_"


def generate_test_password(
    length: int = DEFAULT_PASSWORD_LENGTH, prefix: str = DEFAULT_PREFIX
) -> str:
    """Generate a fake password for testing purposes."""
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = schemas.STRENGTH_REGEX[1:-1]

    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]

    password.extend(
        secrets.choice(lowercase + uppercase + digits + symbols)
        for _ in range(length - 4)
    )

    secrets.SystemRandom().shuffle(password)

    return prefix + "".join(password)


@pytest.fixture(name="test_transaction")
def fixture_test_transaction() -> schemas.TransactionCreate:
    """Mock transaction."""
    return schemas.TransactionCreate(
        uid="user_1_t_1",
        user_id="user_1",
        amount=Decimal("10.99"),
        created_at=datetime.datetime.now().astimezone(),
        type="DEPOSIT",
    )


@pytest.fixture(name="user_data_with_password")
def fixture_user_data_with_password() -> schemas.UserCreate:
    """Mock user data."""
    return schemas.UserCreate(
        id=None,
        email="a@b.com",
        name="JohnDoe",
        full_name="John Jr Doe",
        password=generate_test_password(length=12),
    )


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


@pytest_asyncio.fixture(name="async_client")
async def fixture_async_client(
    payment_repo: PaymentRepository,
) -> typing.AsyncGenerator[AsyncClient, None]:
    """Mock client."""
    app.dependency_overrides[get_payment_repo] = lambda: payment_repo

    transport = ASGITransport(app=typing.cast(ASGIApp, app))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="payment_repo")
def fixture_payment_repo(
    test_transaction: schemas.TransactionCreate,
) -> PaymentRepository:
    """Mock PaymentRepository instance."""

    class MockPaymentRepository(PaymentRepository):
        def __init__(self, db_session: unittest_mock.AsyncMock):
            super().__init__(db_session)

        async def create_user(self, data: schemas.UserCreate) -> models.User:
            hashed_password = (
                security.get_password_hash(data.password) if data.password else None
            )

            user_data = data.model_dump(exclude={"password"})
            user_data["hashed_password"] = hashed_password
            user_data["id"] = "test_id_1" if data.id is None else data.id
            user_data["created_at"] = datetime.datetime.now().astimezone()
            user_data["updated_at"] = datetime.datetime.now().astimezone()

            return models.User(**user_data)

        async def get_transaction(
            self, transaction_id: str
        ) -> models.Transaction | None:
            if transaction_id == "existing_id":
                transaction_data = test_transaction.model_dump(mode="json")
                transaction_data["id"] = "existing_id"
                return models.Transaction(**transaction_data)
            if transaction_id == "non_existing_id":
                return None
            msg = "Mock payment error"
            raise exceptions.PaymentError(msg)

    return MockPaymentRepository(db_session=unittest_mock.AsyncMock())


@pytest.mark.asyncio
async def test_curl_create_user_success(
    async_client: AsyncClient, curl_test_user_data: schemas.UserCreate
) -> None:
    response = await async_client.post(
        "/api/user/", json=curl_test_user_data.model_dump()
    )
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["name"] == curl_test_user_data.name
    assert response_data["id"] == curl_test_user_data.id


@pytest.mark.asyncio
async def test_create_user_success(
    async_client: AsyncClient, user_data_with_password: schemas.UserCreate
) -> None:
    response = await async_client.post(
        "/api/user/", json=user_data_with_password.model_dump()
    )
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["email"] == user_data_with_password.email


def test_password_hashing() -> None:
    password = generate_test_password()
    hashed_password = security.get_password_hash(password)
    assert security.verify_password(password, hashed_password)


@pytest.mark.asyncio
async def test_create_user_exists(
    async_client: AsyncClient,
    payment_repo: PaymentRepository,
    user_data_with_password: schemas.UserCreate,
) -> None:

    with unittest_mock.patch.object(
        payment_repo, "create_user", new_callable=unittest_mock.AsyncMock
    ) as mock_create_user:
        mock_create_user.side_effect = exceptions.UserExistsError("User already exists")
        response = await async_client.post(
            "/api/user/", json=user_data_with_password.model_dump()
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json() == {"detail": "User already exists"}


@pytest.mark.asyncio
async def test_create_user_invalid_data(async_client: AsyncClient) -> None:
    data = {"invalid": "data"}
    response = await async_client.post("/api/user/", json=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()

    assert "detail" in response_data
    required_fields = [v["loc"][1] for v in response_data["detail"]]

    for field in ["name"]:
        assert field in required_fields


@pytest.mark.asyncio
async def test_get_user_balance_found_user(payment_repo: PaymentRepository) -> None:
    user_id = "test_user_id"
    ts = datetime.datetime.now().astimezone()

    with unittest_mock.patch.object(
        payment_repo, "get_user_balance", new_callable=unittest_mock.AsyncMock
    ) as mock_payment_repo:

        mock_payment_repo.get_user_balance.return_value = 1000.0

        result = await payments.get_user_balance(user_id, ts, mock_payment_repo)

        assert result == typing.cast(schemas.UserBalance, {"balance": 1000.0})
        mock_payment_repo.get_user_balance.assert_called_once_with(
            user_id=user_id, ts=ts
        )


@pytest.mark.asyncio
async def test_get_user_balance_not_found_user() -> None:
    user_id = "test_user_id"
    ts = datetime.datetime.now().astimezone()
    payment_repo = unittest_mock.AsyncMock()
    payment_repo.get_user_balance.return_value = None

    with pytest.raises(fastapi.HTTPException):
        await payments.get_user_balance(user_id, ts, payment_repo)

    payment_repo.get_user_balance.assert_called_once_with(user_id=user_id, ts=ts)


@pytest.mark.asyncio
async def test_add_transaction_success(
    async_client: AsyncClient,
    payment_repo: PaymentRepository,
    test_transaction: schemas.TransactionCreate,
) -> None:
    transaction_data = test_transaction.model_dump(mode="json")
    add_transaction_return = transaction_data.copy()
    add_transaction_return["id"] = "1"
    with unittest_mock.patch.object(
        payment_repo,
        "add_transaction",
        return_value=models.Transaction(**add_transaction_return),
    ):
        response = await async_client.put("/api/transaction/", json=transaction_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == add_transaction_return


@pytest.mark.asyncio
async def test_add_transaction_payment_error(
    async_client: AsyncClient,
    payment_repo: PaymentRepository,
    test_transaction: schemas.TransactionCreate,
) -> None:
    with unittest_mock.patch.object(
        payment_repo,
        "add_transaction",
        side_effect=exceptions.PaymentError("Test error"),
    ):
        transaction_data = test_transaction.model_dump(mode="json")
        response = await async_client.put("/api/transaction/", json=transaction_data)
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json() == {"detail": "Test error"}


@pytest.mark.asyncio
async def test_add_transaction_none_result(
    async_client: AsyncClient,
    payment_repo: PaymentRepository,
    test_transaction: schemas.TransactionCreate,
) -> None:

    with unittest_mock.patch.object(payment_repo, "add_transaction", return_value=None):
        transaction_data = test_transaction.model_dump(mode="json")
        response = await async_client.put("/api/transaction/", json=transaction_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json() == {"detail": "Transaction failed"}


@pytest.mark.asyncio
async def test_get_transaction_success(payment_repo: PaymentRepository) -> None:
    transaction_id = "existing_id"
    result = await payments.get_transaction(transaction_id, payment_repo=payment_repo)
    assert isinstance(result, schemas.Transaction)
    assert result.id == transaction_id


@pytest.mark.asyncio
async def test_get_transaction_not_found(payment_repo: PaymentRepository) -> None:
    transaction_id = "non_existing_id"
    with pytest.raises(fastapi.HTTPException) as exc_info:
        await payments.get_transaction(transaction_id, payment_repo=payment_repo)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == "Transaction not found"


@pytest.mark.asyncio
async def test_get_transaction_payment_error(payment_repo: PaymentRepository) -> None:
    transaction_id = "error_id"
    with pytest.raises(fastapi.HTTPException) as exc_info:
        await payments.get_transaction(transaction_id, payment_repo=payment_repo)
    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert exc_info.value.detail == "Mock payment error"
