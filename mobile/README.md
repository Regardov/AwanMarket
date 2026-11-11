# AwanMarket Mobile

Flutter-приложение покупателя: поиск по названию и описанию, категории, сортировка,
карточки с описаниями, остатки, корзина, вход/регистрация/выход, оформление и история
заказов со статусами. Телефон использует нижнюю навигацию, широкий экран — боковую.
Корзина и адрес сохраняются локально; JWT — в Android Keystore / iOS Keychain через
`flutter_secure_storage`. Пароль не сохраняется. При истечении JWT нужно войти снова.

## Запуск

Нужен Flutter **3.47.9** (версия также закреплена в CI). Проекты Android, iOS и web
уже включены в репозиторий; повторный `flutter create` не требуется.

Сначала запустите backend из корня репозитория, затем:

```bash
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8080
```

`10.0.2.2` — компьютер разработчика из Android Emulator. Для iOS Simulator:

```bash
flutter run --dart-define=API_BASE_URL=http://localhost:8080
```

Для физического телефона укажите доступный ему HTTPS-адрес API. Для локальной
отладки Android допускает HTTP в debug/profile; release использует HTTPS. На iOS
разрешены локальные подключения; произвольный HTTP-сервер по IP может требовать
отдельной настройки ATS. Секреты backend в мобильную сборку не передаются.

## Сборка и проверки

```bash
flutter analyze
flutter test
flutter build apk --debug
flutter build apk --release --dart-define=API_BASE_URL=https://your-api.example.com
# Только macOS с Xcode:
flutter build ios --release --no-codesign --dart-define=API_BASE_URL=https://your-api.example.com
```

APK находится в `build/app/outputs/flutter-apk/`. Текущая Android release-конфигурация
подписывает APK отладочным ключом для тестового распространения. Перед публикацией
в магазине настройте собственную подпись. Для iOS нужны Apple Team, provisioning и
подпись в Xcode; `--no-codesign` проверяет сборку, но не создаёт устанавливаемый IPA.

Для браузерной проверки Flutter-интерфейса:

```bash
flutter run -d chrome --web-port=8090 --dart-define=API_BASE_URL=http://localhost:8080
```

Добавьте `http://localhost:8090` в `CORS_ORIGINS` backend. В web защищённое хранилище
требует HTTPS или localhost; используется обычная JavaScript-сборка, не Wasm.
Noto Color Emoji включён локально, лицензия находится в `assets/fonts/NOTO-LICENSE.txt`.

## Поведение корзины

- Количество ограничено остатком и лимитом API: 99 единиц / 50 разных товаров.
- Обновление каталога удаляет недоступные товары и корректирует количества с уведомлением.
- Во время оформления редактирование и повторная отправка заблокированы.
- Корзина очищается только после подтверждённого успешного ответа API.
- При сетевом таймауте после отправки проверьте историю заказов перед повтором:
  API пока не поддерживает ключи идемпотентности.
