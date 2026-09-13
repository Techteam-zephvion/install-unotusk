import 'package:flutter/material.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';
import 'app_button.dart';

class ErrorStateView extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;

  const ErrorStateView({
    super.key,
    required this.message,
    this.onRetry,
  });

  String get _cleanMessage {
    final lower = message.toLowerCase();
    if (lower.contains('connection refused') ||
        lower.contains('socketexception') ||
        lower.contains('failed to connect') ||
        lower.contains('connection error') ||
        lower.contains('connection timeout')) {
      return 'Unable to reach the Unotusk server. Please check your network or server address in Settings.';
    }
    if (lower.contains('401') || lower.contains('unauthorized')) {
      return 'Your session has expired. Please sign in again to continue.';
    }
    if (lower.contains('404') || lower.contains('not found')) {
      return 'The requested project or resource was not found.';
    }
    if (lower.contains('500') || lower.contains('internal server error')) {
      return 'The server encountered an issue processing the request.';
    }
    return message;
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 400),
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              size: 32,
              color: AppColors.error,
            ),
            const SizedBox(height: 12),
            Text(
              'Unable to load content',
              style: AppTextStyles.h3,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              _cleanMessage,
              style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate600),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 16),
              AppButton(
                text: 'Retry',
                onPressed: onRetry,
                variant: AppButtonVariant.secondary,
                icon: Icons.refresh,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
