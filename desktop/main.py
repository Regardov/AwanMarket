import json
import sys
from datetime import datetime

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if __package__:
    from .client import STATUSES, Api, ApiError, money, reconcile, total_price
    from .tasks import run_task
else:
    from client import STATUSES, Api, ApiError, money, reconcile, total_price
    from tasks import run_task


def label(text, name="", wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, callback):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    return widget


def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())


class AuthDialog(QDialog):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.busy = False
        self.setWindowTitle("Аккаунт · AwanMarket")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        self.mode = QComboBox()
        self.mode.addItems(["Вход", "Регистрация"])
        layout.addWidget(self.mode)
        form = QFormLayout()
        self.name, self.email, self.password = QLineEdit(), QLineEdit(), QLineEdit()
        self.name.setMaxLength(100)
        self.email.setMaxLength(320)
        self.password.setMaxLength(128)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Имя", self.name)
        form.addRow("Email", self.email)
        form.addRow("Пароль", self.password)
        self.name.setEnabled(False)
        self.mode.currentIndexChanged.connect(lambda index: self.name.setEnabled(bool(index)))
        layout.addLayout(form)
        self.error = label("", "error", True)
        layout.addWidget(self.error)
        self.submit_button = button("Продолжить", self.submit)
        layout.addWidget(self.submit_button)
        self.password.returnPressed.connect(self.submit)

    def reject(self):
        if not self.busy:
            super().reject()

    def submit(self):
        if self.busy:
            return
        register = self.mode.currentIndex() == 1
        if "@" not in self.email.text() or not self.password.text():
            self.error.setText("Укажите email и пароль.")
            return
        if register and (len(self.name.text().strip()) < 2 or len(self.password.text()) < 8):
            self.error.setText("Имя — от 2 символов, пароль — от 8.")
            return
        self.busy = True
        self.submit_button.setEnabled(False)
        self.mode.setEnabled(False)
        self.error.setText("Выполняется вход…")
        action = "register" if register else "login"
        email, password, name = self.email.text(), self.password.text(), self.name.text()

        def done(data, error):
            self.busy = False
            self.submit_button.setEnabled(True)
            self.mode.setEnabled(True)
            if error:
                self.error.setText(str(error))
            else:
                self.api.token, self.api.user = data["access_token"], data["user"]
                self.accept()

        run_task(self, lambda: self.api.auth(action, email, password, name), done)


class CartDialog(QDialog):
    def __init__(self, store):
        super().__init__(store)
        self.store = store
        self.busy = False
        self.setWindowTitle("Корзина · AwanMarket")
        self.resize(600, 620)
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.rows = QVBoxLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.total = label("", "price")
        layout.addWidget(self.total)
        self.address = QLineEdit(store.settings.value("address", ""))
        self.address.setPlaceholderText("Город, улица, дом, квартира")
        self.address.setMaxLength(500)
        self.address.textChanged.connect(lambda value: store.settings.setValue("address", value))
        layout.addWidget(self.address)
        self.error = label("", "error", True)
        layout.addWidget(self.error)
        self.checkout = button("Оформить заказ", self.submit)
        layout.addWidget(self.checkout)
        self.render()

    def reject(self):
        if not self.busy:
            super().reject()

    def render(self):
        clear(self.rows)
        for product in self.store.products:
            key = product["id"]
            if key not in self.store.cart:
                continue
            row = QHBoxLayout()
            row.addWidget(
                label(
                    f"{product['emoji']} {product['name']}\n{money(product['price'])}", wrap=True
                ),
                1,
            )
            quantity = QSpinBox()
            quantity.setRange(1, min(99, product["stock"]))
            quantity.setValue(self.store.cart[key])
            quantity.setEnabled(not self.busy)
            quantity.valueChanged.connect(lambda value, key=key: self.change(key, value))
            row.addWidget(quantity)
            remove = button("Удалить", lambda _, key=key: self.remove(key))
            remove.setEnabled(not self.busy)
            row.addWidget(remove)
            self.rows.addLayout(row)
        if not self.store.cart:
            self.rows.addWidget(label("Корзина пуста. Добавьте продукты из каталога.", wrap=True))
        self.rows.addStretch()
        self.update_total()

    def change(self, key, value):
        self.store.cart[key] = value
        self.store.cart_changed()
        self.update_total()

    def remove(self, key):
        self.store.cart.pop(key, None)
        self.store.cart_changed()
        self.render()

    def update_total(self):
        self.total.setText(f"Итого: {money(total_price(self.store.cart, self.store.products))}")
        self.checkout.setEnabled(bool(self.store.cart) and not self.busy)

    def submit(self):
        if self.busy or not self.store.cart:
            return
        if not self.store.api.token and not self.store.login():
            return
        address = self.address.text().strip()
        if len(address) < 8:
            self.error.setText("Укажите полный адрес доставки (от 8 символов).")
            return
        self.busy = True
        self.address.setEnabled(False)
        self.error.setText("Оформляем заказ…")
        self.render()
        cart = self.store.cart.copy()

        def done(order, error):
            self.busy = False
            self.address.setEnabled(True)
            if error:
                self.store.handle_auth_error(error)
                self.error.setText(str(error))
                self.render()
                return
            self.store.cart.clear()
            self.store.cart_changed()
            self.accept()
            self.store.notice.setText(f"Заказ №{order['id']} принят · {money(order['total'])}")
            self.store.load_products()
            self.store.load_orders()

        run_task(self, lambda: self.store.api.order(cart, address), done)


