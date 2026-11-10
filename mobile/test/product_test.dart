import 'package:flutter_test/flutter_test.dart';
import 'package:lunora_mobile/main.dart';

void main() {
  test('product parses API payload', () {
    final product = Product.fromJson({
      'id': 1,
      'name': 'Лампа',
      'description': 'Мягкий свет',
      'emoji': '💡',
      'category': 'Свет',
      'price': '1290.00',
      'stock': 5,
    });

    expect(product.name, 'Лампа');
    expect(product.price, 1290);
  });
}

