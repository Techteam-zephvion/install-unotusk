import 'package:flutter/material.dart';
import '../../theme/app_fonts.dart';
import 'app_colors.dart';

class AppTextStyles {
  // ─── Font family shortcuts ───────────────────────────────────────────────────

  /// Young Serif — logo wordmark + auth headings
  static TextStyle youngSerif({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      AppFonts.youngSerif(
        fontSize: fontSize ?? 20,
        color: color ?? AppColors.textPrimary,
        letterSpacing: letterSpacing,
        lineHeight: height,
      );

  /// Instrument Serif — hero headings (Instrument Serif, Regular weight only)
  static TextStyle instrumentSerif({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      AppFonts.display(
        fontSize: fontSize ?? 26,
        color: color ?? AppColors.textPrimary,
        letterSpacing: letterSpacing,
        lineHeight: height ?? 1.2,
      );

  /// DM Sans — body text, nav labels, general UI
  static TextStyle inter({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      AppFonts.body(
        fontSize: fontSize ?? 14,
        fontWeight: fontWeight,
        color: color ?? AppColors.textPrimary,
        letterSpacing: letterSpacing,
        height: height,
      );

  /// JetBrains Mono — badge labels, processing phases, code
  static TextStyle mono({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      AppFonts.mono(
        fontSize: fontSize ?? 11,
        fontWeight: fontWeight,
        color: color ?? AppColors.textSecondary,
        letterSpacing: letterSpacing,
        height: height,
      );

  // ─── Named semantic styles ─────────────────────────────────────────────────

  /// Logo wordmark "Unotusk" in sidebar
  static TextStyle get logoWordmark => AppFonts.youngSerif(
        fontSize: 17,
        color: AppColors.textPrimary,
        letterSpacing: -0.17,
      );

  /// Auth screen h1 — "Sign in to Unotusk"
  static TextStyle get authHeading => AppFonts.accent(
        fontSize: 24,
        color: AppColors.textPrimary,
        letterSpacing: -0.48,
        lineHeight: 1.2,
      );

  /// Chat hero h1 — "Investigate your project?"
  static TextStyle get heroHeading => AppFonts.display(
        fontSize: 26,
        color: AppColors.textPrimary,
        letterSpacing: -0.26,
        lineHeight: 1.2,
      );

  /// Sidebar nav item label
  static TextStyle navLabel({bool active = false}) => AppFonts.body(
        fontSize: 13,
        fontWeight: active ? FontWeight.w600 : FontWeight.w400,
        color: active ? AppColors.accent : AppColors.textSecondary,
      );

  /// Section header (RECENT, etc.)
  static TextStyle get sectionLabel => AppFonts.mono(
        fontSize: 10,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
        letterSpacing: 0.6,
      );

  /// Standard body text
  static TextStyle get body => AppFonts.body(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        height: 1.5,
      );

  /// Body 14px (auth descriptions, input labels)
  static TextStyle get bodyMd => AppFonts.body(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        height: 1.55,
      );

  /// Caption / secondary 12px
  static TextStyle get caption => AppFonts.body(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
        height: 1.4,
      );

  /// Monospace badge/tag
  static TextStyle get monoBadge => AppFonts.mono(
        fontSize: 10,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.4,
        color: AppColors.textSecondary,
      );

  /// Phase processing label ("INGESTING ΔDOC")
  static TextStyle get monoPhaseLabel => AppFonts.mono(
        fontSize: 11,
        fontWeight: FontWeight.w400,
        letterSpacing: 0.88,
        color: AppColors.live,
      );

  /// Code display
  static TextStyle get code => AppFonts.mono(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
      );

  // ─── Legacy aliases for backward-compat ─────────────────────────────────────
  static TextStyle get editorialHero => heroHeading;
  static TextStyle get editorialSub => caption;
  static TextStyle get h1 => AppFonts.accent(
        fontSize: 20,
        color: AppColors.textPrimary,
        letterSpacing: -0.3,
      );
  static TextStyle get h2 => AppFonts.body(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
        letterSpacing: -0.2,
      );
  static TextStyle get h3 => AppFonts.body(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
      );
  static TextStyle get bodyMedium => body;
  static TextStyle get bodySmall => caption;
  static TextStyle get label => AppFonts.body(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: AppColors.textSecondary,
      );
}
