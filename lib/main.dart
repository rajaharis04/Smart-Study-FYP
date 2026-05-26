import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme.dart';
import 'core/router.dart';
import 'core/constants.dart';
import 'providers/settings_provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    // Wrap with ProviderScope to enable Riverpod throughout the widget tree
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

/// Root application widget.
class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);

    return MaterialApp.router(
      // ── App metadata ──────────────────────────────────────────────────────
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,

      // ── Theme ─────────────────────────────────────────────────────────────
      theme: settings.isDarkMode ? AppTheme.darkTheme : AppTheme.theme,

      // ── Router ────────────────────────────────────────────────────────────
      routerConfig: appRouter,
    );
  }
}
