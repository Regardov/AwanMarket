import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const apiBase = String.fromEnvironment('API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8080');

String money(num value) => '${value.toStringAsFixed(2).replaceAll('.', ',')} ₽';
const orderStatuses = {
  'new': 'Принят',
  'paid': 'Оплачен',
  'shipped': 'В пути',
  'completed': 'Доставлен',
  'cancelled': 'Отменён'
};

class Product {
  Product.fromJson(Map<String, dynamic> json)
      : id = json['id'] as int,
        name = json['name'] as String,
        description = json['description'] as String,
        emoji = json['emoji'] as String,
        category = json['category'] as String,
        cents = (double.parse(json['price'].toString()) * 100).round(),
        stock = json['stock'] as int;
  final int id, cents, stock;
  final String name, description, emoji, category;
  double get price => cents / 100;
  int get limit => stock.clamp(0, 99);
}

class ApiException implements Exception {
  ApiException(this.message, [this.status = 0]);
  final String message;
  final int status;
  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client, this.baseUrl = apiBase})
      : client = client ?? http.Client();
  final http.Client client;
  final String baseUrl;
  String? token;

  Future<dynamic> request(String method, String path,
      [Map<String, dynamic>? body]) async {
    final request = http.Request(
        method, Uri.parse('${baseUrl.replaceFirst(RegExp(r'/+$'), '')}$path'));
    request.headers['Content-Type'] = 'application/json';
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    if (body != null) request.body = jsonEncode(body);
    late http.Response response;
    try {
      response = await http.Response.fromStream(await client.send(request))
          .timeout(const Duration(seconds: 15));
    } on TimeoutException {
      throw ApiException('Сервер не ответил вовремя. Повторите попытку.');
    } on http.ClientException {
      throw ApiException('Нет связи с сервером. Проверьте подключение.');
    }
    dynamic data;
    try {
      data = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      throw ApiException(
          'Некорректный ответ сервера: HTTP ${response.statusCode}',
          response.statusCode);
    }
    if (response.statusCode >= 400) {
      if (response.statusCode == 401) {
        throw ApiException(
            'Неверный email или пароль, либо срок входа истёк. Войдите снова.',
            401);
      }
      final detail = data is Map ? data['detail'] : null;
      final message = detail is List
          ? detail.map((e) => e is Map ? e['msg'] : e).join('\n')
          : detail?.toString();
      throw ApiException(message ?? 'Ошибка сервера: ${response.statusCode}',
          response.statusCode);
    }
    return data;
  }

  Future<List<Product>> products() async =>
      ((await request('GET', '/api/products')) as List)
          .map((e) => Product.fromJson(e as Map<String, dynamic>))
          .toList();
  Future<Map<String, dynamic>> authenticate(
          bool register, String name, String email, String password) async =>
      await request('POST', '/api/auth/${register ? 'register' : 'login'}', {
        'email': email.trim(),
        'password': password,
        if (register) 'name': name.trim(),
      }) as Map<String, dynamic>;
  Future<Map<String, dynamic>> me() async =>
      await request('GET', '/api/auth/me') as Map<String, dynamic>;
  Future<List<dynamic>> orders() async =>
      await request('GET', '/api/orders') as List<dynamic>;
  Future<Map<String, dynamic>> order(
          Map<int, int> cart, String address) async =>
      await request('POST', '/api/orders', {
        'shipping_address': address.trim(),
        'items': cart.entries
            .map((e) => {'product_id': e.key, 'quantity': e.value})
            .toList(),
      }) as Map<String, dynamic>;
}

abstract class SessionStorage {
  Future<String?> read();
  Future<void> write(String? token);
}

class SecureSessionStorage implements SessionStorage {
  final storage = const FlutterSecureStorage();
  @override
  Future<String?> read() => storage.read(key: 'awanmarket_token');
  @override
  Future<void> write(String? token) => token == null
      ? storage.delete(key: 'awanmarket_token')
      : storage.write(key: 'awanmarket_token', value: token);
}

class StoreModel extends ChangeNotifier {
  StoreModel(
      {required this.api, required this.preferences, required this.session});
  final ApiClient api;
  final SharedPreferences preferences;
  final SessionStorage session;
  final cart = <int, int>{};
  List<Product> products = [];
  Map<String, dynamic>? user;
  bool loading = false, ready = false, checkingOut = false, restoring = true;
  String? error, notice;
  String get address => preferences.getString('address') ?? '';
  bool get signedIn => api.token != null;
  int get count => cart.values.fold(0, (sum, value) => sum + value);
  double get total =>
      products.fold<int>(0, (sum, p) => sum + p.cents * (cart[p.id] ?? 0)) /
      100;
  Future<void> _writes = Future.value();

