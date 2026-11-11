import 'dart:async';
import 'dart:convert';

import 'package:awanmarket_mobile/store.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

class MemorySession implements SessionStorage {
  String? token;
  @override
  Future<String?> read() async => token;
  @override
  Future<void> write(String? value) async {
    token = value;
  }
}

Map<String, dynamic> productJson(
        {int id = 1,
        int stock = 2,
        String name = 'Молоко',
        String price = '109.25'}) =>
    {
      'id': id,
      'name': name,
      'description': 'Свежее молоко',
      'emoji': '🥛',
      'category': 'Молочное',
      'price': price,
      'stock': stock,
    };

Future<StoreModel> model(Future<http.Response> Function(http.Request) handler,
    {Map<String, Object> saved = const {}}) async {
  SharedPreferences.setMockInitialValues(saved);
  final store = StoreModel(
      api: ApiClient(client: MockClient(handler)),
      preferences: await SharedPreferences.getInstance(),
      session: MemorySession());
  await store.initialize();
  return store;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
      'restored cart drops missing products, clamps stock and persists changes',
      () async {
    final store = await model(
        (_) async => http.Response(jsonEncode([productJson()]), 200,
            headers: {'content-type': 'application/json; charset=utf-8'}),
        saved: {'cart': '{"1":8,"2":1}'});
    expect(store.error, isNull);
    expect(store.cart, {1: 2});
    store.quantity(store.products.first, 3);
    expect(store.cart, {1: 2});
    expect(store.total, 218.50);
    store.quantity(store.products.first, 0);
    await Future<void>.delayed(Duration.zero);
    expect(store.cart, isEmpty);
    expect(jsonDecode(store.preferences.getString('cart')!), isEmpty);
  });

  test(
      'checkout sends snapshot once, retains cart on failure, clears after success',
      () async {
    final pending = Completer<http.Response>();
    var requests = 0;
    var succeed = false;
    final store = await model((request) async {
      if (request.method == 'GET') {
        return http.Response(jsonEncode([productJson()]), 200,
            headers: {'content-type': 'application/json; charset=utf-8'});
      }
      requests++;
      expect(request.headers['Authorization'], 'Bearer token');
      expect(jsonDecode(request.body)['items'], [
        {'product_id': 1, 'quantity': 1}
      ]);
      return succeed
          ? http.Response('{"id":7,"total":"109.25"}', 201)
          : pending.future;
    });
    store.api.token = 'token';
    store.quantity(store.products.first, 1);
    final first = store.checkout('Москва, улица Лесная, 1');
    final failed = expectLater(first, throwsA(isA<ApiException>()));
    await expectLater(store.checkout('Москва, улица Лесная, 1'),
        throwsA(isA<ApiException>()));
    store.quantity(store.products.first, 0);
    expect(store.cart, {1: 1});
    pending.complete(http.Response('{"detail":"Not enough stock"}', 409));
    await failed;
    expect(requests, 1);
    expect(store.cart, {1: 1});
    succeed = true;
    await store.checkout('Москва, улица Лесная, 1');
    expect(store.cart, isEmpty);
    expect(store.checkingOut, isFalse);
  });

  test('expired session is removed after protected API error', () async {
    final store = await model((request) async =>
        request.url.path == '/api/products'
            ? http.Response('[]', 200)
            : http.Response('{"detail":"expired"}', 401));
    store.api.token = 'expired';
    await store.session.write('expired');
    await expectLater(store.orders(), throwsA(isA<ApiException>()));
    expect(store.signedIn, isFalse);
    expect(await store.session.read(), isNull);
  });

  test('failed refresh can be retried', () async {
    var fail = true;
    final store = await model((_) async =>
        fail ? http.Response('gateway', 502) : http.Response('[]', 200));
    expect(store.error, isNotNull);
    fail = false;
    await store.refresh();
    expect(store.error, isNull);
    expect(store.ready, isTrue);
  });
}
