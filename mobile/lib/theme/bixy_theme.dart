import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'colors.dart';

// Theme builder pattern adapted from `tasky` by Youssef Awad Sadek (MIT):
// derive the whole Material 3 palette from one seed color instead of
// hand-picking dozens of surface hexes.
class BixyTheme {
  static const Color seed = Color(0xFF2BFF88);

  static ThemeData dark() {
    final scheme = ColorScheme.fromSeed(
      seedColor: seed,
      brightness: Brightness.dark,
    );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: BixyColors.background,
    );

    return base.copyWith(
      textTheme: GoogleFonts.plusJakartaSansTextTheme(base.textTheme).copyWith(
        displayLarge: GoogleFonts.fraunces(
          fontSize: 40,
          fontWeight: FontWeight.w600,
          letterSpacing: -1.0,
          height: 1.0,
          color: scheme.onSurface,
        ),
        displayMedium: GoogleFonts.fraunces(
          fontSize: 30,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.8,
          color: scheme.onSurface,
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: BixyColors.background,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.fraunces(
          fontSize: 22,
          fontWeight: FontWeight.w600,
          color: scheme.onSurface,
        ),
      ),
      cardTheme: CardTheme(
        elevation: 0,
        color: scheme.surfaceContainerHighest.withOpacity(0.4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        clipBehavior: Clip.antiAlias,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surfaceContainerHighest.withOpacity(0.5),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: scheme.primary, width: 1.5),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          textStyle: GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: scheme.surface,
        indicatorColor: scheme.secondaryContainer,
      ),
    );
  }

  /// Editorial display style (Fraunces) for hero numerals + titles.
  static TextStyle display(double size, {Color? color, FontWeight? weight}) {
    return GoogleFonts.fraunces(
      fontSize: size,
      fontWeight: weight ?? FontWeight.w600,
      letterSpacing: -0.02 * size,
      height: 1.02,
      color: color ?? BixyColors.textPrimary,
    );
  }

  static TextStyle body(double size,
      {Color? color, FontWeight? weight, double? height}) {
    return GoogleFonts.plusJakartaSans(
      fontSize: size,
      fontWeight: weight ?? FontWeight.w500,
      height: height ?? 1.4,
      color: color ?? BixyColors.textSecondary,
    );
  }

  static TextStyle mono(double size, {Color? color, FontWeight? weight}) {
    return TextStyle(
      fontFamily: 'monospace',
      fontFamilyFallback: const ['Menlo', 'Courier'],
      fontSize: size,
      fontWeight: weight ?? FontWeight.w500,
      color: color ?? BixyColors.textSecondary,
    );
  }

  /// Small caps section label, letterspaced.
  static TextStyle eyebrow({Color? color}) {
    return GoogleFonts.plusJakartaSans(
      fontSize: 10.5,
      fontWeight: FontWeight.w800,
      letterSpacing: 1.4,
      color: color ?? BixyColors.textMuted,
    );
  }
}
