import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/uno_palette.dart';
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
    final palette = UnoPalette.of(context);
    final verifyState = ref.watch(verifyControllerProvider);
    final verifyNotifier = ref.read(verifyControllerProvider.notifier);
    final wizardNotifier = ref.read(wizardControllerProvider.notifier);
    final serverConfig = ref.watch(configControllerProvider).config;
    final localUrl = 'http://localhost:${serverConfig.serverPort}';
    final lanUrl = verifyState.lanServerUrl;

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 580),
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Verifying Server Health',
                style: UnoTypography.brandSerif(
                  palette: palette,
                  fontSize: 21,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Checking server responsiveness, database transactions, and network handshake.',
                style: AppTextStyles.bodyMediumOf(context).copyWith(
                  color: palette.textSec,
                  fontSize: 13.5,
                ),
              ),
              const SizedBox(height: 24),
              AppCard(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        if (verifyState.isVerifying) ...[
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: palette.accent),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            'Waiting for services to start...',
                            style: AppTextStyles.bodyMediumOf(context).copyWith(
                              fontWeight: FontWeight.w500,
                              color: palette.text,
                            ),
                          ),
                        ] else if (verifyState.isSuccess) ...[
                          Icon(Icons.check_circle_rounded, size: 22, color: palette.live),
                          const SizedBox(width: 10),
                          Text(
                            'Services Running & Healthy',
                            style: AppTextStyles.h2Of(context).copyWith(
                              color: palette.live,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ] else ...[
                          Icon(Icons.cancel_rounded, size: 22, color: palette.error),
                          const SizedBox(width: 10),
                          Text(
                            'Verification Failed',
                            style: AppTextStyles.h2Of(context).copyWith(
                              color: palette.error,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 18),
                    Divider(color: palette.div),
                    const SizedBox(height: 16),
                    _buildMetricRow(
                      context,
                      'Local Health Check',
                      localUrl,
                      isSuccess: verifyState.isLocalHealthy ? true : (verifyState.isVerifying ? null : false),
                      isChecking: verifyState.isVerifying && !verifyState.isLocalHealthy,
                    ),
                    if (lanUrl != null) ...[
                      const SizedBox(height: 12),
                      _buildMetricRow(
                        context,
                        'LAN Health Check',
                        lanUrl,
                        isSuccess: verifyState.isLanHealthy ? true : (verifyState.isVerifying ? null : false),
                        isChecking: verifyState.isVerifying && !verifyState.isLanHealthy,
                      ),
                    ],
                    const SizedBox(height: 12),
                    _buildMetricRow(
                      context,
                      'PostgreSQL & pgvector',
                      verifyState.healthStatus?.databaseStatus ??
                          (verifyState.isVerifying ? 'Checking...' : 'Disconnected'),
                      isSuccess: verifyState.healthStatus?.databaseStatus == 'connected'
                          ? true
                          : (verifyState.isVerifying ? null : false),
                      isChecking: verifyState.isVerifying &&
                          verifyState.healthStatus?.databaseStatus != 'connected',
                    ),
                    const SizedBox(height: 12),
                    _buildMetricRow(
                      context,
                      'Redis Cache & Queue',
                      verifyState.healthStatus?.redisStatus ??
                          (verifyState.isVerifying ? 'Checking...' : 'Disconnected'),
                      isSuccess: verifyState.healthStatus?.redisStatus == 'connected'
                          ? true
                          : (verifyState.isVerifying ? null : false),
                      isChecking: verifyState.isVerifying &&
                          verifyState.healthStatus?.redisStatus != 'connected',
                    ),
                  ],
                ),
              ),
              if (!verifyState.isVerifying && !verifyState.isSuccess) ...[
                const SizedBox(height: 16),
                Container(
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
                            'Health check failed',
                            style: AppTextStyles.h3Of(context).copyWith(color: palette.error),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        verifyState.errorMessage ?? 'Server failed to start in time or LAN connection was blocked.',
                        style: AppTextStyles.bodyMediumOf(context).copyWith(color: palette.text),
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
                      icon: Icons.refresh_rounded,
                      onPressed: () => verifyNotifier.verifyServer(),
                    ),
                    const SizedBox(width: 12),
                  ],
                  AppButton(
                    label: 'Continue',
                    icon: Icons.arrow_forward_rounded,
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

  Widget _buildMetricRow(
    BuildContext context,
    String label,
    String value, {
    bool? isSuccess,
    bool isChecking = false,
  }) {
    final palette = UnoPalette.of(context);

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: AppTextStyles.bodyMediumOf(context).copyWith(
            color: palette.textSec,
            fontSize: 13,
          ),
        ),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (isChecking) ...[
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(strokeWidth: 2, color: palette.accent),
              ),
              const SizedBox(width: 8),
            ] else if (isSuccess != null) ...[
              Icon(
                isSuccess ? Icons.check_circle_outline_rounded : Icons.cancel_outlined,
                size: 15,
                color: isSuccess ? palette.live : palette.error,
              ),
              const SizedBox(width: 6),
            ],
            Text(
              value,
              style: UnoTypography.mono(
                color: isChecking
                    ? palette.textSec
                    : isSuccess == true
                        ? palette.live
                        : isSuccess == false
                            ? palette.error
                            : palette.text,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
