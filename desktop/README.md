# AwanMarket Desktop

Приложение PyQt6 для покупателя: каталог с поиском, категориями и сортировкой,
адаптивная сетка карточек, остатки, корзина с изменением количества, регистрация,
вход/выход, оформление и история заказов. HTTP-запросы выполняются в рабочем пуле,
чтобы окно оставалось отзывчивым. Ошибку загрузки можно повторить кнопкой «Обновить».

## Запуск

Запустите backend из корня репозитория. Python 3.11+:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r desktop\requirements.txt
$env:AWANMARKET_API_URL = "http://127.0.0.1:8080"
.venv\Scripts\python desktop\main.py
```

Linux/macOS:

```bash
python -m venv .venv
.venv/bin/pip install -r desktop/requirements.txt
AWANMARKET_API_URL=http://127.0.0.1:8080 .venv/bin/python -m desktop.main
```

Для удалённого backend укажите его HTTPS-адрес в `AWANMARKET_API_URL` до запуска.
Корзина и адрес сохраняются через `QSettings` в профиле ОС. Токен живёт только до
выхода или закрытия приложения; пароль и JWT на диск не записываются. После
перезапуска войдите повторно для просмотра заказов и оформления.

## Проверки и упаковка

```bash
pip install -r desktop/requirements-dev.txt
# На машине без дисплея:
QT_QPA_PLATFORM=offscreen python -m pytest -q desktop/tests
# На Windows: python -m pytest -q desktop/tests
pip install pyinstaller
pyinstaller --onefile --windowed --name AwanMarket desktop/main.py
```

Windows EXE собирается на Windows, Linux-бинарник — на Linux; PyInstaller не
выполняет перекрёстную сборку. Готовый файл находится в `dist/`. Ручной workflow
**Build AwanMarket clients** собирает Windows EXE и Android APK в GitHub Actions.
Для production APK передайте HTTPS API URL; для desktop задайте переменную окружения.

Количество ограничивается остатком и лимитами API. После покупки каталог обновляется.
При сетевом таймауте после отправки сначала обновите «Мои заказы»: сервер может успеть
создать заказ, даже если ответ не дошёл. API пока не поддерживает идемпотентность.
