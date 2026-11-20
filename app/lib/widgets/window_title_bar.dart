import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';
import '../theme/app_theme.dart';
import 'desktop_window_controls.dart';
import 'unotusk_workspace_brand.dart';

/// Custom window title bar for standalone screens like AuthScreen.
/// Displays branding on the left, draggable middle, and DesktopWindowControls on the right.
class WindowTitleBar extends StatelessWidget {
  final UnoPalette palette;

  /// Optional trailing widgets shown next to the brand (e.g. OIDC badge).
  final Widget? trailing;

  final double height;

  /// When true, omits the solid background fill so full-bleed artwork shows through.
  final bool transparent;

  const WindowTitleBar({
    super.key,
    required this.palette,
    this.trailing,
    this.height = 54.0,
    this.transparent = false,
  });

  @override
  Widget build(BuildContext context) {
    if (kIsWeb || (!Platform.isWindows && !Platform.isLinux && !Platform.isMacOS)) {
      return const SizedBox.shrink();
    }

    final isDark = palette.isDark;
    final isMacOS = !kIsWeb && Platform.isMacOS;

    return Container(
      height: height,
      color: transparent ? Colors.transparent : palette.bgBase,
      padding: EdgeInsets.only(left: isMacOS ? 78.0 : 20.0),
      child: Row(
        children: [
          // ── Logo + Brand Name + Quiet Workspace Tag ──
          UnotuskWorkspaceBrand(
            palette: palette,
            isDark: isDark,
          ),

          // ── Optional trailing (e.g. badge) ──
          if (trailing != null) ...[
            const SizedBox(width: 10),
            trailing!,
          ],

          // ── Draggable Area ──
          const Expanded(
            child: DragToMoveArea(
              child: SizedBox(
                height: double.infinity,
                width: double.infinity,
              ),
            ),
          ),

          // ── Window Controls (Windows / Linux only) ──
          if (!isMacOS)
            DesktopWindowControls(palette: palette, height: height),
        ],
      ),
    );
  }
}
