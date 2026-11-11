import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'store.dart';
export 'store.dart' show Product;

const green = Color(0xff294438);
const cream = Color(0xfff7f3eb);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final store = StoreModel(
      api: ApiClient(),
      preferences: await SharedPreferences.getInstance(),
      session: SecureSessionStorage());
  runApp(AwanMarketApp(store: store));
  unawaited(store.initialize());
}

class AwanMarketApp extends StatelessWidget {
  const AwanMarketApp({required this.store, super.key});
  final StoreModel store;
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'AwanMarket',
        debugShowCheckedModeBanner: false,
        locale: const Locale('ru'),
        supportedLocales: const [Locale('ru')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        theme: ThemeData(
          useMaterial3: true,
          fontFamilyFallback: const ['NotoEmoji'],
          colorScheme: ColorScheme.fromSeed(seedColor: green),
          scaffoldBackgroundColor: cream,
          appBarTheme: const AppBarTheme(
              backgroundColor: cream, scrolledUnderElevation: 0),
          cardTheme: CardThemeData(
              color: Colors.white,
              elevation: 0,
              margin: EdgeInsets.zero,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20))),
          inputDecorationTheme: InputDecorationTheme(
              filled: true,
              fillColor: Colors.white,
              border:
                  OutlineInputBorder(borderRadius: BorderRadius.circular(14))),
        ),
        home: StoreHome(store: store),
      );
}

Future<bool> signIn(BuildContext context, StoreModel store) async =>
    await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (_) => AuthDialog(store: store)) ??
    false;

class StoreHome extends StatefulWidget {
  const StoreHome({required this.store, super.key});
  final StoreModel store;
  @override
  State<StoreHome> createState() => _StoreHomeState();
}

class _StoreHomeState extends State<StoreHome> {
  int page = 0;
  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: widget.store,
        builder: (context, _) {
          final store = widget.store;
          final wide = MediaQuery.sizeOf(context).width >= 900;
          final destinations = [
            const NavigationDestination(
                icon: Icon(Icons.storefront_outlined),
                selectedIcon: Icon(Icons.storefront),
                label: 'Каталог'),
            NavigationDestination(
                icon: Badge(
                    isLabelVisible: store.count > 0,
                    label: Text('${store.count}'),
                    child: const Icon(Icons.shopping_bag_outlined)),
                label: 'Корзина'),
            const NavigationDestination(
                icon: Icon(Icons.receipt_long_outlined), label: 'Заказы'),
            const NavigationDestination(
                icon: Icon(Icons.person_outline), label: 'Аккаунт'),
          ];
          final content = IndexedStack(index: page, children: [
            CatalogPage(store: store),
            CartPage(
                store: store,
                onCatalog: () => setState(() => page = 0),
                onOrders: () => setState(() => page = 2)),
            OrdersPage(
                key: ValueKey(store.api.token),
                store: store,
                active: page == 2),
            ProfilePage(store: store),
          ]);
          return Scaffold(
            appBar: AppBar(
                title: const Text('AWANMARKET',
                    style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2)),
                actions: [
                  IconButton(
                      tooltip: 'Обновить каталог',
                      onPressed: store.loading || store.checkingOut
                          ? null
                          : store.refresh,
                      icon: const Icon(Icons.refresh)),
                  const SizedBox(width: 8)
                ]),
            body: SafeArea(
                child: Column(children: [
              if (store.notice != null)
                Material(
                    color: const Color(0xffdfeadf),
                    child: Padding(
                        padding: const EdgeInsets.only(left: 16),
                        child: Row(children: [
                          Expanded(child: Text(store.notice!)),
                          IconButton(
                              tooltip: 'Закрыть уведомление',
                              onPressed: store.clearNotice,
                              icon: const Icon(Icons.close, size: 18)),
                        ]))),
              Expanded(
                  child: Row(children: [
                if (wide)
                  NavigationRail(
                      selectedIndex: page,
                      labelType: NavigationRailLabelType.all,
                      onDestinationSelected: store.checkingOut
                          ? null
                          : (value) => setState(() => page = value),
                      destinations: destinations
                          .map((d) => NavigationRailDestination(
                              icon: d.icon, label: Text(d.label)))
                          .toList()),
                Expanded(
                    child: Center(
                        child: ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 1300),
                            child: content))),
              ])),
            ])),
            bottomNavigationBar: wide
                ? null
                : NavigationBar(
                    selectedIndex: page,
                    onDestinationSelected: store.checkingOut
                        ? null
                        : (value) => setState(() => page = value),
                    destinations: destinations),
          );
        },
      );
}

