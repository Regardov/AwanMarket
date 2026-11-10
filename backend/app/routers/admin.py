from decimal import Decimal

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..dependencies import AdminUser, DbSession
from ..models import Order, OrderStatus, Product, User
from ..schemas import (
    AdminStats,
    OrderAdminRead,
    OrderStatusUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    UserRead,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def stats(_: AdminUser, db: DbSession):
    users = await db.scalar(select(func.count(User.id))) or 0
    products = await db.scalar(select(func.count(Product.id))) or 0
    orders = await db.scalar(select(func.count(Order.id))) or 0
    revenue = await db.scalar(
        select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != OrderStatus.cancelled)
    )
    return AdminStats(users=users, products=products, orders=orders, revenue=Decimal(revenue))


@router.get("/users", response_model=list[UserRead])
async def users(_: AdminUser, db: DbSession):
    return (await db.scalars(select(User).order_by(User.created_at.desc()))).all()


@router.get("/products", response_model=list[ProductRead])
async def products(_: AdminUser, db: DbSession):
    return (await db.scalars(select(Product).order_by(Product.created_at.desc()))).all()


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def add_product(payload: ProductCreate, _: AdminUser, db: DbSession):
    product = Product(**payload.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=ProductRead)
async def update_product(product_id: int, payload: ProductUpdate, _: AdminUser, db: DbSession):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, _: AdminUser, db: DbSession):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/orders", response_model=list[OrderAdminRead])
async def orders(_: AdminUser, db: DbSession):
    query = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    return (await db.scalars(query)).all()


@router.patch("/orders/{order_id}/status", response_model=OrderAdminRead)
async def update_order_status(
    order_id: int, payload: OrderStatusUpdate, _: AdminUser, db: DbSession
):
    order = await db.scalar(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    await db.commit()
    return order

