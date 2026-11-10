from fastapi import APIRouter, HTTPException
from sqlalchemy import or_, select

from ..dependencies import DbSession
from ..models import Product
from ..schemas import ProductRead

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductRead])
async def list_products(db: DbSession, search: str | None = None, category: str | None = None):
    query = select(Product).where(Product.is_active.is_(True)).order_by(Product.created_at.desc())
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
    if category:
        query = query.where(Product.category == category)
    return (await db.scalars(query)).all()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: int, db: DbSession):
    product = await db.get(Product, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