class CatalogPage extends StatefulWidget {
  const CatalogPage({required this.store, super.key});
  final StoreModel store;
  @override
  State<CatalogPage> createState() => _CatalogPageState();
}

class _CatalogPageState extends State<CatalogPage> {
  String query = '', category = 'Все', sort = 'По умолчанию';
  @override
  Widget build(BuildContext context) {
    final store = widget.store;
    if (!store.ready && store.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (!store.ready && store.error != null) {
      return EmptyState(
          icon: Icons.wifi_off,
          title: store.error!,
          action: 'Повторить',
          onPressed: store.refresh);
    }
    final categories = [
      'Все',
      ...({...store.products.map((p) => p.category)}.toList()..sort())
    ];
    final selectedCategory = categories.contains(category) ? category : 'Все';
    final visible = store.products
        .where((p) =>
            (selectedCategory == 'Все' || p.category == selectedCategory) &&
            '${p.name} ${p.description}'
                .toLowerCase()
                .contains(query.trim().toLowerCase()))
        .toList();
    if (sort == 'Сначала дешевле') {
      visible.sort((a, b) => a.cents.compareTo(b.cents));
    }
    if (sort == 'Сначала дороже') {
      visible.sort((a, b) => b.cents.compareTo(a.cents));
    }
    if (sort == 'По названию') visible.sort((a, b) => a.name.compareTo(b.name));
    return LayoutBuilder(builder: (context, constraints) {
      final columns = (constraints.maxWidth / 190).floor().clamp(1, 4);
      return RefreshIndicator(
          onRefresh: store.refresh,
          child: CustomScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              slivers: [
                SliverPadding(
                    padding: const EdgeInsets.all(16),
                    sliver: SliverToBoxAdapter(
                        child: Container(
                      padding: const EdgeInsets.all(26),
                      decoration: BoxDecoration(
                          color: green,
                          borderRadius: BorderRadius.circular(26)),
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('СВЕЖЕЕ КАЖДЫЙ ДЕНЬ',
                                style: TextStyle(
                                    color: Color(0xffffdf9e),
                                    letterSpacing: 2,
                                    fontSize: 11)),
                            const SizedBox(height: 14),
                            Text('Продукты\nдля вашего дня',
                                style: TextStyle(
                                    color: Colors.white,
                                    fontSize:
                                        constraints.maxWidth > 600 ? 42 : 32,
                                    fontWeight: FontWeight.w800,
                                    height: 1.1)),
                            const SizedBox(height: 12),
                            const Text(
                                'Всё необходимое по честным ценам.\nСоберите корзину, остальное — за нами.',
                                style: TextStyle(color: Colors.white70)),
                          ]),
                    ))),
                SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    sliver: SliverToBoxAdapter(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                          TextField(
                              onChanged: (value) =>
                                  setState(() => query = value),
                              decoration: const InputDecoration(
                                  hintText: 'Найти продукты',
                                  prefixIcon: Icon(Icons.search))),
                          const SizedBox(height: 12),
                          SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              child: Row(children: [
                                for (final item in categories)
                                  Padding(
                                      padding: const EdgeInsets.only(right: 8),
                                      child: ChoiceChip(
                                          label: Text(item),
                                          selected: selectedCategory == item,
                                          onSelected: (_) =>
                                              setState(() => category = item))),
                              ])),
                          Wrap(
                              alignment: WrapAlignment.spaceBetween,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              spacing: 16,
                              children: [
                                Text('Товаров: ${visible.length}',
                                    style: const TextStyle(
                                        color: Color(0xff647168))),
                                SizedBox(
                                    width: 260,
                                    child: DropdownButton<String>(
                                        isExpanded: true,
                                        value: sort,
                                        underline: const SizedBox(),
                                        items: [
                                          'По умолчанию',
                                          'Сначала дешевле',
                                          'Сначала дороже',
                                          'По названию'
                                        ]
                                            .map((s) => DropdownMenuItem(
                                                value: s, child: Text(s)))
                                            .toList(),
                                        onChanged: (value) =>
                                            setState(() => sort = value!))),
                              ]),
                          if (store.loading) const LinearProgressIndicator(),
                          if (store.error != null)
                            Text(store.error!,
                                style: const TextStyle(color: Colors.red)),
                        ]))),
                if (visible.isEmpty)
                  const SliverToBoxAdapter(
                      child: Padding(
                          padding: EdgeInsets.all(32),
                          child: Text(
                              'Ничего не найдено. Измените поиск или категорию.',
                              textAlign: TextAlign.center))),
                SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    sliver: SliverGrid.builder(
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: columns,
                          mainAxisExtent: 325 +
                              (MediaQuery.textScalerOf(context).scale(14) -
                                      14) *
                                  12,
                          crossAxisSpacing: 12,
                          mainAxisSpacing: 12),
                      itemCount: visible.length,
                      itemBuilder: (context, index) =>
                          ProductCard(product: visible[index], store: store),
                    )),
              ]));
    });
  }
}

