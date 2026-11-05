import 'package:flutter/material.dart';
import 'uno_palette.dart';

class AppColors {
  // Brand Terracotta Palette (Image 3 Employee App)
  static const Color primary = Color(0xFFDA7756);       // Warm terracotta accent
  static const Color primaryHover = Color(0xFFE59866);  // Hover state
  static const Color primaryMuted = Color(0xFF282824);  // Elevated container
  static const Color primaryLight = Color(0xFFE07A5F);

  // Dark Neutrals (UnoPalette.dark)
  static const Color slate50 = Color(0xFF181816);   // bgBase (dark canvas)
  static const Color slate100 = Color(0xFF20201D);  // bgSurface (dark card)
  static const Color slate200 = Color(0xFF282824);  // bgElevated (nested surfaces)
  static const Color slate300 = Color(0xFF2E2E2A);  // div (subtle borders)
  static const Color slate400 = Color(0xFF706E6B);  // muted text
  static const Color slate500 = Color(0xFF8E8D88);  // textSec
  static const Color slate600 = Color(0xFFA09F9A);  // secondary text
  static const Color slate700 = Color(0xFFD4D3CF);  // primary body
  static const Color slate800 = Color(0xFFEDEDEB);  // text (crisp light)
  static const Color slate900 = Color(0xFFFFFFFF);  // pure white heading
  static const Color slate950 = Color(0xFFFFFFFF);  // brightest text

  // Status Colors
  static const Color success = Color(0xFF22C55E);       // emerald live
  static const Color successBg = Color(0xFF1C2B22);     // dark green bg
  static const Color successBorder = Color(0xFF244430); // green border

  static const Color warning = Color(0xFFE8A455);       // warm amber
  static const Color warningBg = Color(0xFF2C2418);     // dark amber bg
  static const Color warningBorder = Color(0xFF48361E); // amber border

  static const Color error = Color(0xFFD4725A);         // hot terracotta error
  static const Color errorBg = Color(0xFF2B1D19);       // dark red bg
  static const Color errorBorder = Color(0xFF4A2B23);   // red border

  static const Color info = Color(0xFF6EC8B8);          // cold query teal
  static const Color infoBg = Color(0xFF1B2926);        // dark teal bg
  static const Color infoBorder = Color(0xFF27423D);    // teal border

  // Light Theme equivalents when needed directly
  static const Color lightBgBase = Color(0xFFF7F6F3);
  static const Color lightBgSurface = Color(0xFFFFFFFF);
  static const Color lightBgElevated = Color(0xFFEFECE6);
  static const Color lightDiv = Color(0xFFE8E5DF);
  static const Color lightText = Color(0xFF1C1917);
  static const Color lightTextSec = Color(0xFF706E6B);

  // Helper to obtain current palette from context
  static UnoPalette palette(BuildContext context) => UnoPalette.of(context);
}
