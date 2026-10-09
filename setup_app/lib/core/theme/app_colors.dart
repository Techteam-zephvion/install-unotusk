import 'package:flutter/material.dart';

class AppColors {
  // Mapped to UnoPalette.dark for Warm Dark Figma design system
  
  // Neutral Slate Palette -> Uno Dark Palette Neutrals
  static const Color slate50 = Color(0xFF181816);   // bgBase
  static const Color slate100 = Color(0xFF20201D);  // bgSurface
  static const Color slate200 = Color(0xFF2E2E2A);  // div
  static const Color slate300 = Color(0xFF2E2E2A);  // div
  static const Color slate400 = Color(0xFF8E8D88);  // textSec
  static const Color slate500 = Color(0xFF8E8D88);  // textSec
  static const Color slate600 = Color(0xFF8E8D88);  // textSec
  static const Color slate700 = Color(0xFFEDEDEB);  // text
  static const Color slate800 = Color(0xFFEDEDEB);  // text
  static const Color slate900 = Color(0xFFEDEDEB);  // text
  static const Color slate950 = Color(0xFFFFFFFF);  // brightest text
  
  // Primary Accent -> Uno Dark Accent (Warm Orange)
  static const Color primary = Color(0xFFDA7756);       // accent
  static const Color primaryHover = Color(0xFFE59866);  // output
  static const Color primaryMuted = Color(0xFF282824);  // bgElevated

  // Status Colors -> Uno Dark Tiers
  static const Color success = Color(0xFF22C55E);       // live
  static const Color successBg = Color(0xFF20201D);     // bgSurface
  static const Color successBorder = Color(0xFF2E2E2A); // div

  static const Color warning = Color(0xFFE8A455);       // queryWarm
  static const Color warningBg = Color(0xFF20201D);     // bgSurface
  static const Color warningBorder = Color(0xFF2E2E2A); // div

  static const Color error = Color(0xFFD4725A);         // queryHot
  static const Color errorBg = Color(0xFF20201D);       // bgSurface
  static const Color errorBorder = Color(0xFF2E2E2A);   // div

  static const Color info = Color(0xFF6EC8B8);          // queryCold
  static const Color infoBg = Color(0xFF20201D);        // bgSurface
  static const Color infoBorder = Color(0xFF2E2E2A);    // div
}
