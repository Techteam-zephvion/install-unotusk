import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import 'app_button.dart';
import 'technical_details_dialog.dart';

class ErrorStateCard extends StatelessWidget {
  final String title;
  final String message;
  final String? technicalLogs;
  final VoidCallback? onRetry;
  final String retryLabel;

  const ErrorStateCard({
    super.key,
    required this.title,
    required this.message,
    this.technicalLogs,
    this.onRetry,
    this.retryLabel = 'Retry',
  });

  @override
  Widget build(BuildContext context) {
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
              Expanded(
                child: Text(
                  title,
                  style: AppTextStyles.h3.copyWith(color: AppColors.error),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            message,
            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate800),
          ),
          if (technicalLogs != null && technicalLogs!.isNotEmpty || onRetry != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                if (technicalLogs != null && technicalLogs!.isNotEmpty)
                  TextButton.icon(
                    onPressed: () {
                      TechnicalDetailsDialog.show(
                        context,
                        title: '$title — Diagnostics',
                        details: technicalLogs!,
                      );
                    },
                    icon: const Icon(Icons.terminal, size: 14),
                    label: const Text('View technical details'),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.slate700,
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    ),
                  ),
                const Spacer(),
                if (onRetry != null)
                  AppButton(
                    label: retryLabel,
                    icon: Icons.refresh,
                    variant: AppButtonVariant.primary,
                    onPressed: onRetry,
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
