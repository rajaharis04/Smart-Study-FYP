import 'package:flutter/material.dart';

/// App color palette for SmartStudyInstructor
class AppColors {
  AppColors._();

  // Brand colors
  static const Color primary = Color(0xFF1D9E75);   // teal green
  static const Color secondary = Color(0xFF7F77DD); // purple
  static const Color accent = Color(0xFFEF9F27);    // amber

  // Semantic colors
  static const Color error = Color(0xFFE53935);
  static const Color success = Color(0xFF43A047);
  static const Color warning = Color(0xFFFB8C00);
  static const Color info = Color(0xFF1E88E5);

  // Neutrals
  static const Color background = Color(0xFFF5F7FA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color onSecondary = Color(0xFFFFFFFF);
  static const Color onBackground = Color(0xFF1C1C2E);
  static const Color onSurface = Color(0xFF1C1C2E);
  static const Color textHint = Color(0xFFADB5BD);
  static const Color divider = Color(0xFFE9ECEF);
  static const Color cardShadow = Color(0x14000000);
}

/// Central theme configuration — access via [AppTheme.theme]
class AppTheme {
  AppTheme._();

  static ThemeData get theme => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme(
          brightness: Brightness.light,
          primary: AppColors.primary,
          onPrimary: AppColors.onPrimary,
          secondary: AppColors.secondary,
          onSecondary: AppColors.onSecondary,
          error: AppColors.error,
          onError: AppColors.onPrimary,
          surface: AppColors.surface,
          onSurface: AppColors.onSurface,
        ),
        scaffoldBackgroundColor: AppColors.background,

        // ── AppBar ────────────────────────────────────────────────────────────
        appBarTheme: const AppBarTheme(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.onPrimary,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: TextStyle(
            color: AppColors.onPrimary,
            fontSize: 18,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.3,
          ),
          iconTheme: IconThemeData(color: AppColors.onPrimary),
        ),

        // ── Elevated Button ───────────────────────────────────────────────────
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppColors.primary,
            foregroundColor: AppColors.onPrimary,
            elevation: 2,
            shadowColor: AppColors.primary.withOpacity(0.4),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            textStyle: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.3,
            ),
          ),
        ),

        // ── Outlined Button ───────────────────────────────────────────────────
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.primary,
            side: const BorderSide(color: AppColors.primary, width: 1.5),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),

        // ── Text Button ───────────────────────────────────────────────────────
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppColors.primary,
            textStyle: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),

        // ── Input Decoration ──────────────────────────────────────────────────
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: AppColors.surface,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: AppColors.divider),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: AppColors.divider),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide:
                const BorderSide(color: AppColors.primary, width: 1.8),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: AppColors.error),
          ),
          focusedErrorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: const BorderSide(color: AppColors.error, width: 1.8),
          ),
          hintStyle: const TextStyle(
            color: AppColors.textHint,
            fontSize: 14,
          ),
          labelStyle: const TextStyle(
            color: AppColors.onBackground,
            fontSize: 14,
          ),
          floatingLabelStyle: const TextStyle(
            color: AppColors.primary,
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
          errorStyle: const TextStyle(
            color: AppColors.error,
            fontSize: 12,
          ),
          prefixIconColor: AppColors.textHint,
          suffixIconColor: AppColors.textHint,
        ),

        // ── Text Theme ────────────────────────────────────────────────────────
        textTheme: const TextTheme(
          // Display
          displayLarge: TextStyle(
            fontSize: 57,
            fontWeight: FontWeight.w400,
            color: AppColors.onBackground,
            letterSpacing: -0.25,
          ),
          displayMedium: TextStyle(
            fontSize: 45,
            fontWeight: FontWeight.w400,
            color: AppColors.onBackground,
          ),
          displaySmall: TextStyle(
            fontSize: 36,
            fontWeight: FontWeight.w400,
            color: AppColors.onBackground,
          ),
          // Headline
          headlineLarge: TextStyle(
            fontSize: 32,
            fontWeight: FontWeight.w700,
            color: AppColors.onBackground,
          ),
          headlineMedium: TextStyle(
            fontSize: 28,
            fontWeight: FontWeight.w700,
            color: AppColors.onBackground,
          ),
          headlineSmall: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w600,
            color: AppColors.onBackground,
          ),
          // Title
          titleLarge: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w600,
            color: AppColors.onBackground,
          ),
          titleMedium: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: AppColors.onBackground,
            letterSpacing: 0.15,
          ),
          titleSmall: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w500,
            color: AppColors.onBackground,
            letterSpacing: 0.1,
          ),
          // Body
          bodyLarge: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w400,
            color: AppColors.onBackground,
            letterSpacing: 0.5,
          ),
          bodyMedium: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w400,
            color: AppColors.onBackground,
            letterSpacing: 0.25,
          ),
          bodySmall: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w400,
            color: AppColors.textHint,
            letterSpacing: 0.4,
          ),
          // Label
          labelLarge: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppColors.onBackground,
            letterSpacing: 0.1,
          ),
          labelMedium: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: AppColors.onBackground,
            letterSpacing: 0.5,
          ),
          labelSmall: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: AppColors.textHint,
            letterSpacing: 0.5,
          ),
        ),

        // ── Card Theme ────────────────────────────────────────────────────────
        cardTheme: CardThemeData(
          color: AppColors.surface,
          elevation: 2,
          shadowColor: AppColors.cardShadow,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          margin: const EdgeInsets.symmetric(horizontal: 0, vertical: 6),
        ),

        // ── Divider ───────────────────────────────────────────────────────────
        dividerTheme: const DividerThemeData(
          color: AppColors.divider,
          thickness: 1,
          space: 1,
        ),

        // ── Chip ──────────────────────────────────────────────────────────────
        chipTheme: ChipThemeData(
          backgroundColor: AppColors.primary.withOpacity(0.08),
          selectedColor: AppColors.primary,
          labelStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        ),

        // ── FloatingActionButton ──────────────────────────────────────────────
        floatingActionButtonTheme: const FloatingActionButtonThemeData(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.onPrimary,
          elevation: 4,
          shape: CircleBorder(),
        ),

        // ── SnackBar ──────────────────────────────────────────────────────────
        snackBarTheme: SnackBarThemeData(
          backgroundColor: AppColors.onBackground,
          contentTextStyle: const TextStyle(
            color: AppColors.surface,
            fontSize: 14,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          behavior: SnackBarBehavior.floating,
        ),
      );
}
