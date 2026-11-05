import 'package:flutter/material.dart';
import '../theme/uno_palette.dart';
import '../theme/app_text_styles.dart';

enum StatusType { success, warning, error, info, neutral, accent }

class StatusBadge extends StatelessWidget {
  final String label;
  final StatusType type;
  final IconData? icon;
  final bool isPill;

  const StatusBadge({
    super.key,
    required this.label,
    this.type = StatusType.neutral,
    this.icon,
    this.isPill = false,
  });

  const StatusBadge.pill({
    super.key,
    required this.label,
    this.type = StatusType.accent,
    this.icon,
  }) : isPill = true;

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);

    Color bg;
    Color border;
    Color text;

    switch (type) {
      case StatusType.success:
        bg = palette.live.withValues(alpha: 0.12);
        border = palette.live.withValues(alpha: 0.35);
        text = palette.live;
        break;
      case StatusType.warning:
        bg = palette.warn.withValues(alpha: 0.12);
        border = palette.warn.withValues(alpha: 0.35);
        text = palette.warn;
        break;
      case StatusType.error:
        bg = palette.error.withValues(alpha: 0.12);
        border = palette.error.withValues(alpha: 0.35);
        text = palette.error;
        break;
      case StatusType.info:
        bg = palette.neutral.withValues(alpha: 0.12);
        border = palette.neutral.withValues(alpha: 0.35);
        text = palette.neutral;
        break;
      case StatusType.accent:
        bg = palette.accent.withValues(alpha: 0.12);
        border = palette.accent.withValues(alpha: 0.35);
        text = palette.accent;
        break;
      case StatusType.neutral:
        bg = palette.bgElevated;
        border = palette.div;
        text = palette.textSec;
        break;
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isPill ? 10 : 8,
        vertical: isPill ? 4 : 3,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(isPill ? 16 : 6),
        border: Border.all(color: border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: isPill ? 13 : 12, color: text),
            const SizedBox(width: 5),
          ],
          Text(
            label,
            style: AppTextStyles.labelOf(context).copyWith(
              color: text,
              fontSize: isPill ? 11.5 : 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
    );
  }
}
