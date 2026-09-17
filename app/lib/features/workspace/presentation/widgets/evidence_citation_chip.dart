import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/grounded_answer.dart';

class EvidenceCitationChip extends StatelessWidget {
  final EvidenceItem evidence;
  final void Function(String file, String? lines)? onTap;

  const EvidenceCitationChip({
    super.key,
    required this.evidence,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final hasLines = evidence.lines != null && evidence.lines!.isNotEmpty;
    final displayLabel = hasLines ? '${evidence.file}:${evidence.lines}' : evidence.file;

    return InkWell(
      onTap: () => onTap?.call(evidence.file, evidence.lines),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(
          color: AppColors.bgElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AppColors.divider),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.code, size: 12, color: AppColors.accent),
            const SizedBox(width: 6),
            Text(
              displayLabel,
              style: AppTextStyles.monoBadge.copyWith(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: AppColors.textPrimary,
              ),
            ),
            if (evidence.symbol != null) ...[
              const SizedBox(width: 6),
              Text(
                '• ${evidence.symbol}',
                style: AppTextStyles.monoBadge.copyWith(
                  fontSize: 11,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
