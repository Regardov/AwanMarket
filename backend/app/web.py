from decimal import Decimal, InvalidOperation

from fastapi import FastAPI, HTTPException
from nicegui import app, ui
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from .config import settings
from .database import SessionLocal
from .models import Order, Product, User, UserRole
from .schemas import OrderCreate, OrderItemCreate, UserCreate
from .security import verify_password
from .services import create_order, create_user, get_user_by_email

STYLE = """
<style>
  :root { --ink:#17211d; --cream:#f7f3eb; --sage:#637f6d; --mint:#dfeadf; --gold:#d4a24c; }
  body { background:var(--cream); color:var(--ink); font-family:Inter,system-ui,sans-serif; }
  .q-header { background:rgba(247,243,235,.92)!important; color:var(--ink)!important;
    backdrop-filter:blur(14px); border-bottom:1px solid rgba(23,33,29,.08); }
  .hero { background:linear-gradient(135deg,#20372d 0%,#496553 60%,#789078 100%);
    border-radius:2rem; color:white; overflow:hidden; position:relative; }
  .hero:after { content:'✦'; position:absolute; right:5%; top:-24%; font-size:20rem;
    color:rgba(255,255,255,.07); transform:rotate(15deg); }
  .product-card { background:rgba(255,255,255,.7); border:1px solid rgba(23,33,29,.08);
    border-radius:1.5rem; box-shadow:0 14px 45px rgba(37,56,46,.08); transition:.2s ease; }
  .product-card:hover { transform:translateY(-4px); box-shadow:0 20px 55px rgba(37,56,46,.14); }
  .products-grid { display:grid; grid-template-columns:minmax(0,1fr); gap:1.25rem; }
  @media(min-width:640px) { .products-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
  @media(min-width:1024px) { .products-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } }
  .emoji-tile { background:linear-gradient(145deg,#e4eee4,#cadccf); border-radius:1.15rem; }
  .soft-card { background:white; border-radius:1.5rem; border:1px solid rgba(23,33,29,.08); }
  .accent-button { background:var(--sage)!important; color:white!important; border-radius:999px!important; }
  .gold-button { background:var(--gold)!important; color:#17211d!important; border-radius:999px!important; }
  .muted { color:#647168; }
  .brand { white-space:nowrap; }
  @media(max-width:700px) { .hero { border-radius:1.25rem; } .desktop-nav { display:none!important; } }
</style>
"""


def money(value: Decimal | int | float) -> str:
    return f"{Decimal(value):,.0f} ₽".replace(",", " ")


def cart() -> dict[str, int]:
    if "cart" not in app.storage.user:
        app.storage.user["cart"] = {}
    return app.storage.user["cart"]


async def current_user() -> User | None:
    user_id = app.storage.user.get("user_id")
    if not user_id:
        return None
    async with SessionLocal() as db:
        return await db.get(User, int(user_id))


def add_to_cart(product_id: int) -> None:
    data = dict(cart())
    key = str(product_id)
    data[key] = data.get(key, 0) + 1
    app.storage.user["cart"] = data
    ui.notify("Добавлено в корзину", type="positive")


async def header() -> None:
    user = await current_user()
    with ui.header().classes("items-center no-wrap px-3 md:px-10 h-18"):
        ui.link("☾ LUNORA", "/").classes("brand text-xl font-black tracking-widest no-underline text-slate-800")
        ui.space()
        with ui.row().classes("desktop-nav items-center gap-6"):
            ui.link("Каталог", "/#catalog").classes("no-underline text-slate-700")
            if user:
                ui.link("Заказы", "/orders").classes("no-underline text-slate-700")
            if user and user.role == UserRole.admin:
                ui.link("Админка", "/admin").classes("no-underline text-slate-700")
        ui.space()
        ui.button("Корзина", icon="shopping_bag", on_click=lambda: ui.navigate.to("/cart")).props(
            "flat no-caps"
        )
        if user:
            with ui.button(icon="person").props("round flat"):
                with ui.menu():
                    ui.menu_item(user.name)

                    def logout() -> None:
                        app.storage.user.clear()
                        ui.navigate.to("/")

                    ui.menu_item("Выйти", on_click=logout)
        else:
            ui.button("Войти", on_click=lambda: ui.navigate.to("/login")).props("no-caps").classes(
                "accent-button"
            )


