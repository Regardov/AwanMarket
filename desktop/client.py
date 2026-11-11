"""HTTP and cart rules shared by the desktop screens (no Qt dependency)."""

import os
from decimal import Decimal

import requests


class ApiError(RuntimeError):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def error_message(detail) -> str:
    if isinstance(detail, list):
        return "\n".join(str(item.get("msg", item)) for item in detail)
    return str(detail)


class Api:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (
            base_url or os.getenv("AWANMARKET_API_URL", "http://127.0.0.1:8080")
        ).rstrip("/")
        self.token: str | None = None
        self.user: dict | None = None

    def request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = requests.request(
                method, f"{self.base_url}{path}", headers=headers, timeout=(5, 15), **kwargs
            )
        except requests.RequestException as error:
            raise ApiError(
                "Нет связи с сервером. Проверьте подключение и повторите попытку."
            ) from error
        if not response.ok:
            try:
                detail = response.json().get("detail", "Ошибка сервера")
            except ValueError:
                detail = f"Ошибка сервера: HTTP {response.status_code}"
            if response.status_code == 401:
                detail = "Неверный email или пароль, либо срок входа истёк. Войдите снова."
            raise ApiError(error_message(detail), response.status_code)
        try:
            return response.json() if response.content else None
        except ValueError as error:
            raise ApiError("Сервер вернул некорректный ответ.") from error

    def products(self) -> list[dict]:
        return self.request("GET", "/api/products")

    def auth(self, action: str, email: str, password: str, name: str = "") -> dict:
        payload = {"email": email.strip(), "password": password}
        if action == "register":
            payload["name"] = name.strip()
        return self.request("POST", f"/api/auth/{action}", json=payload)

    def orders(self) -> list[dict]:
        return self.request("GET", "/api/orders")

    def order(self, cart: dict[int, int], address: str) -> dict:
        return self.request(
            "POST",
            "/api/orders",
            json={
                "shipping_address": address.strip(),
                "items": [{"product_id": key, "quantity": value} for key, value in cart.items()],
            },
        )

    def logout(self) -> None:
        self.token = self.user = None


def reconcile(cart: dict[int, int], products: list[dict]) -> bool:
    """Drop unavailable items and clamp quantities after a catalogue refresh."""
    previous = cart.copy()
    by_id = {p["id"]: p for p in products}
    for key, quantity in list(cart.items()):
        limit = min(99, by_id.get(key, {}).get("stock", 0))
        if limit <= 0 or not isinstance(quantity, int) or quantity <= 0:
            del cart[key]
        else:
            cart[key] = min(quantity, limit)
    return cart != previous


def total_price(cart: dict[int, int], products: list[dict]) -> Decimal:
    return sum((Decimal(str(p["price"])) * cart.get(p["id"], 0) for p in products), Decimal(0))


def money(value) -> str:
    return f"{Decimal(str(value)):,.2f}".replace(",", " ").replace(".", ",") + " ₽"


STATUSES = {
    "new": "Принят",
    "paid": "Оплачен",
    "shipped": "В пути",
    "completed": "Доставлен",
    "cancelled": "Отменён",
}