  void clearNotice() {
    notice = null;
    notifyListeners();
  }

  Future<void> initialize() async {
    try {
      final saved = jsonDecode(preferences.getString('cart') ?? '{}') as Map;
      for (final entry in saved.entries) {
        final id = int.tryParse(entry.key.toString());
        if (id != null &&
            entry.value is int &&
            entry.value > 0 &&
            entry.value <= 99 &&
            cart.length < 50) {
          cart[id] = entry.value as int;
        }
      }
    } catch (_) {
      cart.clear();
    }
    await Future.wait([refresh(), _restore()]);
  }

  Future<void> _restore() async {
    try {
      api.token = await session.read();
      if (signedIn) user = await api.me();
    } catch (e) {
      if (e is ApiException && e.status == 401) {
        await logout();
      } else {
        notice =
            'Не удалось восстановить аккаунт. ${e is ApiException ? e.message : 'Войдите снова.'}';
      }
    } finally {
      restoring = false;
      notifyListeners();
    }
  }

  Future<void> refresh() async {
    if (loading || checkingOut) return;
    loading = true;
    error = null;
    notifyListeners();
    try {
      products = await api.products();
      ready = true;
      final before = jsonEncode(cart.map((k, v) => MapEntry('$k', v)));
      final byId = {for (final p in products) p.id: p};
      for (final id in cart.keys.toList()) {
        final limit = byId[id]?.limit ?? 0;
        if (limit == 0) {
          cart.remove(id);
        } else {
          cart[id] = cart[id]!.clamp(1, limit);
        }
      }
      if (jsonEncode(cart.map((k, v) => MapEntry('$k', v))) != before) {
        notice = 'Корзина обновлена с учётом доступных товаров и остатков.';
        persistCart();
      }
    } catch (e) {
      error = e.toString();
    }
    loading = false;
    notifyListeners();
  }

  void persistCart() {
    final value = jsonEncode(cart.map((k, v) => MapEntry('$k', v)));
    _writes = _writes.then((_) async {
      await preferences.setString('cart', value);
    }).catchError((Object _) {
      notice = 'Не удалось сохранить корзину на устройстве.';
      notifyListeners();
    });
  }

  void quantity(Product product, int value) {
    if (checkingOut || !ready) return;
    if (value > product.limit) {
      notice = 'В корзине уже всё доступное количество.';
      notifyListeners();
      return;
    }
    if (value > 0 && !cart.containsKey(product.id) && cart.length >= 50) {
      notice = 'В одном заказе может быть до 50 разных товаров.';
      notifyListeners();
      return;
    }
    if (value <= 0) {
      cart.remove(product.id);
    } else {
      cart[product.id] = value;
    }
    persistCart();
    notifyListeners();
  }

  Future<void> authenticate(
      bool register, String name, String email, String password) async {
    final data = await api.authenticate(register, name, email, password);
    api.token = data['access_token'] as String;
    user = data['user'] as Map<String, dynamic>;
    try {
      await session.write(api.token);
    } catch (_) {
      notice =
          'Вход выполнен. На этом устройстве потребуется повторный вход после закрытия.';
    }
    notifyListeners();
  }

  Future<void> logout() async {
    api.token = null;
    user = null;
    try {
      await session.write(null);
    } catch (_) {
      notice =
          'Не удалось очистить сохранённый вход. Повторите выход после восстановления хранилища.';
    }
    notifyListeners();
  }

  Future<void> authError(Object e) async {
    if (e is ApiException && e.status == 401) {
      await logout();
      notice = 'Срок входа истёк. Войдите снова.';
      notifyListeners();
    }
  }

  Future<List<dynamic>> orders() async {
    try {
      return await api.orders();
    } catch (e) {
      await authError(e);
      rethrow;
    }
  }

  Future<Map<String, dynamic>> checkout(String address) async {
    if (checkingOut) throw ApiException('Заказ уже оформляется.');
    if (!signedIn) throw ApiException('Сначала войдите в аккаунт.');
    if (cart.isEmpty) throw ApiException('Корзина пуста.');
    if (address.trim().length < 8) {
      throw ApiException('Укажите полный адрес доставки (от 8 символов).');
    }
    checkingOut = true;
    notifyListeners();
    try {
      final order = await api.order(Map.of(cart), address);
      cart.clear();
      persistCart();
      notice =
          'Заказ №${order['id']} принят · ${money(double.parse(order['total'].toString()))}';
      return order;
    } catch (e) {
      await authError(e);
      rethrow;
    } finally {
      checkingOut = false;
      notifyListeners();
    }
  }
}
