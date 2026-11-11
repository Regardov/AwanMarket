from decimal import Decimal

import pytest
import requests

from desktop.client import Api, ApiError, reconcile, total_price


def test_reconcile_and_exact_total():
    products = [{"id": 1, "price": "1.10", "stock": 2}, {"id": 2, "price": "0.20", "stock": 0}]
    cart = {1: 8, 2: 1, 3: 1}
    assert reconcile(cart, products)
    assert cart == {1: 2}
    assert total_price(cart, products) == Decimal("2.20")


def test_api_timeout_and_validation_errors(monkeypatch):
    def offline(*args, **kwargs):
        assert kwargs["timeout"] == (5, 15)
        raise requests.Timeout()

    monkeypatch.setattr(requests, "request", offline)
    with pytest.raises(ApiError, match="Нет связи"):
        Api().products()

    response = requests.Response()
    response.status_code = 422
    response._content = b'{"detail":[{"msg":"Address too short"}]}'
    monkeypatch.setattr(requests, "request", lambda *args, **kwargs: response)
    with pytest.raises(ApiError, match="Address too short"):
        Api().order({1: 1}, "short")