def page_shell() -> None:
    ui.add_head_html(STYLE)
    ui.colors(primary="#637f6d", secondary="#d4a24c", accent="#20372d")


@ui.page("/")
async def storefront() -> None:
    page_shell()
    await header()
    with ui.column().classes("w-full max-w-7xl mx-auto px-4 md:px-8 py-8 gap-14"):
        with ui.row().classes("hero w-full p-8 md:p-16 items-center"):
            with ui.column().classes("max-w-2xl gap-5 z-10"):
                ui.label("ВЕЩИ С ТИХИМ ХАРАКТЕРОМ").classes("text-xs tracking-[.28em] text-amber-200")
                ui.label("Маленькие радости для дома и тебя").classes(
                    "text-4xl md:text-6xl font-black leading-tight"
                )
                ui.label(
                    "Собрали уютные, честные и долговечные вещи — без лишнего шума."
                ).classes("text-lg text-slate-100 max-w-xl")
                ui.button("Смотреть коллекцию", on_click=lambda: ui.run_javascript(
                    "document.getElementById('catalog').scrollIntoView({behavior:'smooth'})"
                )).props("no-caps").classes("gold-button px-7 py-3")
        with ui.column().classes("w-full gap-5").props('id="catalog"'):
            with ui.row().classes("w-full items-end"):
                with ui.column().classes("gap-1"):
                    ui.label("Наша коллекция").classes("text-3xl font-black")
                    ui.label("Каждый товар выбран с вниманием к деталям.").classes("muted")
            async with SessionLocal() as db:
                products = (
                    await db.scalars(
                        select(Product).where(Product.is_active.is_(True)).order_by(Product.id)
                    )
                ).all()
            with ui.element("div").classes("products-grid w-full"):
                for product in products:
                    with ui.card().classes("product-card p-3"):
                        with ui.element("div").classes(
                            "emoji-tile w-full h-44 flex items-center justify-center text-7xl"
                        ):
                            ui.label(product.emoji)
                        with ui.column().classes("p-3 w-full gap-2"):
                            ui.label(product.category.upper()).classes(
                                "text-xs tracking-widest text-emerald-700"
                            )
                            ui.label(product.name).classes("text-xl font-bold")
                            ui.label(product.description).classes("muted min-h-12")
                            with ui.row().classes("w-full items-center mt-2"):
                                ui.label(money(product.price)).classes("text-xl font-black")
                                ui.space()
                                ui.button(
                                    icon="add_shopping_cart",
                                    on_click=lambda pid=product.id: add_to_cart(pid),
                                ).props("round unelevated").classes("accent-button")
        with ui.row().classes("w-full soft-card p-8 md:p-12 items-center gap-8"):
            ui.label("✦").classes("text-6xl text-amber-500")
            with ui.column().classes("gap-1"):
                ui.label("Lunora — меньше случайного, больше любимого").classes("text-2xl font-bold")
                ui.label("Бережная упаковка · Честные материалы · Поддержка без ботов").classes("muted")


@ui.page("/login")
async def login_page() -> None:
    page_shell()
    await header()
    with ui.card().classes("soft-card w-[92vw] max-w-md mx-auto mt-16 p-7 gap-4"):
        ui.label("С возвращением").classes("text-3xl font-black")
        ui.label("Войдите, чтобы оформить заказ.").classes("muted")
        email = ui.input("Email").props("outlined type=email").classes("w-full")
        password = ui.input("Пароль", password=True, password_toggle_button=True).props("outlined").classes("w-full")

        async def submit() -> None:
            async with SessionLocal() as db:
                user = await get_user_by_email(db, email.value or "")
                if user is None or not verify_password(password.value or "", user.password_hash):
                    ui.notify("Неверный email или пароль", type="negative")
                    return
                app.storage.user["user_id"] = user.id
                ui.navigate.to("/")

        ui.button("Войти", on_click=submit).props("no-caps").classes("accent-button w-full")
        ui.link("Нет аккаунта? Зарегистрироваться", "/register").classes("text-center")


