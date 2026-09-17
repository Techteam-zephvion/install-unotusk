import 'package:flutter/material.dart';
import '../../app/theme/app_colors.dart';
import '../../app/theme/app_text_styles.dart';

enum BadgeVariant { success, warning, error, info, neutral, confirmed, inferred }

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
        bg = AppColors.liveBg;
        border = AppColors.live.withOpacity(0.35);
        text = AppColors.live;
        break;
      case BadgeVariant.warning:
        bg = AppColors.warningBg;
        border = AppColors.warning.withOpacity(0.35);
        text = AppColors.warning;
        break;
      case BadgeVariant.error:
        bg = AppColors.errorBg;
        border = AppColors.error.withOpacity(0.35);
        text = AppColors.error;
        break;
      case BadgeVariant.info:
        bg = AppColors.infoBg;
        border = AppColors.info.withOpacity(0.35);
        text = AppColors.info;
        break;
      case BadgeVariant.confirmed:
        bg = AppColors.confirmedBg;
        border = AppColors.confirmed.withOpacity(0.4);
        text = AppColors.confirmed;
        break;
      case BadgeVariant.inferred:
        bg = AppColors.inferredBg;
        border = AppColors.inferred.withOpacity(0.4);
        text = AppColors.inferred;
        break;
      case BadgeVariant.neutral:
        bg = AppColors.bgElevated;
        border = AppColors.divider;
        text = AppColors.textSecondary;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12), // Pill shape matching Figma
        border: Border.all(color: border),
      ),
      child: Text(
        label,
        style: AppTextStyles.monoBadge.copyWith(
          color: text,
          fontSize: 10,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
