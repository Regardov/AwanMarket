from decimal import Decimal

from sqlalchemy import select

from .config import settings
from .database import SessionLocal, engine
from .models import Base, Product, User, UserRole
from .security import hash_password

PRODUCTS = [
    ("Лунная кружка", "Керамическая кружка ручной работы, 350 мл.", "1290.00", 24, "Дом", "🌙"),
    ("Свеча «Тихий лес»", "Соевый воск, хлопковый фитиль и аромат хвои.", "890.00", 32, "Ароматы", "🕯️"),
    ("Плед Aurora", "Мягкий плед из переработанного хлопка, 140×200 см.", "3490.00", 12, "Текстиль", "🧶"),
    ("Термобутылка Nova", "Стальная бутылка, которая держит температуру до 12 часов.", "1890.00", 18, "Аксессуары", "✨"),
    ("Блокнот Orbit", "Недатированный блокнот в твёрдой обложке, 192 страницы.", "690.00", 40, "Канцелярия", "📓"),
    ("Лампа Eclipse", "Компактная настольная лампа с тремя уровнями яркости.", "4290.00", 8, "Свет", "💡"),
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

