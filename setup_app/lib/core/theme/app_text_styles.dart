import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';
import 'uno_palette.dart';

class UnoTypography {
  static TextStyle displaySerif({
    required UnoPalette palette,
    double fontSize = 22,
    FontWeight fontWeight = FontWeight.w400,
    double lineHeight = 1.25,
    FontStyle fontStyle = FontStyle.normal,
  }) {
    return GoogleFonts.youngSerif(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: palette.text,
      fontStyle: fontStyle,
      letterSpacing: -0.2,
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
    double fontSize = 13.5,
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

class AppTextStyles {
  // Editorial Serif Headers (matching Employee App / Image 3 & Image 5)
  static TextStyle get h1 => GoogleFonts.youngSerif(
        fontSize: 22,
        fontWeight: FontWeight.w400,
        color: AppColors.slate800,
        letterSpacing: -0.2,
      );

  static TextStyle get h2 => GoogleFonts.youngSerif(
        fontSize: 18,
        fontWeight: FontWeight.w400,
        color: AppColors.slate800,
        letterSpacing: -0.2,
      );

  static TextStyle get h3 => GoogleFonts.youngSerif(
        fontSize: 15,
        fontWeight: FontWeight.w400,
        color: AppColors.slate800,
      );

  // Modern Clean Inter Body Text
  static TextStyle get bodyMedium => GoogleFonts.inter(
        fontSize: 13.5,
        fontWeight: FontWeight.w400,
        color: AppColors.slate700,
        height: 1.45,
      );

  static TextStyle get bodySmall => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.slate500,
        height: 1.35,
      );

  static TextStyle get label => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: AppColors.slate600,
        letterSpacing: 0.2,
      );

  // Clean Monospace Typography
  static TextStyle get code => GoogleFonts.ibmPlexMono(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.slate800,
        letterSpacing: 0.3,
      );

  // Context-aware styles that dynamically adapt to active theme
  static TextStyle h1Of(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.displaySerif(palette: palette, fontSize: 22);
  }

  static TextStyle h2Of(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.brandSerif(palette: palette, fontSize: 18);
  }

  static TextStyle h3Of(BuildContext context) {
    final palette = UnoPalette.of(context);
    return UnoTypography.brandSerif(palette: palette, fontSize: 15);
  }

  static TextStyle bodyMediumOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return GoogleFonts.inter(
      fontSize: 13.5,
      fontWeight: FontWeight.w400,
      color: palette.text,
      height: 1.45,
    );
  }

  static TextStyle bodySmallOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return GoogleFonts.inter(
      fontSize: 12,
      fontWeight: FontWeight.w400,
      color: palette.textSec,
      height: 1.35,
    );
  }

  static TextStyle labelOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return GoogleFonts.inter(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      color: palette.textSec,
      letterSpacing: 0.2,
    );
  }

  static TextStyle codeOf(BuildContext context) {
    final palette = UnoPalette.of(context);
    return GoogleFonts.ibmPlexMono(
      fontSize: 12,
      fontWeight: FontWeight.w400,
      color: palette.text,
      letterSpacing: 0.3,
    );
  }
}
