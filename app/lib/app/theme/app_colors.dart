import 'package:flutter/material.dart';

class AppColors {
  // Unotusk Dark Palette (Exact Obsidian Navy & Warm Sand)
  static const Color bgBase = Color(0xFF0A0F20);
  static const Color bgSurface = Color(0xFF161A29);
  static const Color bgElevated = Color(0xFF1E2336);
  static const Color divider = Color(0xFF2E313C);

  // Brand Signature Accent (Warm Sand)
  static const Color primary = Color(0xFFCBC1B4);
  static const Color accent = Color(0xFFCBC1B4);
  static const Color accentHover = Color(0xFFDFD7CC);
  static const Color accentMuted = Color(0x24CBC1B4); // 14% opacity
  static const Color primaryMuted = Color(0x24CBC1B4); // Compatibility alias
  static const Color output = Color(0xFFCBC1B4);

  // Status & Signal System
  static const Color live = Color(0xFF22C55E);       // Live / Active signal (green)
  static const Color liveBg = Color(0x1F22C55E);
  static const Color confirmed = Color(0xFFCBC1B4);  // Confirmed tag / signal
  static const Color confirmedBg = Color(0x1FCBC1B4);
  static const Color inferred = Color(0xFF84878F);   // Inferred tag / signal
  static const Color inferredBg = Color(0x1F84878F);
  static const Color neutral = Color(0xFF84878F);    // Secondary neutral signal
  static const Color neutralBg = Color(0x1F84878F);

  // Thinking temperature modes (Minimal, clean, non-chapri)
  static const Color modeHot = Color(0xFFCBC1B4);
  static const Color modeWarm = Color(0xFFCBC1B4);
  static const Color modeCold = Color(0xFF84878F);

  // Standard status mappings
  static const Color success = live;
  static const Color successBg = liveBg;
  static const Color successBorder = Color(0x4022C55E);

  static const Color warning = Color(0xFFCBC1B4);
  static const Color warningBg = Color(0x1FCBC1B4);
  static const Color warningBorder = Color(0x40CBC1B4);

  static const Color error = Color(0xFFE05A5A);
  static const Color errorBg = Color(0x1FE05A5A);
  static const Color errorBorder = Color(0x40E05A5A);

  static const Color info = Color(0xFF84878F);
  static const Color infoBg = Color(0x1F84878F);
  static const Color infoBorder = Color(0x4084878F);

  // Typography Tokens
  static const Color textPrimary = Color(0xFFFFFFFF);   // Pure white
  static const Color textSecondary = Color(0xFF84878F); // Cool slate
  static const Color textMuted = Color(0xFF6B686A);

  // Slate compatibility aliases (for existing widgets before complete migration)
  static const Color slate50 = bgBase;
  static const Color slate100 = bgSurface;
  static const Color slate200 = divider;
  static const Color slate300 = Color(0xFF2E313C);
  static const Color slate400 = textMuted;
  static const Color slate500 = textSecondary;
  static const Color slate600 = Color(0xFF84878F);
  static const Color slate700 = Color(0xFFCBC1B4);
  static const Color slate800 = Color(0xFFDFD7CC);
  static const Color slate900 = textPrimary;
  static const Color slate950 = Color(0xFFFFFFFF);

  // Light Palette Tokens
  static const Color bgBaseLight = Color(0xFFF2EFE9);
  static const Color bgSurfaceLight = Color(0xFFF5F2EB);
  static const Color bgElevatedLight = Color(0xFFFFFFFF);
  static const Color dividerLight = Color(0xFFE4DFD6);
  static const Color textPrimaryLight = Color(0xFF0A0F20);
  static const Color textSecondaryLight = Color(0xFF6B686A);
}
