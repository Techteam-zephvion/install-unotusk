import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

class AppTextStyles {
  // ─── Font family shortcuts ───────────────────────────────────────────────────

  /// Young Serif — logo wordmark + auth headings (Figma: "Young Serif")
  static TextStyle youngSerif({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      GoogleFonts.youngSerif(
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color ?? AppColors.textPrimary,
        letterSpacing: letterSpacing,
        height: height,
      );

  /// Instrument Serif — hero "Investigate your project?" (Figma: "Instrument Serif")
  static TextStyle instrumentSerif({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      GoogleFonts.instrumentSerif(
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color ?? AppColors.textPrimary,
        letterSpacing: letterSpacing,
        height: height,
      );

  /// Inter / Geist — body text, nav labels, general UI (Figma: "Geist" / "Inter")
  static TextStyle inter({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      GoogleFonts.inter(
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color ?? AppColors.textPrimary,
        letterSpacing: letterSpacing,
        height: height,
      );

  /// IBM Plex Mono — badge labels, processing phases (Figma: "Geist Mono" / "IBM Plex Mono")
  static TextStyle mono({
    double? fontSize,
    FontWeight fontWeight = FontWeight.w400,
    Color? color,
    double? letterSpacing,
    double? height,
  }) =>
      GoogleFonts.ibmPlexMono(
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color ?? AppColors.textSecondary,
        letterSpacing: letterSpacing,
        height: height,
      );

  // ─── Named semantic styles (matching Figma exactly) ─────────────────────────

  /// Logo wordmark "Unotusk" in sidebar
  /// Figma: Young Serif, 17px, -0.01em, color: text
  static TextStyle get logoWordmark => GoogleFonts.youngSerif(
        fontSize: 17,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        letterSpacing: -0.17,
      );

  /// Auth screen h1 — "Sign in to Unotusk"
  /// Figma: Young Serif, 24px, -0.02em, color: text
  static TextStyle get authHeading => GoogleFonts.youngSerif(
        fontSize: 24,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        letterSpacing: -0.48,
        height: 1.2,
      );

  /// Chat hero h1 — "Investigate your project?"
  /// Figma: Instrument Serif, 26px, -0.01em, weight 400
  static TextStyle get heroHeading => GoogleFonts.instrumentSerif(
        fontSize: 26,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        letterSpacing: -0.26,
        height: 1.2,
      );

  /// Sidebar nav item label
  /// Figma: Geist, 13px, weight 400 (inactive) / 600 (active)
  static TextStyle navLabel({bool active = false}) => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: active ? FontWeight.w600 : FontWeight.w400,
        color: active ? AppColors.accent : AppColors.textSecondary,
      );

  /// Section header (RECENT, etc.)
  /// Figma: Geist Mono, 10px, 0.06em tracking, uppercase
  static TextStyle get sectionLabel => GoogleFonts.ibmPlexMono(
        fontSize: 10,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
        letterSpacing: 0.6,
      );

  /// Standard body text
  /// Figma: Geist/Inter, 13px, weight 400
  static TextStyle get body => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        height: 1.5,
      );

  /// Body 14px (auth descriptions, input labels)
  static TextStyle get bodyMd => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        height: 1.55,
      );

  /// Caption / secondary 12px
  static TextStyle get caption => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
        height: 1.4,
      );

  /// Monospace badge/tag
  /// Figma: Geist Mono, 10px, 0.04em tracking
  static TextStyle get monoBadge => GoogleFonts.ibmPlexMono(
        fontSize: 10,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.4,
        color: AppColors.textSecondary,
      );

  /// Phase processing label ("INGESTING ΔDOC")
  /// Figma: IBM Plex Mono, 11px, 0.08em tracking
  static TextStyle get monoPhaseLabel => GoogleFonts.ibmPlexMono(
        fontSize: 11,
        fontWeight: FontWeight.w400,
        letterSpacing: 0.88,
        color: AppColors.live,
      );

  /// Code display
  static TextStyle get code => GoogleFonts.ibmPlexMono(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
      );

  // ─── Legacy aliases for backward-compat ─────────────────────────────────────
  static TextStyle get editorialHero => heroHeading;
  static TextStyle get editorialSub => caption;
  static TextStyle get h1 => GoogleFonts.youngSerif(
        fontSize: 20,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
        letterSpacing: -0.3,
      );
  static TextStyle get h2 => GoogleFonts.inter(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
        letterSpacing: -0.2,
      );
  static TextStyle get h3 => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
      );
  static TextStyle get bodyMedium => body;
  static TextStyle get bodySmall => caption;
  static TextStyle get label => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: AppColors.textSecondary,
      );
}
