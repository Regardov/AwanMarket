from decimal import Decimal

from sqlalchemy import select

from .config import settings
from .database import SessionLocal, engine
from .models import Base, Product, User, UserRole
from .security import hash_password

PRODUCTS = [
    ("Молоко 3,2%", "Свежее пастеризованное молоко, 1 литр.", "109.00", 40, "Молочное", "🥛"),
    ("Хлеб бородинский", "Ароматный ржано-пшеничный хлеб, 400 г.", "79.00", 50, "Выпечка", "🍞"),
    ("Яйца куриные C1", "Свежие куриные яйца, упаковка 10 штук.", "139.00", 30, "Молочное", "🥚"),
    ("Яблоки Gala", "Сладкие и хрустящие яблоки, цена за 1 кг.", "169.00", 45, "Фрукты", "🍎"),
    ("Куриное филе", "Охлаждённое филе грудки, цена за 1 кг.", "429.00", 25, "Мясо", "🍗"),
    ("Макароны из твёрдых сортов", "Макароны группы А, упаковка 450 г.", "119.00", 36, "Бакалея", "🍝"),
]

LEGACY_NAMES = [
    "Лунная кружка",
    "Свеча «Тихий лес»",
    "Плед Aurora",
    "Термобутылка Nova",
    "Блокнот Orbit",
    "Лампа Eclipse",
]


async def init_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        admin = await db.scalar(select(User).where(User.email == settings.admin_email.lower()))
        if admin is None:
            db.add(
                User(
                    name="Администратор",
                    email=settings.admin_email.lower(),
                    password_hash=hash_password(settings.admin_password),
                    role=UserRole.admin,
                )
            )
        existing = {
            product.name: product
            for product in (await db.scalars(select(Product).where(Product.name.in_(LEGACY_NAMES)))).all()
        }
        if existing:
            for legacy_name, product_data in zip(LEGACY_NAMES, PRODUCTS, strict=True):
                product = existing.get(legacy_name)
                if product is None:
                    continue
                name, description, price, stock, category, emoji = product_data
                product.name = name
                product.description = description
                product.price = Decimal(price)
                product.stock = stock
                product.category = category
                product.emoji = emoji

        has_products = await db.scalar(select(Product.id).limit(1))
        if has_products is None:
            for name, description, price, stock, category, emoji in PRODUCTS:
                db.add(
                    Product(
                        name=name,
                        description=description,
                        price=Decimal(price),
                        stock=stock,
                        category=category,
                        emoji=emoji,
                    )
                )
        await db.commit()

