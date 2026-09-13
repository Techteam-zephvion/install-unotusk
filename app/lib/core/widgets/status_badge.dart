import 'package:flutter/material.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';

enum BadgeVariant { success, warning, error, info, neutral }

class StatusBadge extends StatelessWidget {
  final String label;
  final BadgeVariant variant;

  const StatusBadge({
    super.key,
    required this.label,
    this.variant = BadgeVariant.neutral,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color text;

    switch (variant) {
      case BadgeVariant.success:
        bg = AppColors.successBg;
        border = AppColors.successBorder;
        text = AppColors.success;
        break;
      case BadgeVariant.warning:
        bg = AppColors.warningBg;
        border = AppColors.warningBorder;
        text = AppColors.warning;
        break;
      case BadgeVariant.error:
        bg = AppColors.errorBg;
        border = AppColors.errorBorder;
        text = AppColors.error;
        break;
      case BadgeVariant.info:
        bg = AppColors.infoBg;
        border = AppColors.infoBorder;
        text = AppColors.info;
        break;
      case BadgeVariant.neutral:
        bg = AppColors.slate100;
        border = AppColors.slate300;
        text = AppColors.slate700;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: border),
      ),
      child: Text(
        label,
        style: AppTextStyles.bodySmall.copyWith(
          color: text,
          fontWeight: FontWeight.w600,
          fontSize: 11,
        ),
      ),
    );
  }
}