class ProductCard extends StatelessWidget {
  const ProductCard({required this.product, required this.store, super.key});
  final Product product;
  final StoreModel store;
  @override
  Widget build(BuildContext context) {
    final quantity = store.cart[product.id] ?? 0;
    return Card(
        child: Padding(
            padding: const EdgeInsets.all(14),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                  child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () => showDialog<void>(
                          context: context,
                          builder: (_) => AlertDialog(
                                title: Text('${product.emoji} ${product.name}'),
                                content: Text(
                                    '${product.description}\n\n${money(product.price)}\nВ наличии: ${product.stock}'),
                                actions: [
                                  TextButton(
                                      onPressed: () => Navigator.pop(context),
                                      child: const Text('Закрыть'))
                                ],
                              )),
                      child: Container(
                          width: double.infinity,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                              color: const Color(0xffedf1e8),
                              borderRadius: BorderRadius.circular(14)),
                          child: Text(product.emoji,
                              style: const TextStyle(fontSize: 54))))),
              const SizedBox(height: 10),
              Text(product.category.toUpperCase(),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 10,
                      letterSpacing: 1,
                      color: Color(0xff637f6d))),
              SizedBox(
                  height: MediaQuery.textScalerOf(context).scale(44),
                  child: Text(product.name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w600))),
              Text(money(product.price),
                  style: const TextStyle(
                      fontSize: 19, fontWeight: FontWeight.w800)),
              Text(
                  product.stock == 0
                      ? 'Нет в наличии'
                      : 'В наличии: ${product.stock}',
                  style:
                      const TextStyle(fontSize: 11, color: Color(0xff647168))),
              const SizedBox(height: 8),
              if (quantity == 0)
                SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                        onPressed: product.stock == 0 || store.checkingOut
                            ? null
                            : () => store.quantity(product, 1),
                        child: const Text('В корзину')))
              else
                QuantityControl(
                    value: quantity,
                    limit: product.limit,
                    busy: store.checkingOut,
                    changed: (value) => store.quantity(product, value)),
            ])));
  }
}