@ui.page("/register")
async def register_page() -> None:
    page_shell()
    await header()
    with ui.card().classes("soft-card w-[92vw] max-w-md mx-auto mt-12 p-7 gap-4"):
        ui.label("Создать аккаунт").classes("text-3xl font-black")
        name = ui.input("Имя").props("outlined").classes("w-full")
        email = ui.input("Email").props("outlined type=email").classes("w-full")
        password = ui.input("Пароль", password=True, password_toggle_button=True).props("outlined").classes("w-full")

        async def submit() -> None:
            try:
                payload = UserCreate(name=name.value or "", email=email.value or "", password=password.value or "")
                async with SessionLocal() as db:
                    user = await create_user(db, payload)
                app.storage.user["user_id"] = user.id
                ui.navigate.to("/")
            except (ValueError, HTTPException) as exc:
                detail = getattr(exc, "detail", "Проверьте заполнение полей")
                ui.notify(str(detail), type="negative")

        ui.button("Зарегистрироваться", on_click=submit).props("no-caps").classes("accent-button w-full")


@ui.page("/cart")
async def cart_page() -> None:
    page_shell()
    await header()
    ids = [int(product_id) for product_id in cart()]
    async with SessionLocal() as db:
        products = (await db.scalars(select(Product).where(Product.id.in_(ids)))).all() if ids else []
    with ui.column().classes("w-full max-w-4xl mx-auto p-4 md:p-8 gap-6"):
        ui.label("Корзина").classes("text-4xl font-black")
        if not products:
            with ui.card().classes("soft-card w-full p-10 items-center"):
                ui.label("🛍️").classes("text-6xl")
                ui.label("Здесь пока пусто").classes("text-2xl font-bold")
                ui.button("В каталог", on_click=lambda: ui.navigate.to("/")).classes("accent-button")
            return
        total = Decimal("0")
        for product in products:
            quantity = cart()[str(product.id)]
            total += product.price * quantity
            with ui.row().classes("soft-card w-full p-4 items-center gap-4"):
                ui.label(product.emoji).classes("text-4xl")
                with ui.column().classes("gap-0"):
                    ui.label(product.name).classes("font-bold")
                    ui.label(f"{quantity} × {money(product.price)}").classes("muted")
                ui.space()
                ui.label(money(product.price * quantity)).classes("font-bold")
        ui.separator()
        ui.label(f"Итого: {money(total)}").classes("text-2xl font-black self-end")
        address = ui.input("Адрес доставки").props("outlined").classes("w-full")

        async def checkout() -> None:
            user = await current_user()
            if user is None:
                ui.notify("Сначала войдите в аккаунт", type="warning")
                ui.navigate.to("/login")
                return
            try:
                payload = OrderCreate(
                    shipping_address=address.value or "",
                    items=[
                        OrderItemCreate(product_id=int(product_id), quantity=quantity)
                        for product_id, quantity in cart().items()
                    ],
                )
                async with SessionLocal() as db:
                    await create_order(db, user, payload)
                app.storage.user["cart"] = {}
                ui.notify("Заказ оформлен!", type="positive")
                ui.navigate.to("/orders")
            except (ValueError, HTTPException) as exc:
                ui.notify(str(getattr(exc, "detail", "Проверьте адрес")), type="negative")

        ui.button("Оформить заказ", on_click=checkout).props("no-caps").classes("accent-button self-end px-8")


