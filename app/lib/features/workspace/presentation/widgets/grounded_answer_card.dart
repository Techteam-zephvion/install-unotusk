import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/grounded_answer.dart';
import 'evidence_citation_chip.dart';

class GroundedAnswerCard extends StatelessWidget {
  final String question;
  final GroundedAnswer answer;
  final void Function(String file, String? lines)? onCitationTap;

  const GroundedAnswerCard({
    super.key,
    required this.question,
    required this.answer,
    this.onCitationTap,
  });

  @override
  Widget build(BuildContext context) {
    final isConfirmed = answer.evidence.isNotEmpty;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Question Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.bgElevated,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(8),
                topRight: Radius.circular(8),
              ),
              border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outline)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.help_outline, size: 15, color: AppColors.accent),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    question,
                    style: AppTextStyles.h2.copyWith(fontSize: 14),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: isConfirmed ? AppColors.confirmedBg : AppColors.inferredBg,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isConfirmed
                          ? AppColors.confirmed.withOpacity(0.35)
                          : AppColors.inferred.withOpacity(0.35),
                    ),
                  ),
                  child: Text(
                    isConfirmed ? '[CONFIRMED]' : '[INFERRED]',
                    style: AppTextStyles.monoBadge.copyWith(
                      fontSize: 9,
                      fontWeight: FontWeight.bold,
                      color: isConfirmed ? AppColors.confirmed : AppColors.inferred,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Grounded Answer Body
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Text Explanation
                Text(
                  answer.content,
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.textPrimary,
                    height: 1.55,
                  ),
                ),

                // Citations & Evidence Section
                if (answer.evidence.isNotEmpty) ...[
                  Divider(height: 24, color: Theme.of(context).colorScheme.outline),
                  Text(
                    'Supporting Evidence & Citations',
                    style: AppTextStyles.monoBadge.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: answer.evidence.map((evidence) {
                      return EvidenceCitationChip(
                        evidence: evidence,
                        onTap: onCitationTap,
                      );
                    }).toList(),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
