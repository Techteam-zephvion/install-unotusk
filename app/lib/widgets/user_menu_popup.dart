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

  Widget _buildItem({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) {
    return InkWell(
      onTap: onTap,
      hoverColor: palette.accent.withValues(alpha: 0.08),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        child: Row(
          children: [
            Icon(
              icon,
              size: 14,
              color: isDestructive ? const Color(0xFFE05A5A) : palette.textSec,
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Text(
                label,
                style: UnoTypography.body(
                  color:
                      isDestructive ? const Color(0xFFE05A5A) : palette.text,
                  fontSize: 13,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 240,
      decoration: BoxDecoration(
        color: palette.bgSurface,
        border: Border.all(color: palette.div),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.22),
            blurRadius: 28,
            offset: const Offset(0, 8),
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
                  width: 34,
                  height: 34,
                  decoration: const BoxDecoration(
                    color: Color(0xFF7B5EA7),
                    shape: BoxShape.circle,
                  ),
                  child: const Center(
                    child: Icon(LucideIcons.user, size: 16, color: Colors.white),
                  ),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.name.isNotEmpty ? user.name : 'User',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: UnoTypography.body(
                          color: palette.text,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (user.org.isNotEmpty)
                        Text(
                          user.org,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: UnoTypography.mono(
                            color: palette.textSec,
                            fontSize: 10,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Divider(height: 1, thickness: 1, color: palette.div),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                _buildItem(
                  icon: LucideIcons.sliders,
                  label: 'Personalization',
                  onTap: () {
                    onClose();
                    onNavigateSettings('personalization');
                  },
                ),
                _buildItem(
                  icon: LucideIcons.user,
                  label: 'Profile',
                  onTap: () {
                    onClose();
                    onNavigateSettings('profile');
                  },
                ),
                _buildItem(
                  icon: LucideIcons.settings,
                  label: 'Settings',
                  onTap: () {
                    onClose();
                    onNavigateSettings('settings');
                  },
                ),
              ],
            ),
          ),
          Divider(height: 1, thickness: 1, color: palette.div),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Column(
              children: [
                _buildItem(
                  icon: LucideIcons.lifeBuoy,
                  label: 'Support',
                  onTap: () {
                    onClose();
                    onNavigateSettings('support');
                  },
                ),
                _buildItem(
                  icon: LucideIcons.logOut,
                  label: 'Sign out',
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
    );
  }
}
