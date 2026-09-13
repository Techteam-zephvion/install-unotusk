import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_text_styles.dart';
import '../../domain/wizard_step.dart';

class WizardStepHeader extends StatelessWidget {
  final WizardStep currentStep;

  const WizardStepHeader({
    super.key,
    required this.currentStep,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(
          bottom: BorderSide(color: AppColors.slate200),
        ),
      ),
      child: Center(
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: WizardStep.values.map((step) {
              final isCurrent = step == currentStep;
              final isCompleted = step.index < currentStep.index;
              final stepNum = step.index + 1;

              Color badgeBg;
              Color badgeText;
              Color textColor;

              if (isCompleted) {
                badgeBg = AppColors.successBg;
                badgeText = AppColors.success;
                textColor = AppColors.slate700;
              } else if (isCurrent) {
                badgeBg = AppColors.primary;
                badgeText = Colors.white;
                textColor = AppColors.slate900;
              } else {
                badgeBg = AppColors.slate100;
                badgeText = AppColors.slate400;
                textColor = AppColors.slate400;
              }

              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      color: badgeBg,
                      shape: BoxShape.circle,
                      border: isCompleted
                          ? Border.all(color: AppColors.successBorder)
                          : null,
                    ),
                    child: Center(
                      child: isCompleted
                          ? const Icon(Icons.check, size: 12, color: AppColors.success)
                          : Text(
                              '$stepNum',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: badgeText,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    step.label,
                    style: AppTextStyles.label.copyWith(
                      color: textColor,
                      fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w500,
                    ),
                  ),
                  if (step.index < WizardStep.values.length - 1) ...[
                    const SizedBox(width: 6),
                    Container(
                      width: 12,
                      height: 1,
                      color: isCompleted ? AppColors.slate300 : AppColors.slate200,
                    ),
                    const SizedBox(width: 6),
                  ],
                ],
              );
            }).toList(),
          ),
        ),
      ),
    );
  }
}