class ProductCard(QFrame):
    def __init__(self, product, store):
        super().__init__()
        self.setObjectName("card")
        self.setMinimumWidth(225)
        self.setMinimumHeight(390)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        emoji = label(product["emoji"], "emoji")
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji.setFixedHeight(90)
        layout.addWidget(emoji)
        layout.addWidget(label(product["category"].upper(), "category"))
        layout.addWidget(label(product["name"], "title", True))
        layout.addWidget(label(product["description"], "muted", True))
        layout.addStretch()
        layout.addWidget(label(money(product["price"]), "price"))
        layout.addWidget(
            label(
                f"В наличии: {product['stock']}" if product["stock"] else "Нет в наличии", "muted"
            )
        )
        add = button("В корзину", lambda: store.add(product["id"]))
        add.setEnabled(product["stock"] > 0)
        layout.addWidget(add)


class MainWindow(QMainWindow):
    def __init__(self, api=None, settings=None):
        super().__init__()
        self.api = api or Api()
        self.settings = settings or QSettings("AwanMarket", "Desktop")
        try:
            saved = json.loads(self.settings.value("cart", "{}"))
            self.cart = {
                int(key): value
                for key, value in saved.items()
                if isinstance(value, int) and 0 < value <= 99
            }
        except (ValueError, TypeError, AttributeError):
            self.cart = {}
        self.products = []
        self.loading = False
        self.orders_loading = False
        self.columns = 0
        self.setWindowTitle("AwanMarket · продукты каждый день")
        self.resize(1180, 840)
        self.setMinimumSize(760, 560)
        self.build()
        self.cart_changed()
        self.load_products()

    def build(self):
        root = QWidget()
        main = QVBoxLayout(root)
        main.setContentsMargins(28, 20, 28, 20)
        main.setSpacing(16)
        nav = QHBoxLayout()
        nav.addWidget(label("AWANMARKET", "logo"))
        nav.addStretch()
        self.account = button("Войти", self.account_action)
        nav.addWidget(self.account)
        self.cart_button = button("Корзина · 0", self.open_cart)
        nav.addWidget(self.cart_button)
        main.addLayout(nav)
        self.notice = label("", "muted", True)
        main.addWidget(self.notice)
        self.tabs = QTabWidget()
        catalogue = QWidget()
        layout = QVBoxLayout(catalogue)
        hero = QFrame()
        hero.setObjectName("hero")
        h = QVBoxLayout(hero)
        h.addWidget(label("СВЕЖЕЕ КАЖДЫЙ ДЕНЬ", "overline"))
        h.addWidget(label("Продукты для вашего дня", "headline", True))
        h.addWidget(label("Соберите корзину — мы позаботимся об остальном.", wrap=True))
        layout.addWidget(hero)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Найти продукты…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.render_products)
        filters.addWidget(self.search, 1)
        self.category = QComboBox()
        self.category.addItem("Все категории")
        self.category.currentIndexChanged.connect(self.render_products)
        filters.addWidget(self.category)
        self.sort = QComboBox()
        self.sort.addItems(["По умолчанию", "Сначала дешевле", "Сначала дороже", "По названию"])
        self.sort.currentIndexChanged.connect(self.render_products)
        filters.addWidget(self.sort)
        self.refresh = button("Обновить", self.load_products)
        filters.addWidget(self.refresh)
        layout.addLayout(filters)
        self.catalogue_status = label("", "muted", True)
        layout.addWidget(self.catalogue_status)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid.setSpacing(16)
        self.scroll.setWidget(content)
        layout.addWidget(self.scroll, 1)
        self.tabs.addTab(catalogue, "Каталог")
        orders_page = QWidget()
        orders_layout = QVBoxLayout(orders_page)
        orders_layout.addWidget(button("Обновить заказы", self.load_orders))
        self.orders_status = label("Войдите, чтобы увидеть свои заказы.", "muted", True)
        orders_layout.addWidget(self.orders_status)
        orders_scroll = QScrollArea()
        orders_scroll.setWidgetResizable(True)
        orders_content = QWidget()
        self.order_rows = QVBoxLayout(orders_content)
        self.order_rows.setAlignment(Qt.AlignmentFlag.AlignTop)
        orders_scroll.setWidget(orders_content)
        orders_layout.addWidget(orders_scroll, 1)
        self.tabs.addTab(orders_page, "Мои заказы")
        self.tabs.currentChanged.connect(lambda index: self.load_orders() if index == 1 else None)
        main.addWidget(self.tabs, 1)
        self.setCentralWidget(root)
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.reflow)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "resize_timer"):
            self.resize_timer.start(80)

    def reflow(self):
        columns = max(1, self.scroll.viewport().width() // 260)
        if columns != self.columns:
            self.render_products()

    def load_products(self):
        if self.loading:
            return
        self.loading = True
        self.refresh.setEnabled(False)
        self.cart_button.setEnabled(False)
        self.catalogue_status.setText("Обновляем каталог…")

        def done(products, error):
            self.loading = False
            self.refresh.setEnabled(True)
            self.cart_button.setEnabled(bool(self.products) or not error)
            if error:
                self.catalogue_status.setText(f"{error} Нажмите «Обновить».")
                return
            self.products = products
            if reconcile(self.cart, products):
                self.notice.setText("Корзина обновлена с учётом доступных товаров и остатков.")
            self.cart_changed()
            selected = self.category.currentText()
            self.category.blockSignals(True)
            self.category.clear()
            self.category.addItems(["Все категории", *sorted({p["category"] for p in products})])
            index = self.category.findText(selected)
            self.category.setCurrentIndex(max(0, index))
            self.category.blockSignals(False)
            self.render_products()

        run_task(self, self.api.products, done)

    def render_products(self):
        clear(self.grid)
        query = self.search.text().strip().casefold()
        category = self.category.currentText()
        products = [
            p
            for p in self.products
            if (not query or query in (p["name"] + " " + p["description"]).casefold())
            and (self.category.currentIndex() <= 0 or p["category"] == category)
        ]
        sort = self.sort.currentIndex()
        if sort in (1, 2):
            products.sort(key=lambda p: float(p["price"]), reverse=sort == 2)
        elif sort == 3:
            products.sort(key=lambda p: p["name"].casefold())
        self.columns = max(1, self.scroll.viewport().width() // 260)
        for index, product in enumerate(products):
            self.grid.addWidget(
                ProductCard(product, self), index // self.columns, index % self.columns
            )
        self.catalogue_status.setText(
            f"Найдено товаров: {len(products)}"
            if products
            else "Ничего не найдено. Измените поиск или категорию."
        )

    def cart_changed(self):
        self.settings.setValue("cart", json.dumps(self.cart))
        self.cart_button.setText(f"Корзина · {sum(self.cart.values())}")

    def add(self, key):
        product = next(p for p in self.products if p["id"] == key)
        if self.cart.get(key, 0) >= min(99, product["stock"]):
            self.notice.setText("В корзине уже всё доступное количество этого товара.")
            return
        if key not in self.cart and len(self.cart) >= 50:
            self.notice.setText("В одном заказе может быть до 50 разных товаров.")
            return
        self.cart[key] = self.cart.get(key, 0) + 1
        self.cart_changed()
        self.notice.setText(f"Добавлено: {product['name']}")

    def login(self):
        if AuthDialog(self.api, self).exec():
            self.account.setText(self.api.user["name"] + " · Выйти")
            self.load_orders()
            return True
        return False

    def account_action(self):
        if self.api.token:
            self.api.logout()
            self.account.setText("Войти")
            clear(self.order_rows)
            self.orders_status.setText("Войдите, чтобы увидеть свои заказы.")
        else:
            self.login()

    def handle_auth_error(self, error):
        if isinstance(error, ApiError) and error.status == 401:
            self.api.logout()
            self.account.setText("Войти")
            clear(self.order_rows)

    def open_cart(self):
        if not self.loading:
            CartDialog(self).exec()

    def load_orders(self):
        if not self.api.token:
            self.orders_status.setText("Войдите, чтобы увидеть свои заказы.")
            return
        if self.orders_loading:
            return
        self.orders_loading = True
        token = self.api.token
        self.orders_status.setText("Загружаем заказы…")

        def done(orders, error):
            self.orders_loading = False
            if token != self.api.token:
                if self.api.token:
                    self.load_orders()
                return
            clear(self.order_rows)
            if error:
                self.handle_auth_error(error)
                self.orders_status.setText(str(error))
                return
            self.orders_status.setText(
                f"Ваши заказы: {len(orders)}" if orders else "Заказов пока нет. Начните с каталога."
            )
            for order in orders:
                frame = QFrame()
                frame.setObjectName("card")
                layout = QVBoxLayout(frame)
                date = datetime.fromisoformat(order["created_at"].replace("Z", "+00:00")).strftime(
                    "%d.%m.%Y %H:%M"
                )
                layout.addWidget(
                    label(
                        f"Заказ №{order['id']} · {STATUSES.get(order['status'], order['status'])}",
                        "title",
                        True,
                    )
                )
                layout.addWidget(label(f"{date} · {money(order['total'])}", "price"))
                layout.addWidget(label(order["shipping_address"], "muted", True))
                for item in order["items"]:
                    layout.addWidget(
                        label(
                            f"{item['product_name']} × {item['quantity']} · {money(item['unit_price'])}",
                            wrap=True,
                        )
                    )
                self.order_rows.addWidget(frame)

        run_task(self, self.api.orders, done)


STYLE = """
QWidget { background:#f7f3eb; color:#17211d; font:14px 'Segoe UI'; }
QPushButton { background:#426950; color:white; border:0; border-radius:12px; padding:10px 16px; font-weight:600; }
QPushButton:hover { background:#294438; }
QPushButton:disabled { background:#dce1da; color:#69766d; }
QLineEdit, QComboBox, QSpinBox { background:white; border:1px solid #cad4cc; border-radius:8px; padding:9px; }
QScrollArea { border:0; }
QTabWidget::pane { border:0; }
QTabBar::tab { padding:12px 22px; }
QTabBar::tab:selected { color:#294438; border-bottom:3px solid #426950; }
#logo { font-size:23px; font-weight:900; letter-spacing:2px; }
#hero { background:#294438; border-radius:20px; padding:20px; }
#hero QLabel { background:transparent; color:white; }
#overline { color:#ffdf9e; letter-spacing:2px; font-size:11px; }
#headline { font-size:30px; font-weight:900; }
#card { background:white; border:1px solid #e0e4df; border-radius:18px; padding:14px; }
#card QLabel { background:transparent; }
#emoji { font-size:48px; min-height:85px; }
#category { color:#426950; font-size:11px; }
#title { font-size:17px; font-weight:700; }
#price { font-size:18px; font-weight:800; }
#muted { color:#647168; }
#error { color:#9e342b; }
"""


def main():
    application = QApplication(sys.argv)
    application.setOrganizationName("AwanMarket")
    application.setApplicationName("Desktop")
    application.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(application.exec())


if __name__ == "__main__":
    main()
