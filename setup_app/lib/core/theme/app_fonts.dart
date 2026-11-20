import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Central Typography System for Unotusk Server Setup App
/// Exactly aligned with Employee App (`app/lib/theme/app_fonts.dart`).
///
/// 1. Editorial serif (headers):
///    - Primary display: Instrument Serif (Regular weight only)
///    - Accent display: DM Serif Display (Regular weight only)
///    - Brand display: Young Serif (Regular weight only)
///
/// 2. Sans (body and labels):
///    - DM Sans (default app font)
///
/// 3. Monospace (ports, hashes, code, logs):
///    - JetBrains Mono
class AppFonts {
  /// Base textTheme for ThemeData using DM Sans
  static TextTheme textTheme([TextTheme? base]) {
    return GoogleFonts.dmSansTextTheme(base);
  }

  /// Primary Display: Instrument Serif
  /// NOTE: Instrument Serif only has a regular weight (w400).
  static TextStyle display({
    double fontSize = 26,
    Color? color,
    FontStyle fontStyle = FontStyle.normal,
    double lineHeight = 1.2,
    double? letterSpacing,
  }) {
    return GoogleFonts.instrumentSerif(
      fontSize: fontSize,
      fontWeight: FontWeight.w400,
      color: color,
      fontStyle: fontStyle,
      height: lineHeight,
      letterSpacing: letterSpacing,
    );
  }

  /// Accent Display: DM Serif Display
  static TextStyle accent({
    double fontSize = 20,
    Color? color,
    FontStyle fontStyle = FontStyle.normal,
    double lineHeight = 1.2,
    double? letterSpacing,
  }) {
    return GoogleFonts.dmSerifDisplay(
      fontSize: fontSize,
      fontWeight: FontWeight.w400,
      color: color,
      fontStyle: fontStyle,
      height: lineHeight,
      letterSpacing: letterSpacing,
    );
  }

  /// Young Serif — dedicated for brand headers & wordmarks
  static TextStyle youngSerif({
    double fontSize = 17,
    Color? color,
    FontStyle fontStyle = FontStyle.normal,
    double? letterSpacing = -0.2,
    double? lineHeight,
  }) {
    return GoogleFonts.youngSerif(
      fontSize: fontSize,
      fontWeight: FontWeight.w400,
      color: color,
      fontStyle: fontStyle,
      letterSpacing: letterSpacing,
      height: lineHeight,
    );
  }

  /// Sans: DM Sans
  static TextStyle body({
    double fontSize = 14,
    FontWeight fontWeight = FontWeight.normal,
    Color? color,
    double? height = 1.5,
    double? letterSpacing,
    FontStyle fontStyle = FontStyle.normal,
  }) {
    return GoogleFonts.dmSans(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
      letterSpacing: letterSpacing,
      fontStyle: fontStyle,
    );
  }

  /// Monospace: JetBrains Mono
  static TextStyle mono({
    double fontSize = 11,
    FontWeight fontWeight = FontWeight.normal,
    Color? color,
    double? height,
    double? letterSpacing = 0.5,
    FontStyle fontStyle = FontStyle.normal,
  }) {
    return GoogleFonts.jetBrainsMono(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
      letterSpacing: letterSpacing,
      fontStyle: fontStyle,
    );
  }
}
