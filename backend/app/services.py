from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Order, OrderItem, Product, User
from .schemas import OrderCreate, UserCreate
from .security import hash_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower().strip()))


async def create_user(db: AsyncSession, payload: UserCreate) -> User:
    if await get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_order(db: AsyncSession, user: User, payload: OrderCreate) -> Order:
    requested: dict[int, int] = {}
    for item in payload.items:
        requested[item.product_id] = requested.get(item.product_id, 0) + item.quantity

    products = (
        await db.scalars(
            select(Product).where(Product.id.in_(requested), Product.is_active.is_(True)).with_for_update()
        )
    ).all()
    by_id = {product.id: product for product in products}
    if len(by_id) != len(requested):
        raise HTTPException(status_code=400, detail="One or more products are unavailable")

    total = Decimal("0")
    order = Order(user_id=user.id, shipping_address=payload.shipping_address.strip())
    for product_id, quantity in requested.items():
        product = by_id[product_id]
        if product.stock < quantity:
            raise HTTPException(status_code=409, detail=f"Not enough stock for {product.name}")
        product.stock -= quantity
        total += product.price * quantity
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price,
            )
        )
    order.total = total
    db.add(order)
    await db.commit()
    return await db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order.id))

