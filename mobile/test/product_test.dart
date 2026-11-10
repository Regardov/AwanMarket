import 'package:flutter_test/flutter_test.dart';
import 'package:awanmarket_mobile/main.dart';

void main() {
  test('product parses API payload', () {
    final product = Product.fromJson({
      'id': 1,
      'name': 'Молоко',
      'description': 'Свежее молоко',
      'emoji': '🥛',
      'category': 'Молочное',
      'price': '109.00',
      'stock': 5,
    });

    expect(product.name, 'Молоко');
    expect(product.price, 109);
  });
}

