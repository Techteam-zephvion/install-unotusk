import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../security/secret_sanitizer.dart';
import '../theme/uno_palette.dart';
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

  static Future<void> show(
    BuildContext context, {
    required String title,
    String? details,
    String? logs,
  }) {
    final text = details ?? logs ?? '';
    return showDialog(
      context: context,
      builder: (context) => TechnicalDetailsDialog(title: title, details: text),
    );
  }

  @override
  State<TechnicalDetailsDialog> createState() => _TechnicalDetailsDialogState();
}

class _TechnicalDetailsDialogState extends State<TechnicalDetailsDialog> {
  bool _copied = false;

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);
    final sanitized = SecretSanitizer.sanitize(widget.details);

    return Dialog(
      backgroundColor: palette.bgSurface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: palette.div),
      ),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 620, maxHeight: 520),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(Icons.terminal_rounded, size: 20, color: palette.accent),
                      const SizedBox(width: 10),
                      Text(widget.title, style: AppTextStyles.h2Of(context)),
                    ],
                  ),
                  IconButton(
                    icon: Icon(Icons.close, size: 18, color: palette.textSec),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Expanded(
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF141412),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: palette.div),
                  ),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      sanitized,
                      style: UnoTypography.mono(
                        color: const Color(0xFFEDEDEB),
                        fontSize: 12,
                        letterSpacing: 0.3,
                        height: 1.5,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  AppButton(
                    label: _copied ? 'Copied' : 'Copy Logs',
                    variant: AppButtonVariant.secondary,
                    icon: _copied ? Icons.check : Icons.copy,
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: sanitized));
                      setState(() => _copied = true);
                      Future.delayed(const Duration(seconds: 2), () {
                        if (mounted) setState(() => _copied = false);
                      });
                    },
                  ),
                  AppButton(
                    label: 'Close',
                    variant: AppButtonVariant.primary,
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
