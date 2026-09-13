import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

enum StatusType { success, warning, error, info, neutral }

class StatusBadge extends StatelessWidget {
  final String label;
  final StatusType type;
  final IconData? icon;

  const StatusBadge({
    super.key,
    required this.label,
    this.type = StatusType.neutral,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color text;

    switch (type) {
      case StatusType.success:
        bg = AppColors.successBg;
        border = AppColors.successBorder;
        text = AppColors.success;
        break;
      case StatusType.warning:
        bg = AppColors.warningBg;
        border = AppColors.warningBorder;
        text = AppColors.warning;
        break;
      case StatusType.error:
        bg = AppColors.errorBg;
        border = AppColors.errorBorder;
        text = AppColors.error;
        break;
      case StatusType.info:
        bg = AppColors.infoBg;
        border = AppColors.infoBorder;
        text = AppColors.info;
        break;
      case StatusType.neutral:
        bg = AppColors.slate100;
        border = AppColors.slate200;
        text = AppColors.slate600;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: text),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: AppTextStyles.bodySmall.copyWith(
              color: text,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