@ui.page("/orders")
async def orders_page() -> None:
    page_shell()
    await header()
    user = await current_user()
    if user is None:
        ui.navigate.to("/login")
        return
    async with SessionLocal() as db:
        orders = (
            await db.scalars(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.user_id == user.id)
                .order_by(Order.created_at.desc())
            )
        ).all()
    with ui.column().classes("w-full max-w-4xl mx-auto p-4 md:p-8 gap-5"):
        ui.label("Мои заказы").classes("text-4xl font-black")
        if not orders:
            ui.label("Вы ещё ничего не заказывали.").classes("muted")
        for order in orders:
            with ui.card().classes("soft-card w-full p-5"):
                with ui.row().classes("w-full"):
                    ui.label(f"Заказ №{order.id}").classes("text-xl font-bold")
                    ui.space()
                    ui.badge(order.status.value.upper()).props("outline color=primary")
                ui.label(" · ".join(f"{item.product_name} × {item.quantity}" for item in order.items)).classes("muted")
                ui.label(money(order.total)).classes("font-black")


@ui.page("/admin")
async def admin_page() -> None:
    page_shell()
    await header()
    user = await current_user()
    if user is None or user.role != UserRole.admin:
        ui.navigate.to("/")
        return
    async with SessionLocal() as db:
        products = (await db.scalars(select(Product).order_by(Product.id))).all()
        orders_count = await db.scalar(select(func.count(Order.id))) or 0
        users_count = await db.scalar(select(func.count(User.id))) or 0
        revenue = await db.scalar(select(func.coalesce(func.sum(Order.total), 0))) or 0

    with ui.column().classes("w-full max-w-6xl mx-auto p-4 md:p-8 gap-6"):
        ui.label("Панель управления").classes("text-4xl font-black")
        with ui.grid(columns=1).classes("w-full sm:grid-cols-3 gap-4"):
            for label, value in (("Пользователи", users_count), ("Заказы", orders_count), ("Выручка", money(revenue))):
                with ui.card().classes("soft-card p-5"):
                    ui.label(label).classes("muted")
                    ui.label(str(value)).classes("text-3xl font-black")

        with ui.dialog() as dialog, ui.card().classes("w-[92vw] max-w-lg p-6"):
            ui.label("Новый товар").classes("text-2xl font-bold")
            name = ui.input("Название").classes("w-full")
            description = ui.input("Описание").classes("w-full")
            category = ui.input("Категория").classes("w-full")
            emoji = ui.input("Эмодзи", value="✨").classes("w-full")
            price = ui.input("Цена", value="1000").classes("w-full")
            stock = ui.number("Остаток", value=10, min=0).classes("w-full")

            async def save_product() -> None:
                try:
                    value = Decimal(price.value or "0")
                    async with SessionLocal() as db:
                        db.add(Product(name=name.value, description=description.value, category=category.value,
                                       emoji=emoji.value, price=value, stock=int(stock.value or 0)))
                        await db.commit()
                    ui.notify("Товар добавлен", type="positive")
                    dialog.close()
                    ui.navigate.reload()
                except (InvalidOperation, ValueError):
                    ui.notify("Проверьте поля", type="negative")

            ui.button("Сохранить", on_click=save_product).classes("accent-button")

        with ui.row().classes("w-full items-center"):
            ui.label("Товары").classes("text-2xl font-bold")
            ui.space()
            ui.button("Добавить", icon="add", on_click=dialog.open).props("no-caps").classes("accent-button")
        rows = [
            {"id": p.id, "name": p.name, "category": p.category, "price": money(p.price), "stock": p.stock, "active": "Да" if p.is_active else "Нет"}
            for p in products
        ]
        ui.table(
            columns=[{"name": key, "label": label, "field": key, "align": "left"} for key, label in (
                ("id", "ID"), ("name", "Название"), ("category", "Категория"), ("price", "Цена"), ("stock", "Остаток"), ("active", "Активен")
            )],
            rows=rows,
            row_key="id",
        ).classes("w-full soft-card")


def attach_nicegui(fastapi_app: FastAPI) -> None:
    ui.run_with(
        fastapi_app,
        storage_secret=settings.secret_key,
        title=settings.app_name,
        favicon="🌙",
    )

