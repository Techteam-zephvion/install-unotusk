import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../security/secret_sanitizer.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import 'app_button.dart';

class TechnicalDetailsDialog extends StatefulWidget {
  final String title;
  final String details;

  const TechnicalDetailsDialog({
    super.key,
    required this.title,
    required this.details,
  });

  static Future<void> show(BuildContext context, {required String title, required String details}) {
    return showDialog(
      context: context,
      builder: (context) => TechnicalDetailsDialog(title: title, details: details),
    );
  }

  @override
  State<TechnicalDetailsDialog> createState() => _TechnicalDetailsDialogState();
}

class _TechnicalDetailsDialogState extends State<TechnicalDetailsDialog> {
  bool _copied = false;

  @override
  Widget build(BuildContext context) {
    final sanitized = SecretSanitizer.sanitize(widget.details);

    return Dialog(
      backgroundColor: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 600, maxHeight: 500),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(widget.title, style: AppTextStyles.h2),
                  IconButton(
                    icon: const Icon(Icons.close, size: 18),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.slate900,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      sanitized,
                      style: AppTextStyles.code.copyWith(
                        color: AppColors.slate100,
                        fontSize: 11,
                        height: 1.4,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  AppButton(
                    label: _copied ? 'Copied' : 'Copy Logs',
                    variant: AppButtonVariant.secondary,
                    icon: _copied ? Icons.check : Icons.copy,
                    onPressed: () async {
                      await Clipboard.setData(ClipboardData(text: sanitized));
                      if (mounted) {
                        setState(() => _copied = true);
                        Future.delayed(const Duration(seconds: 2), () {
                          if (mounted) setState(() => _copied = false);
                        });
                      }
                    },
                  ),
                  const SizedBox(width: 8),
                  AppButton(
                    label: 'Close',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
