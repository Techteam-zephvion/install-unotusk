import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:window_manager/window_manager.dart';
import '../theme/app_theme.dart';
import 'desktop_window_controls.dart';

class TopNavBar extends StatelessWidget {
  final UnoPalette palette;
  final bool isDark;
  final int unreadCount;
  final bool notificationsOpen;
  final VoidCallback onToggleNotifications;
  final VoidCallback onToggleTheme;
  final bool showSidebarToggle;
  final VoidCallback? onToggleSidebar;
  final String? projectName;
  final String? repoFullName;
  final String? branchName;
  final VoidCallback? onBackToProjects;

  const TopNavBar({
    super.key,
    required this.palette,
    required this.isDark,
    required this.unreadCount,
    required this.notificationsOpen,
    required this.onToggleNotifications,
    required this.onToggleTheme,
    this.showSidebarToggle = false,
    this.onToggleSidebar,
    this.projectName,
    this.repoFullName,
    this.branchName,
    this.onBackToProjects,
  });

  @override
  Widget build(BuildContext context) {
    final rawName = (repoFullName != null && repoFullName!.isNotEmpty)
        ? repoFullName!
        : ((projectName != null && projectName!.isNotEmpty)
            ? projectName!
            : 'Workspace');
    final repoName = formatDisplayTitle(rawName);
    final isDesktop =
        !kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS);
    final isWindowsOrLinux = !kIsWeb && (Platform.isWindows || Platform.isLinux);
    final isDark = palette.isDark;

    return Container(
      height: 54,
      color: Colors.transparent,
      padding: EdgeInsets.only(
        left: showSidebarToggle ? 10 : 20,
        right: isWindowsOrLinux ? 0 : 22,
      ),
      child: Row(
        children: [
          // ── Left: Sidebar toggle + Creative Minimal Repository Title ──
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (showSidebarToggle && onToggleSidebar != null)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _TopBarIconButton(
                    icon: LucideIcons.menu,
                    size: 16,
                    palette: palette,
                    tooltip: 'Toggle sidebar',
                    onTap: onToggleSidebar!,
                  ),
                ),
              _TopBarRepoTitle(
                repoName: repoName,
                palette: palette,
                isDark: isDark,
                onTap: onBackToProjects,
              ),
            ],
          ),

          // ── Middle: Draggable window title bar area ──
          Expanded(
            child: isDesktop
                ? const DragToMoveArea(
                    child: SizedBox(
                      height: 54,
                      width: double.infinity,
                    ),
                  )
                : const SizedBox(height: 54),
          ),

