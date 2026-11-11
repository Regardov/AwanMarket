import threading

from PyQt6.QtCore import QSettings

from desktop.client import Api
from desktop.main import CartDialog, MainWindow

PRODUCT = {
    "id": 1,
    "name": "Молоко",
    "emoji": "🥛",
    "category": "Молочное",
    "description": "Свежее",
    "stock": 2,
    "price": "109.25",
}


class FakeApi(Api):
    def products(self):
        return [PRODUCT.copy()]

    def orders(self):
        return []


def window(qtbot, tmp_path, api=None):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    widget = MainWindow(api=api or FakeApi(), settings=settings)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitUntil(lambda: not widget.loading)
    return widget


def test_filters_stock_cart_editing_and_persistence(qtbot, tmp_path):
    store = window(qtbot, tmp_path)
    store.search.setText("несуществующий")
    assert store.grid.count() == 0
    store.search.clear()
    assert store.grid.count() == 1
    for _ in range(3):
        store.add(1)
    assert store.cart == {1: 2}
    dialog = CartDialog(store)
    qtbot.addWidget(dialog)
    dialog.change(1, 1)
    assert dialog.total.text() == "Итого: 109,25 ₽"
    dialog.remove(1)
    assert store.cart == {}
    assert store.settings.value("cart") == "{}"
    assert not dialog.checkout.isEnabled()


def test_catalogue_runs_outside_ui_thread(qtbot, tmp_path):
    gate = threading.Event()

    class SlowApi(FakeApi):
        def products(self):
            gate.wait(3)
            return super().products()

    settings = QSettings(str(tmp_path / "slow.ini"), QSettings.Format.IniFormat)
    widget = MainWindow(api=SlowApi(), settings=settings)
    qtbot.addWidget(widget)
    try:
        assert widget.loading
        widget.search.setText("молоко")
        assert widget.search.text() == "молоко"
    finally:
        gate.set()
    qtbot.waitUntil(lambda: not widget.loading)
    assert widget.grid.count() == 1


def test_checkout_prevents_double_submit_and_clears_cart(qtbot, tmp_path):
    gate = threading.Event()

    class CheckoutApi(FakeApi):
        calls = 0

        def order(self, cart, address):
            self.calls += 1
            assert cart == {1: 1}
            gate.wait(3)
            return {"id": 7, "total": "109.25"}

    api = CheckoutApi()
    api.token = "token"
    store = window(qtbot, tmp_path, api)
    store.add(1)
    dialog = CartDialog(store)
    qtbot.addWidget(dialog)
    dialog.address.setText("Москва, улица Лесная, 1")
    try:
        dialog.submit()
        dialog.submit()
        assert dialog.busy
        assert not dialog.checkout.isEnabled()
    finally:
        gate.set()
    qtbot.waitUntil(lambda: not dialog.busy)
    qtbot.waitUntil(lambda: not store.loading and not store.orders_loading)
    assert api.calls == 1
    assert store.cart == {}
