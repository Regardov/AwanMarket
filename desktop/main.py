import os
import sys
from collections import defaultdict

import requests
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

API_BASE = os.getenv("LUNORA_API_URL", "http://127.0.0.1:8080")


class Api:
    def __init__(self) -> None:
        self.token: str | None = None

    def request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = requests.request(
            method, f"{API_BASE}{path}", headers=headers, timeout=10, **kwargs
        )
        if not response.ok:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(detail or f"HTTP {response.status_code}")
        return response.json() if response.content else None

    def products(self) -> list[dict]:
        return self.request("GET", "/api/products")

    def auth(self, action: str, email: str, password: str, name: str = "") -> None:
        payload = {"email": email, "password": password}
        if action == "register":
            payload["name"] = name
        data = self.request("POST", f"/api/auth/{action}", json=payload)
        self.token = data["access_token"]

    def order(self, cart: dict[int, int], address: str) -> dict:
        return self.request(
            "POST",
            "/api/orders",
            json={
                "shipping_address": address,
                "items": [
                    {"product_id": product_id, "quantity": quantity}
                    for product_id, quantity in cart.items()
                ],
            },
        )


class AuthDialog(QDialog):
    def __init__(self, api: Api, parent=None) -> None:
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Lunora — аккаунт")
        self.setMinimumWidth(390)
        tabs = QTabWidget()
        tabs.addTab(self.form("login"), "Вход")
        tabs.addTab(self.form("register"), "Регистрация")
        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

    def form(self, action: str) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        name = QLineEdit()
        email = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.EchoMode.Password)
        if action == "register":
            layout.addRow("Имя", name)
        layout.addRow("Email", email)
        layout.addRow("Пароль", password)
        button = QPushButton("Создать аккаунт" if action == "register" else "Войти")

        def submit() -> None:
            try:
                self.api.auth(action, email.text(), password.text(), name.text())
                self.accept()
            except (RuntimeError, requests.RequestException) as error:
                QMessageBox.warning(self, "Ошибка", str(error))

        button.clicked.connect(submit)
        layout.addRow(button)
        return widget


class CartDialog(QDialog):
    def __init__(self, api: Api, products: list[dict], cart: dict[int, int], parent=None) -> None:
        super().__init__(parent)
        self.api, self.products, self.cart = api, products, cart
        self.setWindowTitle("Корзина")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        total = 0.0
        by_id = {product["id"]: product for product in products}
        for product_id, quantity in cart.items():
            product = by_id[product_id]
            price = float(product["price"])
            total += price * quantity
            label = QLabel(f"{product['emoji']}  {product['name']}   × {quantity}   {price * quantity:,.0f} ₽")
            layout.addWidget(label)
        if not cart:
            layout.addWidget(QLabel("Корзина пока пуста"))
        layout.addWidget(QLabel(f"Итого: {total:,.0f} ₽"))
        self.address = QLineEdit()
        self.address.setPlaceholderText("Адрес доставки")
        layout.addWidget(self.address)
        checkout = QPushButton("Оформить заказ")
        checkout.setEnabled(bool(cart))
        checkout.clicked.connect(self.submit)
        layout.addWidget(checkout)

    def submit(self) -> None:
        if not self.api.token:
            QMessageBox.information(self, "Нужен вход", "Сначала войдите или зарегистрируйтесь.")
            return
        try:
            self.api.order(self.cart, self.address.text())
            self.cart.clear()
            QMessageBox.information(self, "Готово", "Заказ успешно оформлен!")
            self.accept()
        except (RuntimeError, requests.RequestException) as error:
            QMessageBox.warning(self, "Ошибка", str(error))


