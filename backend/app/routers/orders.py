from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..dependencies import CurrentUser, DbSession
from ..models import Order
from ..schemas import OrderCreate, OrderRead
from ..services import create_order

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(payload: OrderCreate, user: CurrentUser, db: DbSession):
    return await create_order(db, user, payload)


@router.get("", response_model=list[OrderRead])
async def my_orders(user: CurrentUser, db: DbSession):
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
    )
    return (await db.scalars(query)).all()


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: int, user: CurrentUser, db: DbSession):
    order = await db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

