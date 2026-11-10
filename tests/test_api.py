from uuid import uuid4


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_registration_products_and_order(client):
    email = f"buyer-{uuid4().hex}@example.com"
    registration = client.post(
        "/api/auth/register",
        json={"name": "Тестовый покупатель", "email": email, "password": "StrongPass123!"},
    )
    assert registration.status_code == 201
    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    products = client.get("/api/products")
    assert products.status_code == 200
    assert len(products.json()) >= 1

    order = client.post(
        "/api/orders",
        headers=headers,
        json={
            "shipping_address": "Москва, Тверская улица, дом 1",
            "items": [{"product_id": products.json()[0]["id"], "quantity": 1}],
        },
    )
    assert order.status_code == 201
    assert order.json()["total"] != "0.00"

    history = client.get("/api/orders", headers=headers)
    assert history.status_code == 200
    assert any(item["id"] == order.json()["id"] for item in history.json())


def test_admin_access_and_product_crud(client, admin_headers):
    stats = client.get("/api/admin/stats", headers=admin_headers)
    assert stats.status_code == 200
    assert stats.json()["products"] >= 1

    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={
            "name": "Тестовый товар",
            "description": "Создан автоматическим тестом",
            "price": "999.00",
            "stock": 5,
            "category": "Тест",
            "emoji": "🧪",
            "is_active": True,
        },
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    updated = client.patch(
        f"/api/admin/products/{product_id}",
        headers=admin_headers,
        json={"stock": 7},
    )
    assert updated.status_code == 200
    assert updated.json()["stock"] == 7

    deleted = client.delete(f"/api/admin/products/{product_id}", headers=admin_headers)
    assert deleted.status_code == 204


def test_customer_cannot_use_admin_api(client):
    email = f"customer-{uuid4().hex}@example.com"
    response = client.post(
        "/api/auth/register",
        json={"name": "Покупатель", "email": email, "password": "StrongPass123!"},
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/api/admin/stats", headers=headers).status_code == 403

