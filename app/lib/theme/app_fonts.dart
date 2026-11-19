import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Central Typography System for Unotusk
///
/// 1. Editorial serif (headers):
///    - Primary display: Instrument Serif (Regular weight only)
///    - Accent display: DM Serif Display (Regular weight only)
///    - Used for: workspace tab hero titles, spec titles, and intelligence report headers.
///
/// 2. Sans (body and labels):
///    - DM Sans (default app font)
///    - Used for: sidebar navigation, dialog text, buttons, and form inputs.
///
/// 3. Monospace (code and citations):
///    - JetBrains Mono (with IBM Plex Mono fallback)
///    - Used for: file paths, line ranges, commit hashes, AST symbol identifiers, and diff hunks.
class AppFonts {
  /// Base textTheme for ThemeData (light and dark) using DM Sans
  static TextTheme textTheme([TextTheme? base]) {
    return GoogleFonts.dmSansTextTheme(base);
  }

  /// Primary Display: Instrument Serif
  /// NOTE: Instrument Serif only has a regular weight.
  /// Do not apply FontWeight.bold to it; use size and spacing for hierarchy.
  static TextStyle display({
    double fontSize = 26,
    Color? color,
    FontStyle fontStyle = FontStyle.normal,
    double lineHeight = 1.2,
    double? letterSpacing,
  }) {
    return GoogleFonts.instrumentSerif(
      fontSize: fontSize,
      fontWeight: FontWeight.w400, // Regular weight strictly enforced
      color: color,
      fontStyle: fontStyle,
      height: lineHeight,
      letterSpacing: letterSpacing,
    );
  }

  /// Accent Display: DM Serif Display
  /// NOTE: DM Serif Display only has a regular weight.
  /// Do not apply FontWeight.bold to it; use size and spacing for hierarchy.
  static TextStyle accent({
    double fontSize = 20,
    Color? color,
    FontStyle fontStyle = FontStyle.normal,
    double lineHeight = 1.2,
    double? letterSpacing,
  }) {
    return GoogleFonts.dmSerifDisplay(
      fontSize: fontSize,
      fontWeight: FontWeight.w400, // Regular weight strictly enforced
      color: color,
      fontStyle: fontStyle,
      height: lineHeight,
      letterSpacing: letterSpacing,
    );
  }

  /// Young Serif — dedicated for the "Unotusk" brand wordmark next to the logo emblem
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
  /// Used for sidebar navigation, dialog text, buttons, and form inputs.
  static TextStyle body({
    double fontSize = 14,
    FontWeight fontWeight = FontWeight.normal,
    Color? color,
    double? height,
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

  /// Monospace: JetBrains Mono (IBM Plex Mono fallback)
  /// Used for file paths, line ranges, commit hashes, AST symbol identifiers, and diff hunks.
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
