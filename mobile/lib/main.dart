import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const apiBase = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8080');

void main() => runApp(const AwanMarketApp());

class Product {
  Product.fromJson(Map<String, dynamic> json)
      : id = json['id'] as int,
        name = json['name'] as String,
        description = json['description'] as String,
        emoji = json['emoji'] as String,
        category = json['category'] as String,
        price = double.parse(json['price'].toString()),
        stock = json['stock'] as int;

  final int id;
  final String name, description, emoji, category;
  final double price;
  final int stock;
}

class ApiClient {
  String? token;

  Future<List<Product>> products() async {
    final response = await http.get(Uri.parse('$apiBase/api/products'));
    _check(response);
    return (jsonDecode(response.body) as List)
        .map((item) => Product.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<void> authenticate(String path, String name, String email, String password) async {
    final body = <String, String>{'email': email, 'password': password};
    if (path == 'register') body['name'] = name;
    final response = await http.post(
      Uri.parse('$apiBase/api/auth/$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _check(response);
    token = (jsonDecode(response.body) as Map<String, dynamic>)['access_token'] as String;
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString('token', token!);
  }

  Future<void> restore() async {
    token = (await SharedPreferences.getInstance()).getString('token');
  }

  Future<void> order(Map<int, int> cart, String address) async {
    if (token == null) throw Exception('Сначала войдите в аккаунт');
    final response = await http.post(
      Uri.parse('$apiBase/api/orders'),
      headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
      body: jsonEncode({
        'shipping_address': address,
        'items': cart.entries.map((e) => {'product_id': e.key, 'quantity': e.value}).toList(),
      }),
    );
    _check(response);
  }

  void _check(http.Response response) {
    if (response.statusCode >= 400) {
      String detail = 'Ошибка сервера: ${response.statusCode}';
      try {
        detail = (jsonDecode(response.body) as Map<String, dynamic>)['detail'].toString();
      } catch (_) {
        // Preserve the generic status message when a proxy returns non-JSON.
      }
      throw Exception(detail);
    }
  }
}

class AwanMarketApp extends StatefulWidget {
  const AwanMarketApp({super.key});
  @override
  State<AwanMarketApp> createState() => _AwanMarketAppState();
}

class _AwanMarketAppState extends State<AwanMarketApp> {
  final api = ApiClient();
  final cart = <int, int>{};

  @override
  void initState() {
    super.initState();
    api.restore().then((_) => setState(() {}));
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'AwanMarket',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff637f6d)),
          scaffoldBackgroundColor: const Color(0xfff7f3eb),
          useMaterial3: true,
          cardTheme: const CardThemeData(elevation: 0, margin: EdgeInsets.zero),
        ),
        home: StorePage(
          api: api,
          cart: cart,
          changed: () => setState(() {}),
        ),
      );
}

class StorePage extends StatefulWidget {
  const StorePage({required this.api, required this.cart, required this.changed, super.key});
  final ApiClient api;
  final Map<int, int> cart;
  final VoidCallback changed;

  @override
  State<StorePage> createState() => _StorePageState();
}

class _StorePageState extends State<StorePage> {
  late final Future<List<Product>> future = widget.api.products();

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          title: const Text('AWANMARKET', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 2)),
          actions: [
            IconButton(
              tooltip: widget.api.token == null ? 'Войти' : 'Аккаунт',
              onPressed: () => showDialog<void>(
                context: context,
                builder: (_) => AuthDialog(api: widget.api, changed: widget.changed),
              ),
              icon: const Icon(Icons.person_outline),
            ),
            Badge(
              label: Text('${widget.cart.values.fold(0, (a, b) => a + b)}'),
              isLabelVisible: widget.cart.isNotEmpty,
              child: IconButton(
                onPressed: () async {
                  final products = await future;
                  if (!context.mounted) return;
                  await Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => CartPage(
                        api: widget.api,
                        cart: widget.cart,
                        products: products,
                        changed: widget.changed,
                      ),
                    ),
                  );
                  setState(() {});
                },
                icon: const Icon(Icons.shopping_bag_outlined),
              ),
            ),
          ],
        ),
        body: FutureBuilder<List<Product>>(
          future: future,
          builder: (context, snapshot) {
            if (snapshot.hasError) return Center(child: Text('${snapshot.error}'));
            if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
            return CustomScrollView(slivers: [
              SliverToBoxAdapter(
                child: Container(
                  margin: const EdgeInsets.all(16),
                  padding: const EdgeInsets.all(28),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xff20372d), Color(0xff789078)]),
                    borderRadius: BorderRadius.circular(28),
                  ),
                  child: const Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('СВЕЖЕЕ КАЖДЫЙ ДЕНЬ', style: TextStyle(color: Color(0xffffdf9e), letterSpacing: 2)),
                    SizedBox(height: 12),
                    Text('Обычные продукты\nпо честным ценам', style: TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.w900)),
                    SizedBox(height: 8),
                    Text('Молоко, хлеб, овощи и всё необходимое.', style: TextStyle(color: Colors.white70)),
                  ]),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                sliver: SliverGrid.builder(
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                    maxCrossAxisExtent: 430,
                    mainAxisExtent: 330,
                    crossAxisSpacing: 14,
                    mainAxisSpacing: 14,
                  ),
                  itemCount: snapshot.data!.length,
                  itemBuilder: (context, index) {
                    final product = snapshot.data![index];
                    return Card(
                      clipBehavior: Clip.antiAlias,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Expanded(child: Container(
                            width: double.infinity,
                            decoration: BoxDecoration(color: const Color(0xffdfeadf), borderRadius: BorderRadius.circular(18)),
                            alignment: Alignment.center,
                            child: Text(product.emoji, style: const TextStyle(fontSize: 62)),
                          )),
                          const SizedBox(height: 12),
                          Text(product.category.toUpperCase(), style: const TextStyle(fontSize: 11, color: Color(0xff637f6d), letterSpacing: 1.5)),
                          Text(product.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                          Text('${product.price.toStringAsFixed(0)} ₽', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
                          Align(
                            alignment: Alignment.bottomRight,
                            child: IconButton.filled(
                              onPressed: () {
                                widget.cart.update(product.id, (value) => value + 1, ifAbsent: () => 1);
                                widget.changed();
                                setState(() {});
                              },
                              icon: const Icon(Icons.add_shopping_cart),
                            ),
                          ),
                        ]),
                      ),
                    );
                  },
                ),
              ),
            ]);
          },
        ),
      );
}