class QuantityControl extends StatelessWidget {
  const QuantityControl(
      {required this.value,
      required this.limit,
      required this.busy,
      required this.changed,
      super.key});
  final int value, limit;
  final bool busy;
  final ValueChanged<int> changed;
  @override
  Widget build(BuildContext context) => Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton(
                tooltip: value == 1 ? 'Удалить' : 'Уменьшить',
                onPressed: busy ? null : () => changed(value - 1),
                icon: Icon(value == 1 ? Icons.delete_outline : Icons.remove),
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                padding: EdgeInsets.zero),
            Text('$value', style: const TextStyle(fontWeight: FontWeight.bold)),
            IconButton(
                tooltip: 'Добавить',
                onPressed:
                    busy || value >= limit ? null : () => changed(value + 1),
                icon: const Icon(Icons.add),
                constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                padding: EdgeInsets.zero),
          ]);
}

class CartPage extends StatefulWidget {
  const CartPage(
      {required this.store,
      required this.onCatalog,
      required this.onOrders,
      super.key});
  final StoreModel store;
  final VoidCallback onCatalog, onOrders;
  @override
  State<CartPage> createState() => _CartPageState();
}

class _CartPageState extends State<CartPage> {
  late final address = TextEditingController(text: widget.store.address);
  String? error;
  @override
  void dispose() {
    address.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    final store = widget.store;
    if (store.checkingOut || store.restoring) return;
    if (!store.signedIn && !await signIn(context, store)) return;
    if (!mounted) return;
    setState(() => error = null);
    try {
      await store.checkout(address.text);
      if (!mounted) return;
      unawaited(store.refresh());
      widget.onOrders();
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final store = widget.store;
    if (!store.ready) {
      return EmptyState(
          icon: Icons.shopping_bag_outlined,
          title: 'Для корзины нужен актуальный каталог.',
          action: 'Открыть каталог',
          onPressed: widget.onCatalog);
    }
    if (store.cart.isEmpty) {
      return EmptyState(
          icon: Icons.shopping_bag_outlined,
          title: 'Корзина пока пуста',
          action: 'Выбрать продукты',
          onPressed: widget.onCatalog);
    }
    return ListView(padding: const EdgeInsets.all(20), children: [
      const Text('Ваша корзина',
          style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800)),
      const SizedBox(height: 20),
      for (final p in store.products.where((p) => store.cart.containsKey(p.id)))
        Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Card(
                child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(children: [
                Row(children: [
                  Text(p.emoji, style: const TextStyle(fontSize: 36)),
                  const SizedBox(width: 14),
                  Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                        Text(p.name,
                            style:
                                const TextStyle(fontWeight: FontWeight.bold)),
                        Text('${money(p.price)} за шт.')
                      ])),
                ]),
                Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      QuantityControl(
                          value: store.cart[p.id]!,
                          limit: p.limit,
                          busy: store.checkingOut,
                          changed: (value) => store.quantity(p, value)),
                      Text(money(p.price * store.cart[p.id]!),
                          style: const TextStyle(fontWeight: FontWeight.bold)),
                    ])
              ]),
            ))),
      const SizedBox(height: 16),
      Text('Итого: ${money(store.total)}',
          style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800)),
      const SizedBox(height: 8),
      const Text('Оплата согласуется при доставке.'),
      const SizedBox(height: 20),
      TextField(
          controller: address,
          enabled: !store.checkingOut,
          minLines: 1,
          maxLines: 3,
          maxLength: 500,
          keyboardType: TextInputType.streetAddress,
          autofillHints: const [AutofillHints.fullStreetAddress],
          onChanged: (value) => store.preferences.setString('address', value),
          decoration: const InputDecoration(
              labelText: 'Адрес доставки',
              hintText: 'Город, улица, дом, квартира')),
      if (error != null)
        Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error))),
      FilledButton.icon(
          onPressed: store.checkingOut || store.restoring || store.loading
              ? null
              : submit,
          icon: store.checkingOut
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.check),
          label: Text(store.checkingOut
              ? 'Оформляем…'
              : store.signedIn
                  ? 'Оформить заказ'
                  : 'Войти и оформить')),
    ]);
  }
}

class AuthDialog extends StatefulWidget {
  const AuthDialog({required this.store, super.key});
  final StoreModel store;
  @override
  State<AuthDialog> createState() => _AuthDialogState();
}

