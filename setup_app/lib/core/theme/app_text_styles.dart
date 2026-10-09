import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';

class AppTextStyles {
  static TextStyle get h1 => GoogleFonts.youngSerif(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: AppColors.slate900,
        letterSpacing: -0.2,
      );

  static TextStyle get h2 => GoogleFonts.youngSerif(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.slate900,
        letterSpacing: -0.1,
      );

  static TextStyle get h3 => GoogleFonts.youngSerif(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.slate900,
      );

  static TextStyle get bodyMedium => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        color: AppColors.slate700,
        height: 1.4,
      );

  static TextStyle get bodySmall => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.slate500,
        height: 1.3,
      );

  static TextStyle get label => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: AppColors.slate700,
      );

  static TextStyle get code => GoogleFonts.ibmPlexMono(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.slate800,
      );
}