class ProductCard(QFrame):
    def __init__(self, product: dict, add_callback, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumSize(260, 280)
        layout = QVBoxLayout(self)
        emoji = QLabel(product["emoji"])
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji.setObjectName("emoji")
        layout.addWidget(emoji, 1)
        category = QLabel(product["category"].upper())
        category.setObjectName("category")
        layout.addWidget(category)
        title = QLabel(product["name"])
        title.setObjectName("title")
        layout.addWidget(title)
        description = QLabel(product["description"])
        description.setWordWrap(True)
        description.setObjectName("muted")
        layout.addWidget(description)
        row = QHBoxLayout()
        price = QLabel(f"{float(product['price']):,.0f} ₽")
        price.setObjectName("price")
        button = QPushButton("В корзину")
        button.clicked.connect(lambda: add_callback(product["id"]))
        row.addWidget(price)
        row.addStretch()
        row.addWidget(button)
        layout.addLayout(row)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.api = Api()
        self.products: list[dict] = []
        self.cart: dict[int, int] = defaultdict(int)
        self.setWindowTitle("Lunora Market")
        self.resize(1120, 760)
        self.build()
        self.load_products()

    def build(self) -> None:
        root = QWidget()
        main = QVBoxLayout(root)
        nav = QHBoxLayout()
        logo = QLabel("☾  L U N O R A")
        logo.setObjectName("logo")
        self.status = QLabel("Гость")
        login = QPushButton("Войти")
        login.clicked.connect(self.login)
        self.cart_button = QPushButton("Корзина · 0")
        self.cart_button.clicked.connect(self.open_cart)
        nav.addWidget(logo)
        nav.addStretch()
        nav.addWidget(self.status)
        nav.addWidget(login)
        nav.addWidget(self.cart_button)
        main.addLayout(nav)
        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QVBoxLayout(hero)
        overline = QLabel("ВЕЩИ С ТИХИМ ХАРАКТЕРОМ")
        overline.setObjectName("overline")
        headline = QLabel("Маленькие радости\nдля дома и тебя")
        headline.setObjectName("headline")
        hero_layout.addStretch()
        hero_layout.addWidget(overline)
        hero_layout.addWidget(headline)
        hero_layout.addWidget(QLabel("Уютные, честные и долговечные вещи — без лишнего шума."))
        hero_layout.addStretch()
        main.addWidget(hero)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setSpacing(18)
        scroll.setWidget(content)
        main.addWidget(scroll, 1)
        self.setCentralWidget(root)

    def load_products(self) -> None:
        try:
            self.products = self.api.products()
            for index, product in enumerate(self.products):
                self.grid.addWidget(ProductCard(product, self.add), index // 3, index % 3)
        except (RuntimeError, requests.RequestException) as error:
            QMessageBox.critical(self, "Нет соединения", f"Не удалось открыть магазин:\n{error}")

    def add(self, product_id: int) -> None:
        self.cart[product_id] += 1
        self.cart_button.setText(f"Корзина · {sum(self.cart.values())}")

    def login(self) -> None:
        if AuthDialog(self.api, self).exec():
            self.status.setText("Вы вошли")

    def open_cart(self) -> None:
        CartDialog(self.api, self.products, self.cart, self).exec()
        self.cart_button.setText(f"Корзина · {sum(self.cart.values())}")


STYLE = """
QWidget { background:#f7f3eb; color:#17211d; font:14px 'Segoe UI'; }
QPushButton { background:#637f6d; color:white; border:0; border-radius:16px; padding:9px 16px; font-weight:600; }
QPushButton:hover { background:#496553; }
QLineEdit { background:white; border:1px solid #cad4cc; border-radius:10px; padding:10px; }
#logo { font-size:20px; font-weight:900; letter-spacing:3px; }
#hero { background:#294438; color:white; border-radius:24px; min-height:230px; padding:25px; }
#hero QLabel { background:transparent; color:white; }
#overline { color:#ffdf9e; letter-spacing:3px; font-size:11px; }
#headline { font-size:38px; font-weight:900; }
#card { background:white; border:1px solid #e0e4df; border-radius:20px; padding:12px; }
#emoji { background:#dfeadf; border-radius:16px; font-size:52px; min-height:105px; }
#category { color:#637f6d; font-size:10px; letter-spacing:2px; }
#title { font-size:18px; font-weight:700; }
#price { font-size:18px; font-weight:900; }
#muted { color:#647168; }
"""


def main() -> None:
    application = QApplication(sys.argv)
    application.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()

