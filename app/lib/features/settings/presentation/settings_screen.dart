import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../app/config/app_config.dart';
import '../../../app/theme/app_colors.dart';
import '../../../app/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/desktop_scaffold.dart';
import '../../../core/widgets/status_badge.dart';
import '../../../core/logging/diagnostic_logs_modal.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../connection/presentation/connection_controller.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authControllerProvider);
    final connectionState = ref.watch(connectionControllerProvider);
    final user = authState.user;

    return DesktopScaffold(
      currentRoute: '/settings',
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 640),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Page Title
              Text('Settings', style: AppTextStyles.h1),
              const SizedBox(height: 4),
              Text(
                'Application connection, account, and environment configuration',
                style: AppTextStyles.bodySmall,
              ),
              const SizedBox(height: 24),

              // Section 1: Server Configuration
              Text('Server', style: AppTextStyles.h3),
              const SizedBox(height: 8),
              AppCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Server address', style: AppTextStyles.label),
                            const SizedBox(height: 2),
                            Text(
                              connectionState.serverUrl,
                              style: AppTextStyles.code.copyWith(fontSize: 13),
                            ),
                          ],
                        ),
                        AppButton(
                          text: 'Change',
                          variant: AppButtonVariant.secondary,
                          onPressed: () => context.go('/connection'),
                        ),
                      ],
                    ),
                    const Divider(height: 24),
                    Row(
                      children: [
                        Text('Connection status', style: AppTextStyles.label),
                        const Spacer(),
                        StatusBadge(
                          label: connectionState.isConnected ? 'CONNECTED' : 'DISCONNECTED',
                          variant: connectionState.isConnected
                              ? BadgeVariant.success
                              : BadgeVariant.warning,
                        ),
                        const SizedBox(width: 8),
                        IconButton(
                          icon: const Icon(Icons.refresh, size: 16),
                          tooltip: 'Test Connection',
                          onPressed: () =>
                              ref.read(connectionControllerProvider.notifier).checkConnection(),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Section 2: Account Details
              Text('Account', style: AppTextStyles.h3),
              const SizedBox(height: 8),
              AppCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (user != null) ...[
                      Row(
                        children: [
                          CircleAvatar(
                            radius: 18,
                            backgroundColor: AppColors.slate200,
                            child: Text(
                              user.fullName.isNotEmpty ? user.fullName[0].toUpperCase() : 'U',
                              style: AppTextStyles.h3.copyWith(color: AppColors.slate800),
                            ),
                          ),
                          const SizedBox(width: 14),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(user.fullName, style: AppTextStyles.h3),
                              Text(user.email, style: AppTextStyles.bodySmall),
                            ],
                          ),
                          const Spacer(),
                          StatusBadge(
                            label: user.role.toUpperCase(),
                            variant: BadgeVariant.neutral,
                          ),
                        ],
                      ),
                      const Divider(height: 24),
                      AppButton(
                        text: 'Sign Out',
                        variant: AppButtonVariant.danger,
                        icon: Icons.logout,
                        onPressed: () =>
                            ref.read(authControllerProvider.notifier).logout(),
                      ),
                    ] else ...[
                      Text('No active session.', style: AppTextStyles.bodyMedium),
                      const SizedBox(height: 12),
                      AppButton(
                        text: 'Sign In',
                        onPressed: () => context.go('/login'),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Section 3: Application & Diagnostics
              Text('Application & Diagnostics', style: AppTextStyles.h3),
              const SizedBox(height: 8),
              AppCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Unotusk Employee Client', style: AppTextStyles.label),
                            const SizedBox(height: 2),
                            Text(
                              'Desktop Foundation v${AppConfig.appVersion}',
                              style: AppTextStyles.bodySmall,
                            ),
                          ],
                        ),
                        StatusBadge(
                          label: 'DESKTOP-FIRST',
                          variant: BadgeVariant.info,
                        ),
                      ],
                    ),
                    const Divider(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Pilot Event Logs', style: AppTextStyles.label),
                            const SizedBox(height: 2),
                            Text(
                              'Inspect sanitized in-memory event stream for LAN testing',
                              style: AppTextStyles.bodySmall,
                            ),
                          ],
                        ),
                        AppButton(
                          text: 'View Logs',
                          icon: Icons.receipt_long_outlined,
                          variant: AppButtonVariant.secondary,
                          onPressed: () => DiagnosticLogsModal.show(context),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
