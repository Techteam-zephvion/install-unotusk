import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_fonts.dart';
import 'uno_palette.dart';

class UnoTypography {
  static TextStyle displaySerif({
    required UnoPalette palette,
    double fontSize = 26,
    FontWeight fontWeight = FontWeight.w400,
    double lineHeight = 1.2,
    FontStyle fontStyle = FontStyle.normal,
    double? letterSpacing,
  }) {
    return AppFonts.display(
      fontSize: fontSize,
      color: palette.text,
      fontStyle: fontStyle,
      lineHeight: lineHeight,
      letterSpacing: letterSpacing,
    );
  }

  static TextStyle brandSerif({
    required UnoPalette palette,
    double fontSize = 17,
    FontWeight fontWeight = FontWeight.w400,
    double? letterSpacing = -0.2,
    FontStyle fontStyle = FontStyle.normal,
  }) {
    return AppFonts.youngSerif(
      fontSize: fontSize,
      color: palette.text,
      fontStyle: fontStyle,
      letterSpacing: letterSpacing,
    );
  }

  static TextStyle accentSerif({
    required UnoPalette palette,
    double fontSize = 18,
    FontWeight fontWeight = FontWeight.w400,
    double? letterSpacing,
    FontStyle fontStyle = FontStyle.normal,
  }) {
    return AppFonts.accent(
      fontSize: fontSize,
      color: palette.text,
      fontStyle: fontStyle,
      letterSpacing: letterSpacing,
    );
  }

  static TextStyle mono({
    required Color color,
    double fontSize = 11,
    FontWeight fontWeight = FontWeight.normal,
    double letterSpacing = 0.5,
    double? height,
  }) {
    return AppFonts.mono(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      letterSpacing: letterSpacing,
      height: height,
    );
  }

  static TextStyle body({
    required Color color,
    double fontSize = 13.5,
    FontWeight fontWeight = FontWeight.normal,
    double height = 1.5,
    double? letterSpacing,
    FontStyle fontStyle = FontStyle.normal,
  }) {
    return AppFonts.body(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
      letterSpacing: letterSpacing,
      fontStyle: fontStyle,
    );
  }
}

class AppTextStyles {
  static TextStyle get h1 => GoogleFonts.instrumentSerif(
        fontSize: 28,
        fontWeight: FontWeight.w400,
        color: const Color(0xFFF4F1EC),
        letterSpacing: -0.2,
      );

  static TextStyle get h2 => GoogleFonts.youngSerif(
        fontSize: 20,
        fontWeight: FontWeight.w400,
        color: const Color(0xFFF4F1EC),
        letterSpacing: -0.2,
      );

  static TextStyle get h3 => GoogleFonts.youngSerif(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        color: const Color(0xFFF4F1EC),
      );

  static TextStyle get bodyMedium => GoogleFonts.dmSans(
        fontSize: 13.5,
        fontWeight: FontWeight.w400,
        color: const Color(0xFFF4F1EC),
        height: 1.45,
      );

  static TextStyle get bodySmall => GoogleFonts.dmSans(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: const Color(0xFFA5A5AE),
        height: 1.35,
      );

  static TextStyle get label => GoogleFonts.dmSans(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: const Color(0xFFA5A5AE),
        letterSpacing: 0.2,
      );

  static TextStyle get code => GoogleFonts.jetBrainsMono(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: const Color(0xFFE9DFD0),
        letterSpacing: 0.3,
      );

  // Context-aware helpers
  static TextStyle h1Of(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.displaySerif(palette: palette, fontSize: 28);
  }

  static TextStyle h2Of(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.brandSerif(palette: palette, fontSize: 20);
  }

  static TextStyle h3Of(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.brandSerif(palette: palette, fontSize: 16);
  }

  static TextStyle bodyMediumOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.body(color: palette.text, fontSize: 13.5);
  }

  static TextStyle bodySmallOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.body(color: palette.textSec, fontSize: 12, height: 1.35);
  }

  static TextStyle labelOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return GoogleFonts.dmSans(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      color: palette.textSec,
      letterSpacing: 0.2,
    );
  }

  static TextStyle codeOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.mono(color: palette.accent, fontSize: 12);
  }
}
