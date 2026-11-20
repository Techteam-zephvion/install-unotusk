import 'package:flutter/material.dart';

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

  /// Dark Midnight Navy & Warm Ivory (Exact 1:1 match with Employee App)
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

  /// Warm Sand & Paper Light
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
  Color get error => const Color(0xFFE06C75);

  Color get bgSidebar =>
      isDark ? const Color(0xFF0D1425) : const Color(0xFFF5F1E9);
  Color get bgInteractive =>
      isDark ? const Color(0xFF20283B) : const Color(0xFFEAE3D8);
  Color get textMuted =>
      isDark ? const Color(0xFF777D8B) : const Color(0xFF837E7A);
  Color get accentMuted =>
      isDark ? const Color(0xFFC8BCA9) : const Color(0xFF3E465E);

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

  /// Subtle ambient glow for focal areas
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

  // Helper method to retrieve from BuildContext
  static UnoPalette of(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return isDark ? dark : light;
  }
}
