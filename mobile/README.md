# Lunora Mobile

The Flutter SDK was not available when this repository was generated, so platform wrappers are
created once on a development machine:

```bash
cd mobile
flutter create --platforms=android,ios .
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8080
```

For a physical phone, replace `10.0.2.2` with the computer's LAN address and make the API reachable
only on a trusted network or through HTTPS.

