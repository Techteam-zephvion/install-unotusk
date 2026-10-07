import 'package:flutter/material.dart';

class AppColors {
  // Unotusk Dark Palette (Warm Editorial Dark — Default)
  static const Color bgBase = Color(0xFF181816);
  static const Color bgSurface = Color(0xFF21211E);
  static const Color bgElevated = Color(0xFF2A2A26);
  static const Color divider = Color(0xFF33332E);

  // Brand Signature Accent (Warm Terracotta / Burnt Orange)
  static const Color primary = Color(0xFFDA7756);
  static const Color accent = Color(0xFFDA7756);
  static const Color accentHover = Color(0xFFC86646);
  static const Color accentMuted = Color(0x24DA7756); // 14% opacity
  static const Color primaryMuted = Color(0x24DA7756); // Compatibility alias
  static const Color output = Color(0xFFE59866);

  // Status & Signal System
  static const Color live = Color(0xFF52B788);       // Live / Active signal (green)
  static const Color liveBg = Color(0x1F52B788);
  static const Color confirmed = Color(0xFFE07A5F);  // Confirmed tag / signal
  static const Color confirmedBg = Color(0x1FE07A5F);
  static const Color inferred = Color(0xFFDA7756);   // Inferred tag / signal
  static const Color inferredBg = Color(0x1FDA7756);
  static const Color neutral = Color(0xFF68A090);    // Secondary neutral signal (teal/sage)
  static const Color neutralBg = Color(0x1F68A090);

  // Thinking temperature modes
  static const Color modeHot = Color(0xFFE05A5A);
  static const Color modeWarm = Color(0xFFE8A455);
  static const Color modeCold = Color(0xFF6EC8B8);

  // Standard status mappings
  static const Color success = live;
  static const Color successBg = liveBg;
  static const Color successBorder = Color(0x4052B788);

  static const Color warning = Color(0xFFE59866);
  static const Color warningBg = Color(0x1FE59866);
  static const Color warningBorder = Color(0x40E59866);

  static const Color error = Color(0xFFE05A5A);
  static const Color errorBg = Color(0x1FE05A5A);
  static const Color errorBorder = Color(0x40E05A5A);

  static const Color info = Color(0xFF68A090);
  static const Color infoBg = Color(0x1F68A090);
  static const Color infoBorder = Color(0x4068A090);

  // Typography Tokens
  static const Color textPrimary = Color(0xFFF0EFEA);   // Parchment warm white
  static const Color textSecondary = Color(0xFFA3A199); // Ink wash muted
  static const Color textMuted = Color(0xFF706E67);

  // Slate compatibility aliases (for existing widgets before complete migration)
  static const Color slate50 = bgBase;
  static const Color slate100 = bgSurface;
  static const Color slate200 = divider;
  static const Color slate300 = Color(0xFF42423D);
  static const Color slate400 = textMuted;
  static const Color slate500 = textSecondary;
  static const Color slate600 = Color(0xFFBEBCB5);
  static const Color slate700 = Color(0xFFD4D3CD);
  static const Color slate800 = Color(0xFFE8E7E1);
  static const Color slate900 = textPrimary;
  static const Color slate950 = Color(0xFFFFFFFF);

  // Light Palette Tokens
  static const Color bgBaseLight = Color(0xFFFAF8F5);
  static const Color bgSurfaceLight = Color(0xFFF3EFE6);
  static const Color bgElevatedLight = Color(0xFFFFFFFF);
  static const Color dividerLight = Color(0xFFE6E5DF);
  static const Color textPrimaryLight = Color(0xFF1D1C1A);
  static const Color textSecondaryLight = Color(0xFF706E6B);
}
