import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/theme/app_text_styles.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../wizard/presentation/wizard_controller.dart';
import '../../validation/domain/check_item.dart';
import '../../config/presentation/config_controller.dart';
import 'network_check_controller.dart';

class NetworkCheckScreen extends ConsumerWidget {
  const NetworkCheckScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = UnoPalette.of(context);
    final checkState = ref.watch(networkCheckControllerProvider);
    final checkNotifier = ref.read(networkCheckControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 580),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Network Check',
                style: UnoTypography.brandSerif(
                  palette: palette,
                  fontSize: 21,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Detecting LAN interface, IP endpoints, and verifying firewall reachability.',
                style: AppTextStyles.bodyMediumOf(context).copyWith(
                  color: palette.textSec,
                  fontSize: 13.5,
                ),
              ),
              const SizedBox(height: 24),
              AppCard(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
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
              Wrap(
                alignment: WrapAlignment.end,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 12,
                runSpacing: 10,
                children: [
                  if (checkState.hasCriticalFailure)
                    AppButton(
                      label: 'Retry',
                      variant: AppButtonVariant.secondary,
                      icon: Icons.refresh_rounded,
                      onPressed: checkState.isRunning ? null : () => checkNotifier.runChecks(),
                    ),
                  AppButton(
                    label: 'Continue',
                    icon: Icons.arrow_forward_rounded,
                    isLoading: checkState.isRunning,
                    onPressed: checkState.isAllPassed
                        ? () {
                            if (checkState.detectedIp != null) {
                              ref.read(configControllerProvider.notifier).updateLanIp(checkState.detectedIp!);
                              if (checkState.availablePort != null) {
                                ref.read(configControllerProvider.notifier).updateServerPort(checkState.availablePort!.toString());
                              }
                            }
                            wizardNotifier.nextStep();
                          }
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
    final palette = UnoPalette.of(context);
    Widget statusIcon;

    switch (item.status) {
      case CheckStatus.pending:
        statusIcon = Container(
          width: 18,
          height: 18,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: palette.bgElevated,
            border: Border.all(color: palette.div),
          ),
        );
        break;
      case CheckStatus.checking:
        statusIcon = SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(strokeWidth: 2, color: palette.accent),
        );
        break;
      case CheckStatus.passed:
        statusIcon = Icon(Icons.check_circle_rounded, size: 20, color: palette.live);
        break;
      case CheckStatus.warning:
        statusIcon = Icon(Icons.info_outline_rounded, size: 20, color: palette.warn);
        break;
      case CheckStatus.failed:
        statusIcon = Icon(Icons.cancel_rounded, size: 20, color: palette.error);
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
                  style: AppTextStyles.bodyMediumOf(context).copyWith(
                    fontWeight: FontWeight.w500,
                    fontSize: 13.5,
                    color: item.status.isFailed ? palette.error : palette.text,
                  ),
                ),
                if (item.status.isFailed && item.failureMessage != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    item.failureMessage!,
                    style: AppTextStyles.bodySmallOf(context).copyWith(
                      color: palette.error,
                      fontSize: 12,
                    ),
                  ),
                ],
                if (item.status.isPassed && item.description.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    item.description,
                    style: AppTextStyles.bodySmallOf(context).copyWith(
                      color: palette.textSec,
                      fontSize: 12,
                    ),
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
    final palette = UnoPalette.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: palette.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: palette.error.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.error_outline_rounded, size: 18, color: palette.error),
              const SizedBox(width: 8),
              Text(
                '${failedItem.title} Failed',
                style: AppTextStyles.h3Of(context).copyWith(color: palette.error),
              ),
            ],
          ),
          if (failedItem.remediationHint != null) ...[
            const SizedBox(height: 6),
            Text(
              failedItem.remediationHint!,
              style: AppTextStyles.bodyMediumOf(context).copyWith(
                color: palette.text,
                fontSize: 13,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
