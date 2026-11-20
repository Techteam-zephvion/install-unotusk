import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_fonts.dart';
import '../../../core/theme/uno_palette.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../wizard/presentation/wizard_controller.dart';
import '../../wizard/domain/wizard_step.dart';
import '../domain/check_item.dart';
import 'server_check_controller.dart';

class ServerCheckScreen extends ConsumerWidget {
  const ServerCheckScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = UnoPalette.of(context);
    final checkState = ref.watch(serverCheckControllerProvider);
    final checkNotifier = ref.read(serverCheckControllerProvider.notifier);
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
                'Environment Preflight Verification',
                style: AppFonts.display(
                  fontSize: 28,
                  color: palette.text,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Validating system container engine, memory allocation, and OS prerequisites.',
                style: AppFonts.body(
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
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  AppButton(
                    label: 'Back',
                    variant: AppButtonVariant.secondary,
                    icon: Icons.arrow_back_rounded,
                    onPressed: checkState.isRunning ? null : () => wizardNotifier.previousStep(),
                  ),
                  Wrap(
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 12,
                    runSpacing: 10,
                    children: [
                      if (checkState.hasCriticalFailure)
                        AppButton(
                          label: 'Retry Checks',
                          variant: AppButtonVariant.secondary,
                          icon: Icons.refresh_rounded,
                          onPressed: checkState.isRunning ? null : () => checkNotifier.runChecks(),
                        ),
                      if (checkState.hasOnlyPortConflict && checkState.isExistingUnotuskActive)
                        AppButton(
                          label: 'Use Existing Server',
                          variant: AppButtonVariant.secondary,
                          icon: Icons.check_circle_outline_rounded,
                          onPressed: checkState.isRunning
                              ? null
                              : () => wizardNotifier.setStep(WizardStep.verify),
                        ),
                      AppButton(
                        label: checkState.hasOnlyPortConflict ? 'Configure Alternate Port' : 'Continue',
                        icon: Icons.arrow_forward_rounded,
                        isLoading: checkState.isRunning,
                        onPressed: (checkState.isAllPassed || checkState.hasOnlyPortConflict)
                            ? () => wizardNotifier.nextStep()
                            : null,
                      ),
                    ],
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
                  style: AppFonts.body(
                    fontWeight: FontWeight.w500,
                    fontSize: 13.5,
                    color: item.status.isFailed ? palette.error : palette.text,
                  ),
                ),
                if (item.status.isFailed && item.failureMessage != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    item.failureMessage!,
                    style: AppFonts.body(
                      color: palette.error,
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
                style: AppFonts.youngSerif(color: palette.error, fontSize: 16),
              ),
            ],
          ),
          if (failedItem.remediationHint != null) ...[
            const SizedBox(height: 6),
            Text(
              failedItem.remediationHint!,
              style: AppFonts.body(
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
