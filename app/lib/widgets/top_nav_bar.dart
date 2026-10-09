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
    final displayName = repoFullName ??
        ((projectName != null && projectName!.isNotEmpty)
            ? 'Kushall-07/$projectName'
            : 'Kushall-07/SyncGuard');
    final displayBranch = branchName ?? 'main';
    final isDesktop =
        !kIsWeb && (Platform.isWindows || Platform.isLinux || Platform.isMacOS);

    return Container(
      height: 52,
      padding: EdgeInsets.only(
        left: showSidebarToggle ? 10 : 20,
        right: isDesktop ? 0 : 24,
      ),
      color: Colors.transparent,
      child: Row(
        children: [
          // ── Left: Sidebar toggle + Project Switcher ──
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (showSidebarToggle && onToggleSidebar != null)
                InkWell(
                  onTap: onToggleSidebar,
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    width: 36,
                    height: 36,
                    alignment: Alignment.center,
                    child: Icon(
                      LucideIcons.menu,
                      size: 20,
                      color: palette.textSec,
                    ),
                  ),
                ),
              if (onBackToProjects != null) ...[
                InkWell(
                  onTap: onBackToProjects,
                  borderRadius: BorderRadius.circular(6),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(LucideIcons.arrowLeft, size: 14, color: palette.textSec),
                        const SizedBox(width: 4),
                        Text(
                          'Projects',
                          style: UnoTypography.body(
                            color: palette.textSec,
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text('/', style: UnoTypography.body(color: palette.div, fontSize: 12)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 4),
              ],
              // Project Switcher Pill matching Kushall-07/SyncGuard · main ↕
              InkWell(
                onTap: onBackToProjects,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: palette.bgSurface,
                    border: Border.all(color: palette.div),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        LucideIcons.folder,
                        size: 14,
                        color: palette.accent,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '$displayName · $displayBranch',
                        style: UnoTypography.body(
                          color: palette.text,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Icon(
                        LucideIcons.chevronsUpDown,
                        size: 13,
                        color: palette.textSec,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),

          // ── Middle: Draggable window title bar area ──
          Expanded(
            child: isDesktop
                ? const DragToMoveArea(
                    child: SizedBox(
                      height: 52,
                      width: double.infinity,
                    ),
                  )
                : const SizedBox(height: 52),
          ),

          // ── Right: Notification, Theme, and Desktop Window Controls ──
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Notification bell button
              Stack(
                clipBehavior: Clip.none,
                children: [
                  InkWell(
                    onTap: onToggleNotifications,
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      width: 30,
                      height: 30,
                      decoration: BoxDecoration(
                        color: notificationsOpen
                            ? palette.accent.withValues(alpha: 0.12)
                            : Colors.transparent,
                        border: Border.all(
                          color: notificationsOpen
                              ? palette.accent
                              : palette.div,
                        ),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Icon(
                        LucideIcons.bell,
                        size: 13,
                        color: notificationsOpen
                            ? palette.accent
                            : palette.textSec,
                      ),
                    ),
                  ),
                  if (unreadCount > 0)
                    Positioned(
                      top: 3,
                      right: 3,
                      child: Container(
                        width: 7,
                        height: 7,
                        decoration: BoxDecoration(
                          color: palette.inferred,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: palette.bgBase,
                            width: 1.5,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(width: 12),
              // Theme toggle button
              InkWell(
                onTap: onToggleTheme,
                borderRadius: BorderRadius.circular(6),
                child: Container(
                  width: 30,
                  height: 30,
                  decoration: BoxDecoration(
                    color: Colors.transparent,
                    border: Border.all(color: palette.div),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Icon(
                    isDark ? LucideIcons.moon : LucideIcons.sun,
                    size: 14,
                    color: palette.textSec,
                  ),
                ),
              ),

              // Desktop Window Controls (Minimize, Maximize/Restore, Close)
              if (isDesktop) ...[
                const SizedBox(width: 8),
                DesktopWindowControls(palette: palette, height: 52),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
