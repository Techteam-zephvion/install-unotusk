import 'package:flutter/material.dart';
import 'app_text_styles.dart';
import 'uno_palette.dart';

class AppTheme {
  static ThemeData get darkTheme => _buildTheme(UnoPalette.dark);
  static ThemeData get lightTheme => _buildTheme(UnoPalette.light);

  static ThemeData _buildTheme(UnoPalette palette) {
    final isDark = palette.isDark;

    return ThemeData(
      useMaterial3: true,
      brightness: isDark ? Brightness.dark : Brightness.light,
      scaffoldBackgroundColor: palette.bgBase,
      canvasColor: palette.bgBase,
      colorScheme: ColorScheme(
        brightness: isDark ? Brightness.dark : Brightness.light,
        primary: palette.accent,
        onPrimary: Colors.white,
        secondary: palette.output,
        onSecondary: Colors.white,
        error: palette.error,
        onError: Colors.white,
        surface: palette.bgSurface,
        onSurface: palette.text,
        surfaceContainerHighest: palette.bgElevated,
        onSurfaceVariant: palette.textSec,
        outline: palette.div,
        outlineVariant: palette.div.withValues(alpha: 0.5),
      ),
      dividerTheme: DividerThemeData(
        color: palette.div,
        thickness: 1,
        space: 1,
      ),
      cardTheme: CardThemeData(
        color: palette.bgSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: palette.div),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: palette.bgElevated,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        hintStyle: AppTextStyles.bodyMedium.copyWith(color: palette.textSec.withValues(alpha: 0.6)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: palette.div),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: palette.div),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: palette.accent, width: 1.5),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: palette.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: palette.error, width: 1.5),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: palette.accent,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: AppTextStyles.label.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: palette.text,
          side: BorderSide(color: palette.div),
          backgroundColor: palette.bgElevated,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 11),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: AppTextStyles.label.copyWith(
            color: palette.text,
            fontWeight: FontWeight.w500,
            fontSize: 13,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: palette.textSec,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: AppTextStyles.label.copyWith(
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
      iconTheme: IconThemeData(
        color: palette.textSec,
        size: 20,
      ),
    );
  }
}
