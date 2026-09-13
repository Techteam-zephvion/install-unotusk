import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppTextStyles {
  static const List<String> _fontFamilyFallback = [
    'Inter',
    '-apple-system',
    'BlinkMacSystemFont',
    'Segoe UI',
    'Roboto',
    'Helvetica Neue',
    'Arial',
    'sans-serif',
  ];

  static const List<String> _codeFontFamilyFallback = [
    'JetBrains Mono',
    'Fira Code',
    'Consolas',
    'Monaco',
    'Courier New',
    'monospace',
  ];

  static TextStyle get h1 => const TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: AppColors.slate900,
        letterSpacing: -0.2,
        fontFamilyFallback: _fontFamilyFallback,
      );

  static TextStyle get h2 => const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.slate900,
        letterSpacing: -0.1,
        fontFamilyFallback: _fontFamilyFallback,
      );

  static TextStyle get h3 => const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.slate900,
        fontFamilyFallback: _fontFamilyFallback,
      );

  static TextStyle get bodyMedium => const TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        color: AppColors.slate700,
        height: 1.4,
        fontFamilyFallback: _fontFamilyFallback,
      );

  static TextStyle get bodySmall => const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.slate500,
        height: 1.3,
        fontFamilyFallback: _fontFamilyFallback,
      );

  static TextStyle get label => const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: AppColors.slate700,
        fontFamilyFallback: _fontFamilyFallback,
      );

  static TextStyle get code => const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.slate800,
        fontFamilyFallback: _codeFontFamilyFallback,
      );
}
