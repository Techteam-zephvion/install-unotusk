import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../wizard/presentation/wizard_controller.dart';
import '../domain/check_item.dart';
import 'server_check_controller.dart';

class ServerCheckScreen extends ConsumerWidget {
  const ServerCheckScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checkState = ref.watch(serverCheckControllerProvider);
    final checkNotifier = ref.read(serverCheckControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Check Server', style: AppTextStyles.h1),
              const SizedBox(height: 6),
              Text(
                'Checking machine readiness and prerequisites before installation.',
                style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate600),
              ),
              const SizedBox(height: 24),
              AppCard(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: Column(
                  children: checkState.items.map((item) {
                    return _buildCheckRow(context, item);
                  }).toList(),
                ),
              ),
              if (checkState.hasCriticalFailure) ...[
                const SizedBox(height: 16),
                _buildFailureBanner(context, checkState.items.firstWhere((i) => i.status.isFailed)),
              ],
              const SizedBox(height: 32),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  if (checkState.hasCriticalFailure) ...[
                    AppButton(
                      label: 'Retry',
                      variant: AppButtonVariant.secondary,
                      icon: Icons.refresh,
                      onPressed: checkState.isRunning ? null : () => checkNotifier.runChecks(),
                    ),
                    const SizedBox(width: 12),
                  ],
                  AppButton(
                    label: 'Continue',
                    isLoading: checkState.isRunning,
                    onPressed: checkState.isAllPassed
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

  Widget _buildCheckRow(BuildContext context, CheckItem item) {
    Widget statusIcon;

    switch (item.status) {
      case CheckStatus.pending:
        statusIcon = Container(
          width: 16,
          height: 16,
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            color: AppColors.slate200,
          ),
        );
        break;
      case CheckStatus.checking:
        statusIcon = const SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
        );
        break;
      case CheckStatus.passed:
        statusIcon = const Icon(Icons.check_circle, size: 18, color: AppColors.success);
        break;
      case CheckStatus.warning:
        statusIcon = const Icon(Icons.info, size: 18, color: AppColors.warning);
        break;
      case CheckStatus.failed:
        statusIcon = const Icon(Icons.cancel, size: 18, color: AppColors.error);
        break;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          statusIcon,
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.title,
                  style: AppTextStyles.bodyMedium.copyWith(
                    fontWeight: FontWeight.w500,
                    color: item.status.isFailed ? AppColors.error : AppColors.slate900,
                  ),
                ),
                if (item.status.isFailed && item.failureMessage != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    item.failureMessage!,
                    style: AppTextStyles.bodySmall.copyWith(color: AppColors.error),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFailureBanner(BuildContext context, CheckItem failedItem) {
    return Container(
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
              Text(
                '${failedItem.title} Failed',
                style: AppTextStyles.h3.copyWith(color: AppColors.error),
              ),
            ],
          ),
          if (failedItem.remediationHint != null) ...[
            const SizedBox(height: 6),
            Text(
              failedItem.remediationHint!,
              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate800),
            ),
          ],
        ],
      ),
    );
  }
}