class _AuthDialogState extends State<AuthDialog> {
  final form = GlobalKey<FormState>();
  final name = TextEditingController(),
      email = TextEditingController(),
      password = TextEditingController();
  bool register = false, busy = false;
  String? error;
  @override
  void dispose() {
    name.dispose();
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> submit() async {
    if (busy || !form.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.store
          .authenticate(register, name.text, email.text, password.text);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
      canPop: !busy,
      child: AlertDialog(
        title: Text(register ? 'Создать аккаунт' : 'С возвращением'),
        content: SizedBox(
            width: 360,
            child: SingleChildScrollView(
                child: Form(
                    key: form,
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      if (register)
                        Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: TextFormField(
                                controller: name,
                                enabled: !busy,
                                maxLength: 100,
                                textCapitalization: TextCapitalization.words,
                                decoration:
                                    const InputDecoration(labelText: 'Имя'),
                                validator: (v) => v!.trim().length < 2
                                    ? 'Не менее 2 символов'
                                    : null)),
                      TextFormField(
                          controller: email,
                          enabled: !busy,
                          maxLength: 320,
                          keyboardType: TextInputType.emailAddress,
                          autofillHints: const [AutofillHints.email],
                          decoration: const InputDecoration(
                              labelText: 'Email', counterText: ''),
                          validator: (v) =>
                              !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
                                      .hasMatch(v!.trim())
                                  ? 'Укажите корректный email'
                                  : null),
                      const SizedBox(height: 12),
                      TextFormField(
                          controller: password,
                          enabled: !busy,
                          maxLength: 128,
                          obscureText: true,
                          onFieldSubmitted: (_) => submit(),
                          decoration: const InputDecoration(
                              labelText: 'Пароль', counterText: ''),
                          validator: (v) => v!.isEmpty ||
                                  (register && v.length < 8)
                              ? 'Пароль ${register ? 'от 8 символов' : 'обязателен'}'
                              : null),
                      if (error != null)
                        Padding(
                            padding: const EdgeInsets.only(top: 12),
                            child: Text(error!,
                                style: TextStyle(
                                    color:
                                        Theme.of(context).colorScheme.error))),
                      TextButton(
                          onPressed: busy
                              ? null
                              : () => setState(() {
                                    register = !register;
                                    error = null;
                                    form.currentState!.reset();
                                  }),
                          child: Text(register
                              ? 'Уже есть аккаунт'
                              : 'Зарегистрироваться')),
                    ])))),
        actions: [
          TextButton(
              onPressed: busy ? null : () => Navigator.pop(context, false),
              child: const Text('Отмена')),
          FilledButton(
              onPressed: busy ? null : submit,
              child: Text(busy
                  ? 'Подождите…'
                  : register
                      ? 'Создать'
                      : 'Войти'))
        ],
      ));
}

class OrdersPage extends StatefulWidget {
  const OrdersPage({required this.store, required this.active, super.key});
  final StoreModel store;
  final bool active;
  @override
  State<OrdersPage> createState() => _OrdersPageState();
}

class _OrdersPageState extends State<OrdersPage> {
  List<dynamic>? orders;
  String? error;
  bool loading = false;
  @override
  void initState() {
    super.initState();
    if (widget.active) unawaited(load());
  }