          // ── Right: Uniform Notification, Theme, and Desktop Window Controls ──
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  _TopBarIconButton(
                    icon: LucideIcons.bell,
                    size: 14,
                    palette: palette,
                    isActive: notificationsOpen,
                    tooltip: 'Notifications',
                    onTap: onToggleNotifications,
                  ),
                  if (unreadCount > 0)
                    Positioned(
                      top: 5,
                      right: 5,
                      child: Container(
                        width: 6.5,
                        height: 6.5,
                        decoration: BoxDecoration(
                          color: palette.accent,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: palette.bgSurface,
                            width: 1.3,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(width: 8),
              _TopBarIconButton(
                icon: isDark ? LucideIcons.moon : LucideIcons.sun,
                size: 14,
                palette: palette,
                rotateTurns: isDark ? 0.0 : 0.5,
                tooltip: isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode',
                onTap: onToggleTheme,
              ),

              // Desktop Window Controls (Minimize, Maximize/Restore, Close - Windows & Linux only)
              if (isWindowsOrLinux) ...[
                const SizedBox(width: 10),
                DesktopWindowControls(palette: palette, height: 54),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

/// Creative, minimal editorial repository title mark for the top bar.
class _TopBarRepoTitle extends StatefulWidget {
  final String repoName;
  final UnoPalette palette;
  final bool isDark;
  final VoidCallback? onTap;

  const _TopBarRepoTitle({
    required this.repoName,
    required this.palette,
    required this.isDark,
    this.onTap,
  });

  @override
  State<_TopBarRepoTitle> createState() => _TopBarRepoTitleState();
}

class _TopBarRepoTitleState extends State<_TopBarRepoTitle> {
  bool _hovered = false;
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final hoverBase = widget.isDark ? p.accent : p.text;

    final titleWidget = MouseRegion(
      cursor: widget.onTap != null
          ? SystemMouseCursors.click
          : SystemMouseCursors.basic,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() {
        _hovered = false;
        _pressed = false;
      }),
      child: GestureDetector(
        onTap: widget.onTap,
        onTapDown:
            widget.onTap != null ? (_) => setState(() => _pressed = true) : null,
        onTapUp: widget.onTap != null
            ? (_) => setState(() => _pressed = false)
            : null,
        onTapCancel:
            widget.onTap != null ? () => setState(() => _pressed = false) : null,
        behavior: HitTestBehavior.opaque,
        child: AnimatedScale(
          scale: _pressed ? 0.98 : 1.0,
          duration: const Duration(milliseconds: 95),
          curve: Curves.easeOutCubic,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 170),
            curve: Curves.easeOutCubic,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: hoverBase.withValues(alpha: _hovered ? 0.06 : 0.0),
              borderRadius: BorderRadius.circular(9),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Simple modern two-tone folder mark
                AnimatedScale(
                  scale: _hovered ? 1.06 : 1.0,
                  duration: const Duration(milliseconds: 160),
                  curve: Curves.easeOutCubic,
                  child: _ModernFolderGlyph(
                    color: p.accent,
                    size: 17,
                  ),
                ),
                const SizedBox(width: 9),
                // Editorial serif repository name
                Text(
                  widget.repoName,
                  style: UnoTypography.headingSerif(
                    color: p.text,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    height: 1.15,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );

    if (widget.onTap != null) {
      return Tooltip(
        message: 'Switch project',
        child: titleWidget,
      );
    }
    return titleWidget;
  }
}

/// Minimal, modern two-tone rounded folder mark aligned to the Unotusk theme.
class _ModernFolderGlyph extends StatelessWidget {
  final Color color;
  final double size;

  const _ModernFolderGlyph({
    required this.color,
    this.size = 17,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size * 0.84,
      child: CustomPaint(
        painter: _ModernFolderPainter(color: color),
      ),
    );
  }
}

class _ModernFolderPainter extends CustomPainter {
  final Color color;

  const _ModernFolderPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Back folder tab silhouette (muted tone)
    final backPath = Path()
      ..moveTo(w * 0.14, 0)
      ..lineTo(w * 0.38, 0)
      ..quadraticBezierTo(w * 0.45, 0, w * 0.49, h * 0.13)
      ..lineTo(w * 0.52, h * 0.20)
      ..lineTo(w * 0.86, h * 0.20)
      ..quadraticBezierTo(w, h * 0.20, w, h * 0.35)
      ..lineTo(w, h * 0.84)
      ..quadraticBezierTo(w, h, w * 0.86, h)
      ..lineTo(w * 0.14, h)
      ..quadraticBezierTo(0, h, 0, h * 0.84)
      ..lineTo(0, h * 0.16)
      ..quadraticBezierTo(0, 0, w * 0.14, 0)
      ..close();

    canvas.drawPath(
      backPath,
      Paint()
        ..color = color.withValues(alpha: 0.42)
        ..style = PaintingStyle.fill,
    );

    // Front rounded body (crisp primary tone)
    final frontRect = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, h * 0.27, w, h * 0.73),
      Radius.circular(h * 0.20),
    );

    canvas.drawRRect(
      frontRect,
      Paint()
        ..color = color
        ..style = PaintingStyle.fill,
    );
  }

  @override
  bool shouldRepaint(covariant _ModernFolderPainter oldDelegate) =>
      oldDelegate.color != color;
}

class _TopBarIconButton extends StatefulWidget {
  final IconData icon;
  final double size;
  final UnoPalette palette;
  final bool isActive;
  final double rotateTurns;
  final String tooltip;
  final VoidCallback onTap;

  const _TopBarIconButton({
    required this.icon,
    required this.size,
    required this.palette,
    this.isActive = false,
    this.rotateTurns = 0.0,
    required this.tooltip,
    required this.onTap,
  });

  @override
  State<_TopBarIconButton> createState() => _TopBarIconButtonState();
}

class _TopBarIconButtonState extends State<_TopBarIconButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final active = widget.isActive;
    final bg = active
        ? p.accent.withValues(alpha: 0.12)
        : (_hovered
            ? p.bgInteractive
            : (p.isDark
                ? const Color(0xFF141C2E).withValues(alpha: 0.65)
                : const Color(0xFFFFFFFF).withValues(alpha: 0.72)));
    final border = active
        ? p.accent.withValues(alpha: 0.45)
        : (_hovered
            ? p.accent.withValues(alpha: p.isDark ? 0.28 : 0.24)
            : p.div.withValues(alpha: 0.8));

    return Tooltip(
      message: widget.tooltip,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          behavior: HitTestBehavior.opaque,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            curve: Curves.easeOutCubic,
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: bg,
              border: Border.all(color: border, width: 1),
              borderRadius: BorderRadius.circular(8),
            ),
            alignment: Alignment.center,
            child: AnimatedRotation(
              turns: widget.rotateTurns,
              duration: const Duration(milliseconds: 240),
              curve: Curves.easeOutCubic,
              child: Icon(
                widget.icon,
                size: widget.size,
                color: active
                    ? p.accent
                    : (_hovered ? p.accent : p.textSec),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
