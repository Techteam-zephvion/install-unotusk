import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../config/presentation/config_controller.dart';
import '../../wizard/presentation/wizard_controller.dart';
import 'verify_controller.dart';

class VerifyScreen extends ConsumerWidget {
  const VerifyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final verifyState = ref.watch(verifyControllerProvider);
    final verifyNotifier = ref.read(verifyControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);
    final serverUrl = ref.watch(configControllerProvider).config.serverUrl;

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Verifying Server Health', style: AppTextStyles.h1),
              const SizedBox(height: 6),
              Text(
                'Checking server responsiveness and database connectivity.',
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600),
              ),
              const SizedBox(height: 24),
              AppCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        if (verifyState.isVerifying) ...[
                          const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                          ),
                          const SizedBox(width: 12),
                          Text('Waiting for server startup...', style: AppTextStyles.bodyMedium),
                        ] else if (verifyState.isSuccess) ...[
                          const Icon(Icons.check_circle, size: 20, color: AppColors.success),
                          const SizedBox(width: 10),
                          Text(
                            'Running',
                            style: AppTextStyles.h2.copyWith(color: AppColors.success),
                          ),
                        ] else ...[
                          const Icon(Icons.cancel, size: 20, color: AppColors.error),
                          const SizedBox(width: 10),
                          Text(
                            'Unhealthy',
                            style: AppTextStyles.h2.copyWith(color: AppColors.error),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Divider(),
                    const SizedBox(height: 16),
                    _buildMetricRow('Server Address', serverUrl),
                    const SizedBox(height: 10),
                    _buildMetricRow(
                      'Database',
                      verifyState.healthStatus?.databaseStatus ?? (verifyState.isVerifying ? 'Checking...' : 'Disconnected'),
                      isSuccess: verifyState.healthStatus?.databaseStatus == 'connected',
                    ),
                    const SizedBox(height: 10),
                    _buildMetricRow(
                      'Redis Cache & Queue',
                      verifyState.healthStatus?.redisStatus ?? (verifyState.isVerifying ? 'Checking...' : 'Disconnected'),
                      isSuccess: verifyState.healthStatus?.redisStatus == 'connected',
                    ),
                    if (verifyState.healthStatus?.version != null) ...[
                      const SizedBox(height: 10),
                      _buildMetricRow('API Version', 'v${verifyState.healthStatus!.version}'),
                    ],
                  ],
                ),
              ),
              if (!verifyState.isVerifying && !verifyState.isSuccess) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.errorBg,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppColors.errorBorder),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.error_outline, size: 18, color: AppColors.error),
                          const SizedBox(width: 8),
                          Text('Health check failed', style: AppTextStyles.h3.copyWith(color: AppColors.error)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        verifyState.errorMessage ?? 'Server failed to start in time.',
                        style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate800),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (!verifyState.isVerifying && !verifyState.isSuccess) ...[
                    AppButton(
                      label: 'Retry Check',
                      variant: AppButtonVariant.secondary,
                      icon: Icons.refresh,
                      onPressed: () => verifyNotifier.verifyServer(),
                    ),
                    const SizedBox(width: 12),
                  ],
                  AppButton(
                    label: 'Continue',
                    isLoading: verifyState.isVerifying,
                    onPressed: verifyState.isSuccess
                        ? () => wizardNotifier.nextStep()
                        : null,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetricRow(String label, String value, {bool? isSuccess}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600)),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (isSuccess != null) ...[
              Icon(
                isSuccess ? Icons.check_circle_outline : Icons.cancel_outlined,
                size: 14,
                color: isSuccess ? AppColors.success : AppColors.error,
              ),
              const SizedBox(width: 6),
            ],
            Text(
              value,
              style: AppTextStyles.bodyMedium.copyWith(
                fontWeight: FontWeight.w600,
                color: isSuccess == true
                    ? AppColors.success
                    : isSuccess == false
                        ? AppColors.error
                        : AppColors.slate900,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
