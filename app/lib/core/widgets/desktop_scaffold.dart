import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/config/app_config.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';
import '../../app/theme/theme_controller.dart';
import '../../features/auth/presentation/auth_controller.dart';
import '../../features/connection/presentation/connection_controller.dart';
import 'status_badge.dart';
import 'unotusk_mark.dart';

class DesktopScaffold extends ConsumerWidget {
  final Widget body;
  final String currentRoute;

  const DesktopScaffold({
    super.key,
    required this.body,
    required this.currentRoute,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final connectionState = ref.watch(connectionControllerProvider);
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == ThemeMode.dark;
    final user = authState.user;

    final bgColor = Theme.of(context).scaffoldBackgroundColor;
    final surfaceColor = Theme.of(context).colorScheme.surface;
    final dividerColor = isDark ? AppColors.divider : AppColors.dividerLight;

    return Scaffold(
      backgroundColor: bgColor,
      body: Column(
        children: [
          // Top Application Bar (52px matching Figma specification)
          Container(
            height: 52,
            padding: const EdgeInsets.symmetric(horizontal: 20),
            decoration: BoxDecoration(
              color: surfaceColor,
              border: Border(
                bottom: BorderSide(color: dividerColor),
              ),
            ),
            child: Row(
              children: [
                // App Logo & Name
                InkWell(
                  onTap: () => context.go('/projects'),
                  borderRadius: BorderRadius.circular(6),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
                    child: Row(
                      children: [
                        UnotuskMark(size: 26, isDark: isDark),
                        const SizedBox(width: 10),
                        Text(
                          AppConfig.appName,
                          style: AppTextStyles.h2.copyWith(
                            fontSize: 14,
                            letterSpacing: -0.2,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 28),

                // Primary Navigation Items (Pill Styled)
                _NavItem(
                  label: 'Projects',
                  icon: Icons.folder_outlined,
                  isSelected: currentRoute.startsWith('/projects'),
                  onTap: () => context.go('/projects'),
                  isDark: isDark,
                ),
                const SizedBox(width: 6),
                _NavItem(
                  label: 'Settings',
                  icon: Icons.settings_outlined,
                  isSelected: currentRoute.startsWith('/settings'),
                  onTap: () => context.go('/settings'),
                  isDark: isDark,
                ),

                const Spacer(),

                // Live Server Connection Status Pill
                InkWell(
                  onTap: () => context.go('/settings'),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: connectionState.isConnected
                          ? AppColors.liveBg
                          : AppColors.warningBg,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: connectionState.isConnected
                            ? AppColors.successBorder
                            : AppColors.warningBorder,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 7,
                          height: 7,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: connectionState.isConnected
                                ? AppColors.live
                                : AppColors.warning,
                          ),
                        ),
                        const SizedBox(width: 7),
                        Text(
                          connectionState.isConnected ? 'Connected' : 'Offline / Checking',
                          style: AppTextStyles.bodySmall.copyWith(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color: connectionState.isConnected
                                ? AppColors.live
                                : AppColors.warning,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 10),

                // Theme Toggle (Sun / Moon)
                IconButton(
                  tooltip: isDark ? 'Switch to light theme' : 'Switch to dark theme',
                  icon: Icon(
                    isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                    size: 17,
                    color: isDark ? AppColors.textSecondary : AppColors.textSecondaryLight,
                  ),
                  onPressed: () => ref.read(themeModeProvider.notifier).toggleTheme(),
                  splashRadius: 18,
                ),
                const SizedBox(width: 4),

                // User / Account Area
                if (user != null) ...[
                  Container(
                    height: 20,
                    width: 1,
                    color: dividerColor,
                  ),
                  const SizedBox(width: 12),
                  PopupMenuButton<String>(
                    offset: const Offset(0, 42),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                      side: BorderSide(color: dividerColor),
                    ),
                    color: isDark ? AppColors.bgElevated : AppColors.bgElevatedLight,
                    elevation: 8,
                    tooltip: 'Account Menu',
                    itemBuilder: (context) => [
                      PopupMenuItem(
                        enabled: false,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user.fullName,
                              style: AppTextStyles.bodyMedium.copyWith(
                                fontWeight: FontWeight.w600,
                                color: isDark ? AppColors.textPrimary : AppColors.textPrimaryLight,
                              ),
                            ),
                            Text(
                              user.email,
                              style: AppTextStyles.bodySmall.copyWith(
                                color: isDark ? AppColors.textSecondary : AppColors.textSecondaryLight,
                              ),
                            ),
                            const SizedBox(height: 6),
                            StatusBadge(
                              label: user.role.toUpperCase(),
                              variant: BadgeVariant.neutral,
                            ),
                          ],
                        ),
                      ),
                      const PopupMenuDivider(),
                      PopupMenuItem(
                        value: 'settings',
                        child: Row(
                          children: [
                            Icon(
                              Icons.settings_outlined,
                              size: 15,
                              color: isDark ? AppColors.textSecondary : AppColors.textSecondaryLight,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              'Settings',
                              style: AppTextStyles.bodyMedium.copyWith(
                                color: isDark ? AppColors.textPrimary : AppColors.textPrimaryLight,
                              ),
                            ),
                          ],
                        ),
                      ),
                      PopupMenuItem(
                        value: 'logout',
                        child: Row(
                          children: [
                            const Icon(Icons.logout, size: 15, color: AppColors.error),
                            const SizedBox(width: 8),
                            Text(
                              'Sign Out',
                              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.error),
                            ),
                          ],
                        ),
                      ),
                    ],
                    onSelected: (value) {
                      if (value == 'settings') {
                        context.go('/settings');
                      } else if (value == 'logout') {
                        ref.read(authControllerProvider.notifier).logout();
                      }
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.transparent),
                      ),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 13,
                            backgroundColor: isDark ? AppColors.bgElevated : const Color(0xFFE6E5DF),
                            child: Text(
                              user.fullName.isNotEmpty ? user.fullName[0].toUpperCase() : 'U',
                              style: TextStyle(
                                fontWeight: FontWeight.w600,
                                color: AppColors.accent,
                                fontSize: 11,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 130),
                            child: Text(
                              user.fullName.isNotEmpty ? user.fullName : user.email,
                              style: AppTextStyles.bodyMedium.copyWith(
                                fontWeight: FontWeight.w500,
                                fontSize: 13,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 4),
                          Icon(
                            Icons.keyboard_arrow_down,
                            size: 15,
                            color: isDark ? AppColors.textSecondary : AppColors.textSecondaryLight,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),

          // Main Content Area
          Expanded(child: body),
        ],
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;
  final bool isDark;

  const _NavItem({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected
              ? (isDark ? AppColors.accentMuted : const Color(0x1ADA7756))
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSelected
                ? AppColors.accent.withValues(alpha: 0.35)
                : Colors.transparent,
          ),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              size: 15,
              color: isSelected
                  ? AppColors.accent
                  : (isDark ? AppColors.textSecondary : AppColors.textSecondaryLight),
            ),
            const SizedBox(width: 7),
            Text(
              label,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                color: isSelected
                    ? (isDark ? AppColors.textPrimary : AppColors.accent)
                    : (isDark ? AppColors.textSecondary : AppColors.textSecondaryLight),
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
