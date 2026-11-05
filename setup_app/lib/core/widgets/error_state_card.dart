import 'package:flutter/material.dart';
import '../theme/uno_palette.dart';
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
    final palette = UnoPalette.of(context);

    return Container(
      padding: const EdgeInsets.all(18),
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
              Expanded(
                child: Text(
                  title,
                  style: AppTextStyles.h3Of(context).copyWith(
                    color: palette.error,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            message,
            style: AppTextStyles.bodyMediumOf(context).copyWith(
              color: palette.text,
              fontSize: 13,
            ),
          ),
          if ((technicalLogs != null && technicalLogs!.isNotEmpty) || onRetry != null) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                if (technicalLogs != null && technicalLogs!.isNotEmpty)
                  TextButton.icon(
                    onPressed: () {
                      TechnicalDetailsDialog.show(
                        context,
                        title: title,
                        logs: technicalLogs!,
                      );
                    },
                    icon: Icon(Icons.terminal_rounded, size: 15, color: palette.textSec),
                    label: Text(
                      'View Logs',
                      style: AppTextStyles.labelOf(context).copyWith(color: palette.textSec),
                    ),
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      backgroundColor: palette.bgElevated,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                        side: BorderSide(color: palette.div),
                      ),
                    ),
                  ),
                const Spacer(),
                if (onRetry != null)
                  AppButton(
                    label: retryLabel,
                    variant: AppButtonVariant.secondary,
                    icon: Icons.refresh_rounded,
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
