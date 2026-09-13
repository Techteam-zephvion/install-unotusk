import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/config/app_config.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';
import '../../features/auth/presentation/auth_controller.dart';
import '../../features/connection/presentation/connection_controller.dart';
import 'status_badge.dart';

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
    final user = authState.user;

    return Scaffold(
      backgroundColor: AppColors.slate50,
      body: Column(
        children: [
          // Top Application Bar
          Container(
            height: 48,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(
                bottom: BorderSide(color: AppColors.slate200),
              ),
            ),
            child: Row(
              children: [
                // App Logo & Name
                Row(
                  children: [
                    Container(
                      width: 24,
                      height: 24,
                      decoration: BoxDecoration(
                        color: AppColors.slate900,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Center(
                        child: Text(
                          'U',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      AppConfig.appName,
                      style: AppTextStyles.h2.copyWith(fontSize: 14),
                    ),
                  ],
                ),
                const SizedBox(width: 32),

                // Primary Navigation Items
                _NavItem(
                  label: 'Projects',
                  icon: Icons.folder_outlined,
                  isSelected: currentRoute.startsWith('/projects'),
                  onTap: () => context.go('/projects'),
                ),
                const SizedBox(width: 8),
                _NavItem(
                  label: 'Settings',
                  icon: Icons.settings_outlined,
                  isSelected: currentRoute.startsWith('/settings'),
                  onTap: () => context.go('/settings'),
                ),

                const Spacer(),

                // Server Connection Status
                InkWell(
                  onTap: () => context.go('/settings'),
                  borderRadius: BorderRadius.circular(4),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: connectionState.isConnected
                                ? AppColors.success
                                : AppColors.warning,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          connectionState.isConnected ? 'Connected' : 'Offline / Checking',
                          style: AppTextStyles.bodySmall.copyWith(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 16),

                // User / Account Area
                if (user != null) ...[
                  Container(
                    height: 24,
                    width: 1,
                    color: AppColors.slate200,
                  ),
                  const SizedBox(width: 16),
                  PopupMenuButton<String>(
                    offset: const Offset(0, 36),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                      side: const BorderSide(color: AppColors.slate200),
                    ),
                    color: Colors.white,
                    elevation: 2,
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
                                color: AppColors.slate900,
                              ),
                            ),
                            Text(
                              user.email,
                              style: AppTextStyles.bodySmall,
                            ),
                            const SizedBox(height: 4),
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
                            const Icon(Icons.settings_outlined, size: 16, color: AppColors.slate700),
                            const SizedBox(width: 8),
                            Text('Settings', style: AppTextStyles.bodyMedium),
                          ],
                        ),
                      ),
                      PopupMenuItem(
                        value: 'logout',
                        child: Row(
                          children: [
                            const Icon(Icons.logout, size: 16, color: AppColors.error),
                            const SizedBox(width: 8),
                            Text('Sign Out', style: AppTextStyles.bodyMedium.copyWith(color: AppColors.error)),
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
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 12,
                          backgroundColor: AppColors.slate200,
                          child: Text(
                            user.fullName.isNotEmpty ? user.fullName[0].toUpperCase() : 'U',
                            style: AppTextStyles.bodySmall.copyWith(
                              fontWeight: FontWeight.w600,
                              color: AppColors.slate800,
                              fontSize: 11,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 120),
                          child: Text(
                            user.fullName.isNotEmpty ? user.fullName : user.email,
                            style: AppTextStyles.bodyMedium.copyWith(
                              fontWeight: FontWeight.w500,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Icon(Icons.keyboard_arrow_down, size: 14, color: AppColors.slate500),
                      ],
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

  const _NavItem({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.slate100 : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              size: 16,
              color: isSelected ? AppColors.primary : AppColors.slate600,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                color: isSelected ? AppColors.slate900 : AppColors.slate700,
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
