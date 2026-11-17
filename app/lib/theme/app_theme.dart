import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class UnoPalette {
  final Color bgBase;
  final Color bgSurface;
  final Color bgElevated;
  final Color div;
  final Color accent;
  final Color output;
  final Color live;
  final Color confirmed;
  final Color inferred;
  final Color neutral;
  final Color text;
  final Color textSec;

  const UnoPalette({
    required this.bgBase,
    required this.bgSurface,
    required this.bgElevated,
    required this.div,
    required this.accent,
    required this.output,
    required this.live,
    required this.confirmed,
    required this.inferred,
    required this.neutral,
    required this.text,
    required this.textSec,
  });

  static const dark = UnoPalette(
    bgBase: Color(0xFF0A0F20),
    bgSurface: Color(0xFF161A29),
    bgElevated: Color(0xFF1E2336),
    div: Color(0xFF2E313C),
    accent: Color(0xFFCBC1B4),
    output: Color(0xFFCBC1B4),
    live: Color(0xFF22C55E),
    confirmed: Color(0xFFCBC1B4),
    inferred: Color(0xFF84878F),
    neutral: Color(0xFF84878F),
    text: Color(0xFFFFFFFF),
    textSec: Color(0xFF84878F),
  );

  static const light = UnoPalette(
    bgBase: Color(0xFFF2EFE9),
    bgSurface: Color(0xFFF5F2EB),
    bgElevated: Color(0xFFFFFFFF),
    div: Color(0xFFE4DFD6),
    accent: Color(0xFF0A0F20),
    output: Color(0xFF0A0F20),
    live: Color(0xFF22C55E),
    confirmed: Color(0xFF0A0F20),
    inferred: Color(0xFF6B686A),
    neutral: Color(0xFF6B686A),
    text: Color(0xFF0A0F20),
    textSec: Color(0xFF6B686A),
  );

  bool get isDark => bgBase == const Color(0xFF0A0F20);

  Color get surface => bgSurface;
  Color get warn => const Color(0xFFE59866);

  // ── Multi-Gradient Tonal Depth System (Strictly Within Palette Shade) ──

  /// Main page canvas gradient: subtle multi-stop tonal atmosphere
  LinearGradient get pageGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.48, 1.0],
          colors: [
            Color(0xFF070B18), // Deepest obsidian top-left
            Color(0xFF0A0F20), // Core Obsidian Navy
            Color(0xFF121930), // Soft midnight navy glow bottom-right
          ],
        )
      : const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.48, 1.0],
          colors: [
            Color(0xFFFAF8F4), // Crisp warm alabaster top-left
            Color(0xFFF2EFE9), // Core Warm Sand
            Color(0xFFE7E0D5), // Richer warm linen bottom-right
          ],
        );

  /// Sidebar navigation vertical tonal gradient
  LinearGradient get sidebarGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          stops: [0.0, 0.55, 1.0],
          colors: [
            Color(0xFF14192B),
            Color(0xFF111626),
            Color(0xFF0C101F),
          ],
        )
      : const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          stops: [0.0, 0.55, 1.0],
          colors: [
            Color(0xFFF9F6F0),
            Color(0xFFF4EFE7),
            Color(0xFFEBE4D9),
          ],
        );

  /// Top navigation bar subtle horizontal tonal sheen
  LinearGradient get headerGradient => isDark
      ? const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          stops: [0.0, 0.5, 1.0],
          colors: [
            Color(0xFF0F1426),
            Color(0xFF151C32),
            Color(0xFF0D1223),
          ],
        )
      : const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          stops: [0.0, 0.5, 1.0],
          colors: [
            Color(0xFFFBF9F5),
            Color(0xFFF5F1E9),
            Color(0xFFEDE7DC),
          ],
        );

  /// Section / panel container gradient to distinguish content zones
  LinearGradient get sectionGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.6, 1.0],
          colors: [
            Color(0xFF1B2138),
            Color(0xFF151A2C),
            Color(0xFF101525),
          ],
        )
      : const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.6, 1.0],
          colors: [
            Color(0xFFFFFFFF),
            Color(0xFFF9F6F0),
            Color(0xFFF2ECE2),
          ],
        );

  /// Secondary elevated card / drawer tonal gradient
  LinearGradient get elevatedCardGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF222942),
            Color(0xFF171D31),
          ],
        )
      : const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFFFFFFFF),
            Color(0xFFF6F2EA),
          ],
        );

  /// Soft radial ambient spotlight for hero / focal areas
  RadialGradient get heroGlowGradient => isDark
      ? RadialGradient(
          center: const Alignment(0.0, -0.25),
          radius: 0.85,
          colors: [
            const Color(0xFF232C4B).withValues(alpha: 0.42),
            const Color(0xFF131A33).withValues(alpha: 0.16),
            const Color(0xFF0A0F20).withValues(alpha: 0.0),
          ],
          stops: const [0.0, 0.5, 1.0],
        )
      : RadialGradient(
          center: const Alignment(0.0, -0.25),
          radius: 0.85,
          colors: [
            const Color(0xFFFFFFFF).withValues(alpha: 0.85),
            const Color(0xFFF6F2EA).withValues(alpha: 0.35),
            const Color(0xFFF2EFE9).withValues(alpha: 0.0),
          ],
          stops: const [0.0, 0.5, 1.0],
        );

  // Query tiers (Subtle, refined monochrome palette matching Warm Sand & Slate)
  static const queryCold = Color(0xFF84878F);
  static const queryWarm = Color(0xFFCBC1B4);
  static const queryHot = Color(0xFFE4DFD6);

  // Confidence tiers
  static const confConfirmed = Color(0xFFCBC1B4);
  static const confUncertain = Color(0xFF84878F);
  static const confInsufficient = Color(0xFF6B686A);

  // Entity types
  static const entityService = Color(0xFF6EC8B8);
  static const entityDecision = Color(0xFFE8A455);
  static const entityCommit = Color(0xFFD4A843);
  static const entityTicket = Color(0xFFD4909A);
  static const entityThread = Color(0xFFD4725A);
  static const entityPerson = Color(0xFFA89070);
}

class UnoTypography {
  static TextStyle displaySerif({
    required UnoPalette palette,
    double fontSize = 26,
    FontWeight fontWeight = FontWeight.w400,
    double lineHeight = 1.2,
    FontStyle fontStyle = FontStyle.normal,
  }) {
    return GoogleFonts.instrumentSerif(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: palette.text,
      fontStyle: fontStyle,
      height: lineHeight,
    );
  }

  static TextStyle brandSerif({
    required UnoPalette palette,
    double fontSize = 17,
    FontWeight fontWeight = FontWeight.w400,
  }) {
    return GoogleFonts.youngSerif(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: palette.text,
      letterSpacing: -0.2,
    );
  }

  static TextStyle mono({
    required Color color,
    double fontSize = 11,
    FontWeight fontWeight = FontWeight.normal,
    double letterSpacing = 0.5,
    double? height,
  }) {
    return GoogleFonts.ibmPlexMono(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      letterSpacing: letterSpacing,
      height: height,
    );
  }

  static TextStyle body({
    required Color color,
    double fontSize = 14,
    FontWeight fontWeight = FontWeight.normal,
    double height = 1.5,
  }) {
    return GoogleFonts.inter(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
    );
  }
}
