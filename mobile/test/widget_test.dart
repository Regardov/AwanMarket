import 'package:awanmarket_mobile/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'store_test.dart' show model, productJson;
import 'dart:convert';

void main() {
  for (final width in [320.0, 390.0, 768.0, 1280.0]) {
    testWidgets('catalogue and cart work at width $width', (tester) async {
      tester.view.physicalSize = Size(width, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final store = await model((_) async => http.Response(
          jsonEncode([
            productJson(),
            productJson(
                id: 2,
                name: 'Длинное название товара в несколько строк',
                stock: 0),
          ]),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'}));
      await tester.pumpWidget(AwanMarketApp(store: store));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.scrollUntilVisible(find.text('В корзину').first, 200,
          scrollable: find
              .descendant(
                  of: find.byType(CatalogPage),
                  matching: find.byType(Scrollable))
              .first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('В корзину').first);
      await tester.pumpAndSettle();
      expect(store.cart, {1: 1});
      await tester.tap(find.text('Корзина').last);
      await tester.pumpAndSettle();
      expect(find.text('Итого: 109,25 ₽'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.byTooltip('Удалить').last);
      await tester.pumpAndSettle();
      expect(find.text('Корзина пока пуста'), findsOneWidget);
      expect(store.count, 0);
    });
  }

  testWidgets('catalogue supports larger system text', (tester) async {
    tester.view.physicalSize = const Size(390, 900);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 1.5;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    final store = await model((_) async => http.Response(
        jsonEncode([productJson()]), 200,
        headers: {'content-type': 'application/json; charset=utf-8'}));
    await tester.pumpWidget(AwanMarketApp(store: store));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('В корзину'), 200,
        scrollable: find
            .descendant(
                of: find.byType(CatalogPage), matching: find.byType(Scrollable))
            .first);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('login form validates locally and fits above keyboard',
      (tester) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final store = await model((_) async => http.Response('[]', 200));
    await tester.pumpWidget(AwanMarketApp(store: store));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Аккаунт').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Войти / Зарегистрироваться'));
    await tester.pumpAndSettle();
    tester.view.viewInsets = const FakeViewPadding(bottom: 250);
    addTearDown(tester.view.resetViewInsets);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Войти').last);
    await tester.pumpAndSettle();
    expect(find.text('Укажите корректный email'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
