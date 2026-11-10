# AwanMarket

Кроссплатформенный магазин обычных продуктов. Один backend обслуживает адаптивную
NiceGUI-витрину, мобильное приложение Flutter и desktop-клиент PyQt6.

## Что уже есть

- регистрация, вход, JWT и роли `customer` / `admin`;
- каталог, поиск API, остатки, корзина и атомарное оформление заказа;
- история заказов и смена их статусов администратором;
- CRUD товаров, пользователи, заказы и статистика в API/веб-админке;
- адаптивный NiceGUI-интерфейс для телефона и компьютера;
- отдельные Flutter и PyQt6 клиенты;
- PostgreSQL, Docker, healthcheck, Caddy + HTTPS и CI;
- Swagger (`/docs`) и готовая Postman-коллекция.

## Структура

```text
backend/app/       FastAPI, модели, API, NiceGUI и бизнес-логика
desktop/           PyQt6 desktop-клиент
mobile/            Flutter mobile-клиент
tests/             API-тесты
postman/           коллекция и локальное окружение
deploy/            Caddy и инструкция production-развёртывания
```

Инструкция для покупателей и администратора: [GITHUB_GUIDE.md](GITHUB_GUIDE.md).

## Быстрый запуск

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Откройте:

- магазин: <http://localhost:8080>
- Swagger: <http://localhost:8080/docs>
- healthcheck: <http://localhost:8080/health>

Тестовый администратор задаётся через `ADMIN_EMAIL` и `ADMIN_PASSWORD` в `.env`. Перед любым
публичным развёртыванием обязательно замените пароль, `SECRET_KEY` и пароль PostgreSQL.

## Локальная разработка без Docker

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
$env:DATABASE_URL = "sqlite+aiosqlite:///./awanmarket.db"
.venv\Scripts\uvicorn backend.app.main:app --reload --port 8080
```

## Проверки

```powershell
ruff check backend tests desktop
pytest -q
postman collection run postman/AwanMarket.postman_collection.json `
  -e postman/AwanMarket.postman_environment.json
```

## Клиенты

Инструкции находятся в [mobile/README.md](mobile/README.md) и [desktop/README.md](desktop/README.md).
Android Emulator обращается к backend через `10.0.2.2`; desktop — через `127.0.0.1`.

## API

| Область | Маршруты |
|---|---|
| Авторизация | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Каталог | `GET /api/products`, `GET /api/products/{id}` |
| Заказы | `POST /api/orders`, `GET /api/orders` |
| Админка | `/api/admin/stats`, `/users`, `/products`, `/orders` |

Подробная схема всегда доступна в OpenAPI/Swagger по `/docs`.

