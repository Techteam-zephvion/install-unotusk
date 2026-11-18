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
    bgBase: Color(0xFF0B1020),
    bgSurface: Color(0xFF101729),
    bgElevated: Color(0xFF171F32),
    div: Color(0xFF242D42),
    accent: Color(0xFFE9DFD0),
    output: Color(0xFFC8BCA9),
    live: Color(0xFF22C55E),
    confirmed: Color(0xFFE9DFD0),
    inferred: Color(0xFFA5A5AE),
    neutral: Color(0xFF777D8B),
    text: Color(0xFFF4F1EC),
    textSec: Color(0xFFA5A5AE),
  );

  static const light = UnoPalette(
    bgBase: Color(0xFFF2EFE9),
    bgSurface: Color(0xFFF5F2EB),
    bgElevated: Color(0xFFFFFFFF),
    div: Color(0xFFE4DFD6),
    accent: Color(0xFF0B1020),
    output: Color(0xFF0B1020),
    live: Color(0xFF22C55E),
    confirmed: Color(0xFF0B1020),
    inferred: Color(0xFF6B686A),
    neutral: Color(0xFF6B686A),
    text: Color(0xFF0B1020),
    textSec: Color(0xFF656369),
  );

  bool get isDark => bgBase.computeLuminance() < 0.2;

  Color get surface => bgSurface;
  Color get warn => const Color(0xFFE59866);

  // Semantic surface & accent tokens for calm, cohesive hierarchy
  Color get bgSidebar =>
      isDark ? const Color(0xFF0D1425) : const Color(0xFFF5F1E9);
  Color get bgInteractive =>
      isDark ? const Color(0xFF20283B) : const Color(0xFFEAE3D8);
  Color get textMuted =>
      isDark ? const Color(0xFF777D8B) : const Color(0xFF837E7A);
  Color get accentMuted =>
      isDark ? const Color(0xFFC8BCA9) : const Color(0xFF3E465E);

  // ── Restrained Tonal Depth System (Strictly Within Midnight Navy / Warm Ivory) ──

  /// Main page canvas gradient: calm, unified midnight navy / warm ivory tone
  LinearGradient get pageGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.55, 1.0],
          colors: [
            Color(0xFF0B1020),
            Color(0xFF0C1223),
            Color(0xFF0F162B),
          ],
        )
      : const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.55, 1.0],
          colors: [
            Color(0xFFFAF8F4),
            Color(0xFFF2EFE9),
            Color(0xFFEBE4D9),
          ],
        );

  /// Sidebar navigation calm vertical surface
  LinearGradient get sidebarGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          stops: [0.0, 0.55, 1.0],
          colors: [
            Color(0xFF0E1527),
            Color(0xFF0D1425),
            Color(0xFF0B1121),
          ],
        )
      : const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          stops: [0.0, 0.55, 1.0],
          colors: [
            Color(0xFFF8F5EE),
            Color(0xFFF4EFE7),
            Color(0xFFEDE6DC),
          ],
        );

  /// Top navigation bar: slightly elevated midnight / ivory surface
  LinearGradient get headerGradient => isDark
      ? const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          stops: [0.0, 0.5, 1.0],
          colors: [
            Color(0xFF101729),
            Color(0xFF11192C),
            Color(0xFF101729),
          ],
        )
      : const LinearGradient(
          begin: Alignment.centerLeft,
          end: Alignment.centerRight,
          stops: [0.0, 0.5, 1.0],
          colors: [
            Color(0xFFFAF8F4),
            Color(0xFFF6F2EA),
            Color(0xFFF3EEE5),
          ],
        );

  /// Section / panel container gradient to distinguish content zones
  LinearGradient get sectionGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.6, 1.0],
          colors: [
            Color(0xFF171F32),
            Color(0xFF131B2D),
            Color(0xFF101729),
          ],
        )
      : const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          stops: [0.0, 0.6, 1.0],
          colors: [
            Color(0xFFFFFFFF),
            Color(0xFFFAF7F1),
            Color(0xFFF3EDE3),
          ],
        );

  /// Secondary elevated card / composer surface
  LinearGradient get elevatedCardGradient => isDark
      ? const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF171F32),
            Color(0xFF141B2D),
          ],
        )
      : const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFFFFFFFF),
            Color(0xFFFAF7F2),
          ],
        );

  /// Subtle ambient glow for focal areas (whisper-quiet, never noisy)
  RadialGradient get heroGlowGradient => isDark
      ? RadialGradient(
          center: const Alignment(0.0, -0.30),
          radius: 0.90,
          colors: [
            const Color(0xFF18223A).withValues(alpha: 0.30),
            const Color(0xFF0E1529).withValues(alpha: 0.12),
            const Color(0xFF0B1020).withValues(alpha: 0.0),
          ],
          stops: const [0.0, 0.55, 1.0],
        )
      : RadialGradient(
          center: const Alignment(0.0, -0.30),
          radius: 0.90,
          colors: [
            const Color(0xFFFFFFFF).withValues(alpha: 0.72),
            const Color(0xFFF6F2EA).withValues(alpha: 0.30),
            const Color(0xFFF2EFE9).withValues(alpha: 0.0),
          ],
          stops: const [0.0, 0.55, 1.0],
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

  static TextStyle headingSerif({
    required Color color,
    double fontSize = 20,
    FontWeight fontWeight = FontWeight.w600,
    double height = 1.32,
  }) {
    return GoogleFonts.lora(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: height,
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

/// Formats repository slugs or raw project names into consistent Title Case
/// across all screens (e.g. "Techteam-zephvion/swastha-yoga" -> "Swastha Yoga").
String formatDisplayTitle(String raw) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) return '';
  final slashIdx = trimmed.lastIndexOf('/');
  final base = (slashIdx >= 0 && slashIdx < trimmed.length - 1)
      ? trimmed.substring(slashIdx + 1).trim()
      : trimmed;
  final words = base
      .replaceAll(RegExp(r'[-_]+'), ' ')
      .split(RegExp(r'\s+'))
      .where((w) => w.isNotEmpty);
  return words.map((word) {
    // Preserve intentional all-caps acronyms (e.g. API, MVP, OIDC)
    if (word.length > 1 && word == word.toUpperCase()) return word;
    if (word.length == 1) return word.toUpperCase();
    return '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}';
  }).join(' ');
}
