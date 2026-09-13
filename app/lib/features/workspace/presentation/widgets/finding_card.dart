import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/project_finding.dart';

class FindingCard extends StatelessWidget {
  final ProjectFinding finding;
  final bool isSelected;
  final VoidCallback onTap;

  const FindingCard({
    super.key,
    required this.finding,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isCritical = finding.severity == 'CRITICAL';
    final isHigh = finding.severity == 'HIGH';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: isSelected ? AppColors.slate100 : Colors.white,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: isSelected ? AppColors.slate400 : AppColors.slate200,
        ),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: isCritical
                          ? AppColors.errorBg
                          : isHigh
                              ? AppColors.warningBg
                              : AppColors.slate100,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      finding.severity,
                      style: AppTextStyles.bodySmall.copyWith(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: isCritical
                            ? AppColors.error
                            : isHigh
                                ? AppColors.warning
                                : AppColors.slate700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    finding.category,
                    style: AppTextStyles.bodySmall.copyWith(
                      fontSize: 11,
                      color: AppColors.slate500,
                    ),
                  ),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    decoration: BoxDecoration(
                      color: finding.status == 'OPEN' ? AppColors.slate100 : AppColors.successBg,
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      finding.status,
                      style: AppTextStyles.bodySmall.copyWith(
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        color: finding.status == 'OPEN' ? AppColors.slate600 : AppColors.success,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                finding.title,
                style: AppTextStyles.bodyMedium.copyWith(
                  fontWeight: FontWeight.w600,
                  color: AppColors.slate900,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                finding.description,
                style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate600),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