  @override
  void didUpdateWidget(covariant OrdersPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !oldWidget.active) unawaited(load());
  }

  Future<void> load() async {
    if (!widget.store.signedIn || loading) return;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final result = await widget.store.orders();
      if (mounted) setState(() => orders = result);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.store.restoring) {
      return const Center(child: CircularProgressIndicator());
    }
    if (!widget.store.signedIn) {
      return EmptyState(
          icon: Icons.receipt_long_outlined,
          title: 'Ваши заказы будут здесь',
          action: 'Войти',
          onPressed: () => signIn(context, widget.store));
    }
    if (loading && orders == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (error != null) {
      return EmptyState(
          icon: Icons.wifi_off,
          title: error!,
          action: 'Повторить',
          onPressed: load);
    }
    return RefreshIndicator(
        onRefresh: load,
        child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(20),
            children: [
              Row(children: [
                const Expanded(
                    child: Text('Мои заказы',
                        style: TextStyle(
                            fontSize: 28, fontWeight: FontWeight.w800))),
                IconButton(
                    tooltip: 'Обновить заказы',
                    onPressed: loading ? null : load,
                    icon: const Icon(Icons.refresh))
              ]),
              if (loading) const LinearProgressIndicator(),
              if (orders?.isEmpty ?? true)
                const Padding(
                    padding: EdgeInsets.all(30),
                    child: Text('Заказов пока нет. Начните с каталога.')),
              for (final order in orders ?? [])
                Padding(
                    padding: const EdgeInsets.only(top: 14),
                    child: Card(
                        child: Padding(
                            padding: const EdgeInsets.all(18),
                            child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Заказ №${order['id']}',
                                      style: const TextStyle(
                                          fontSize: 20,
                                          fontWeight: FontWeight.bold)),
                                  Chip(
                                      label: Text(
                                          orderStatuses[order['status']] ??
                                              order['status'].toString())),
                                  Text(_date(order['created_at'].toString()),
                                      style: const TextStyle(
                                          color: Color(0xff647168))),
                                  const SizedBox(height: 8),
                                  Text(order['shipping_address'].toString()),
                                  const Divider(),
                                  for (final item in order['items'] as List)
                                    Padding(
                                        padding: const EdgeInsets.symmetric(
                                            vertical: 3),
                                        child: Text(
                                            '${item['product_name']} × ${item['quantity']} · ${money(double.parse(item['unit_price'].toString()))}')),
                                  const SizedBox(height: 10),
                                  Text(
                                      'Итого: ${money(double.parse(order['total'].toString()))}',
                                      style: const TextStyle(
                                          fontSize: 20,
                                          fontWeight: FontWeight.bold)),
                                ])))),
            ]));
  }

  String _date(String value) {
    final date = DateTime.tryParse(value)?.toLocal();
    if (date == null) return value;
    return '${date.day.toString().padLeft(2, '0')}.${date.month.toString().padLeft(2, '0')}.${date.year}';
  }
}

class ProfilePage extends StatelessWidget {
  const ProfilePage({required this.store, super.key});
  final StoreModel store;
  @override
  Widget build(BuildContext context) {
    if (store.restoring) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView(padding: const EdgeInsets.all(24), children: [
      const Icon(Icons.account_circle_outlined, size: 80, color: green),
      const SizedBox(height: 20),
      Text(
          store.user?['name']?.toString() ??
              (store.signedIn ? 'Ваш аккаунт' : 'Добро пожаловать'),
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800)),
      const SizedBox(height: 12),
      Text(
          store.user?['email']?.toString() ??
              'Войдите, чтобы оформлять покупки и отслеживать заказы.',
          textAlign: TextAlign.center),
      const SizedBox(height: 24),
      FilledButton(
          onPressed: store.checkingOut
              ? null
              : () async {
                  if (store.signedIn) {
                    await store.logout();
                  } else {
                    await signIn(context, store);
                  }
                },
          child: Text(store.signedIn
              ? 'Выйти из аккаунта'
              : 'Войти / Зарегистрироваться')),
      const SizedBox(height: 24),
      const Text(
          'Корзина и адрес сохраняются на этом устройстве. Заказы доступны после входа в ваш аккаунт.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Color(0xff647168))),
    ]);
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState(
      {required this.icon,
      required this.title,
      required this.action,
      required this.onPressed,
      super.key});
  final IconData icon;
  final String title, action;
  final VoidCallback onPressed;
  @override
  Widget build(BuildContext context) => Center(
      child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 60, color: green),
            const SizedBox(height: 20),
            Text(title, textAlign: TextAlign.center),
            const SizedBox(height: 20),
            FilledButton(onPressed: onPressed, child: Text(action)),
          ])));
}
