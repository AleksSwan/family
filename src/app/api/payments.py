from datetime import datetime
from typing import Final, cast

import fastapi
from starlette import status

from app import exceptions, models, schemas
from app.api.base import get_payment_repo
from app.repositories import PaymentRepository
from app.settings import LoggerConfigurator


logger = LoggerConfigurator(name="api-payments").configure()

ROUTER: Final = fastapi.APIRouter()


@ROUTER.post(
    "/user/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(
    data: schemas.UserCreate,
    payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.UserResponse:
    try:
        user: models.User = await payment_repo.create_user(data)
    except exceptions.UserExistsError as e:
        raise fastapi.HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    return schemas.UserResponse.model_validate(user.model_dump())


@ROUTER.get("/user/{user_id}/balance/")
async def get_user_balance(
    user_id: str,
    ts: datetime | None = None,
    payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.UserBalance:
    balance = await payment_repo.get_user_balance(user_id=user_id, ts=ts)
    if balance is None:
        raise fastapi.HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return cast(schemas.UserBalance, {"balance": balance})


@ROUTER.put("/transaction/")
async def add_transaction(
    data: schemas.TransactionCreate,
    payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.Transaction:
    try:
        transaction: models.Transaction | None = await payment_repo.add_transaction(
            data
        )
    except exceptions.PaymentError as e:
        msg = f"uid={data.uid}; PaymentError: {e}"
        logger.debug(msg)
        raise fastapi.HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    if transaction is None:
        raise fastapi.HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction failed",
        )

    return schemas.Transaction.model_validate(transaction)


@ROUTER.post("/transaction/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.Transaction:
    try:
        transaction: models.Transaction | None = await payment_repo.get_transaction(
            transaction_id
        )
    except exceptions.PaymentError as e:
        raise fastapi.HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    if transaction is None:
        raise fastapi.HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return schemas.Transaction.model_validate(transaction)
