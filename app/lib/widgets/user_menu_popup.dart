import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../theme/app_theme.dart';

class UserMenuPopup extends StatelessWidget {
  final UnoPalette palette;
  final UserModel user;
  final Function(String) onNavigateSettings;
  final VoidCallback onLogOut;
  final VoidCallback onClose;

  const UserMenuPopup({
    super.key,
    required this.palette,
    required this.user,
    required this.onNavigateSettings,
    required this.onLogOut,
    required this.onClose,
  });

  String _initials(String name) {
    final parts =
        name.trim().split(RegExp(r'\s+')).where((s) => s.isNotEmpty).toList();
    if (parts.isEmpty) return 'U';
    if (parts.length == 1) {
      return parts[0].substring(0, parts[0].length >= 2 ? 2 : 1).toUpperCase();
    }
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = palette.isDark;
    final cardBg = isDark ? const Color(0xFF161A29) : const Color(0xFFFFFFFF);
    final borderColor =
        isDark ? const Color(0xFF2E313C) : const Color(0xFFE4DFD6);
    final avatarBg =
        isDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20);
    final avatarFg =
        isDark ? const Color(0xFF0A0F20) : const Color(0xFFCBC1B4);
    final displayName = user.name.isNotEmpty ? user.name : 'User';
    final subtitle = user.org.isNotEmpty ? user.org : user.email;

    return Material(
      color: Colors.transparent,
      child: Container(
        width: 244,
        decoration: BoxDecoration(
          color: cardBg,
          border: Border.all(color: borderColor, width: 1),
          borderRadius: BorderRadius.circular(13),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF0A0F20)
                  .withValues(alpha: isDark ? 0.45 : 0.14),
              blurRadius: 24,
              spreadRadius: 0,
              offset: const Offset(0, 10),
            ),
            BoxShadow(
              color: const Color(0xFF0A0F20)
                  .withValues(alpha: isDark ? 0.20 : 0.05),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // User info header
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 13, 14, 12),
              child: Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: avatarBg,
                      borderRadius: BorderRadius.circular(9),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      _initials(displayName),
                      style: UnoTypography.body(
                        color: avatarFg,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          displayName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: UnoTypography.body(
                            color: palette.text,
                            fontSize: 13.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        if (subtitle.isNotEmpty) ...[
                          const SizedBox(height: 1.5),
                          Text(
                            subtitle,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: UnoTypography.body(
                              color: palette.textSec,
                              fontSize: 11.5,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Divider(height: 1, thickness: 1, color: borderColor),
            Padding(
              padding: const EdgeInsets.all(6),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _PopupMenuRow(
                    icon: LucideIcons.sliders,
                    label: 'Personalization',
                    palette: palette,
                    onTap: () {
                      onClose();
                      onNavigateSettings('personalization');
                    },
                  ),
                  _PopupMenuRow(
                    icon: LucideIcons.user,
                    label: 'Profile',
                    palette: palette,
                    onTap: () {
                      onClose();
                      onNavigateSettings('profile');
                    },
                  ),
                  _PopupMenuRow(
                    icon: LucideIcons.settings,
                    label: 'Settings',
                    palette: palette,
                    onTap: () {
                      onClose();
                      onNavigateSettings('settings');
                    },
                  ),
                ],
              ),
            ),
            Divider(height: 1, thickness: 1, color: borderColor),
            Padding(
              padding: const EdgeInsets.all(6),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _PopupMenuRow(
                    icon: LucideIcons.lifeBuoy,
                    label: 'Support',
                    palette: palette,
                    onTap: () {
                      onClose();
                      onNavigateSettings('support');
                    },
                  ),
                  _PopupMenuRow(
                    icon: LucideIcons.logOut,
                    label: 'Sign out',
                    palette: palette,
                    isDestructive: true,
                    onTap: () {
                      onClose();
                      onLogOut();
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PopupMenuRow extends StatefulWidget {
  final IconData icon;
  final String label;
  final UnoPalette palette;
  final VoidCallback onTap;
  final bool isDestructive;

  const _PopupMenuRow({
    required this.icon,
    required this.label,
    required this.palette,
    required this.onTap,
    this.isDestructive = false,
  });

  @override
  State<_PopupMenuRow> createState() => _PopupMenuRowState();
}

class _PopupMenuRowState extends State<_PopupMenuRow> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final isDark = widget.palette.isDark;
    const destructiveColor = Color(0xFFE05A5A);

    final hoverBase = widget.isDestructive
        ? destructiveColor
        : (isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20));

    final bgColor = hoverBase.withValues(
      alpha: _hovered ? (widget.isDestructive ? 0.10 : 0.06) : 0.0,
    );

    final iconColor = widget.isDestructive
        ? destructiveColor
        : (_hovered ? widget.palette.text : widget.palette.textSec);

    final textColor = widget.isDestructive
        ? destructiveColor
        : (_hovered ? widget.palette.text : widget.palette.text);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              SizedBox(
                width: 18,
                height: 18,
                child: Center(
                  child: Icon(
                    widget.icon,
                    size: 14.5,
                    color: iconColor,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  widget.label,
                  style: UnoTypography.body(
                    color: textColor,
                    fontSize: 13,
                    fontWeight: _hovered ? FontWeight.w500 : FontWeight.w400,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
