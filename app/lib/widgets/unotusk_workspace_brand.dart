import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import 'unotusk_logo.dart';

/// Standard unified Unotusk Workspace brand lockup.
/// Renders: [Elephant Logo]  Unotusk  |  WORKSPACE
class UnotuskWorkspaceBrand extends StatelessWidget {
  final UnoPalette palette;
  final bool isDark;
  final VoidCallback? onTap;
  final double logoSize;
  final double fontSize;
  final double workspaceFontSize;
  final double dividerHeight;
  final Color? color;

  const UnotuskWorkspaceBrand({
    super.key,
    required this.palette,
    required this.isDark,
    this.onTap,
    this.logoSize = 22.0,
    this.fontSize = 15.5,
    this.workspaceFontSize = 10.5,
    this.dividerHeight = 14.0,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final brandColor = color ??
        (isDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20));

    Widget content = Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        UnotuskLogo(size: logoSize, onDark: isDark),
        const SizedBox(width: 8),
        Text(
          'Unotusk',
          style: GoogleFonts.youngSerif(
            color: brandColor,
            fontSize: fontSize,
            letterSpacing: -0.2,
          ),
        ),
        Container(
          width: 1,
          height: dividerHeight,
          margin: const EdgeInsets.symmetric(horizontal: 12),
          color: brandColor.withValues(alpha: 0.20),
        ),
        Text(
          'WORKSPACE',
          style: GoogleFonts.inter(
            color: brandColor.withValues(alpha: 0.62),
            fontSize: workspaceFontSize,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.5,
          ),
        ),
      ],
    );

    if (onTap != null) {
      content = MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: onTap,
          behavior: HitTestBehavior.opaque,
          child: content,
        ),
      );
    }

    return content;
  }
}