class AuthDialog extends StatefulWidget {
  const AuthDialog({required this.api, required this.changed, super.key});
  final ApiClient api;
  final VoidCallback changed;
  @override
  State<AuthDialog> createState() => _AuthDialogState();
}

class _AuthDialogState extends State<AuthDialog> {
  final name = TextEditingController(), email = TextEditingController(), password = TextEditingController();
  bool register = false, busy = false;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(register ? 'Регистрация' : 'Вход'),
        content: SizedBox(width: 360, child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (register) TextField(controller: name, decoration: const InputDecoration(labelText: 'Имя')),
          TextField(controller: email, decoration: const InputDecoration(labelText: 'Email')),
          TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Пароль')),
          TextButton(onPressed: () => setState(() => register = !register), child: Text(register ? 'Уже есть аккаунт' : 'Создать аккаунт')),
        ])),
        actions: [FilledButton(
          onPressed: busy ? null : () async {
            setState(() => busy = true);
            try {
              await widget.api.authenticate(register ? 'register' : 'login', name.text, email.text, password.text);
              widget.changed();
              if (context.mounted) Navigator.pop(context);
            } catch (error) {
              if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
            } finally {
              if (mounted) setState(() => busy = false);
            }
          },
          child: Text(busy ? '...' : register ? 'Создать' : 'Войти'),
        )],
      );
}

class CartPage extends StatefulWidget {
  const CartPage({required this.api, required this.cart, required this.products, required this.changed, super.key});
  final ApiClient api;
  final Map<int, int> cart;
  final List<Product> products;
  final VoidCallback changed;
  @override
  State<CartPage> createState() => _CartPageState();
}

class _CartPageState extends State<CartPage> {
  final address = TextEditingController();
  @override
  Widget build(BuildContext context) {
    final selected = widget.products.where((p) => widget.cart.containsKey(p.id)).toList();
    final total = selected.fold<double>(0, (sum, p) => sum + p.price * widget.cart[p.id]!);
    return Scaffold(
      appBar: AppBar(title: const Text('Корзина')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (selected.isEmpty) const Padding(padding: EdgeInsets.all(48), child: Center(child: Text('Корзина пуста'))),
        for (final product in selected)
          Card(child: ListTile(
            leading: Text(product.emoji, style: const TextStyle(fontSize: 32)),
            title: Text(product.name),
            subtitle: Text('${widget.cart[product.id]} × ${product.price.toStringAsFixed(0)} ₽'),
            trailing: IconButton(onPressed: () => setState(() => widget.cart.remove(product.id)), icon: const Icon(Icons.delete_outline)),
          )),
        const SizedBox(height: 18),
        Text('Итого: ${total.toStringAsFixed(0)} ₽', textAlign: TextAlign.end, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900)),
        TextField(controller: address, decoration: const InputDecoration(labelText: 'Адрес доставки')),
        const SizedBox(height: 16),
        FilledButton(onPressed: selected.isEmpty ? null : () async {
          try {
            await widget.api.order(widget.cart, address.text);
            widget.cart.clear(); widget.changed();
            if (context.mounted) Navigator.pop(context);
          } catch (error) {
            if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
          }
        }, child: const Text('Оформить заказ')),
      ]),
    );
  }
}

