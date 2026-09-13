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
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.slate200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Question Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: AppColors.slate50,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(8),
                topRight: Radius.circular(8),
              ),
              border: Border(bottom: BorderSide(color: AppColors.slate200)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.help_outline, size: 16, color: AppColors.slate600),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    question,
                    style: AppTextStyles.h2.copyWith(fontSize: 14, color: AppColors.slate900),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.slate200,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'GROUNDED',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: AppColors.slate700,
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
                    color: AppColors.slate800,
                    height: 1.5,
                  ),
                ),

                // Citations & Evidence Section
                if (answer.evidence.isNotEmpty) ...[
                  const Divider(height: 24, color: AppColors.slate200),
                  Text(
                    'Supporting Evidence & Citations',
                    style: AppTextStyles.bodySmall.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.slate700,
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

                  // Snippets if present
                  ...answer.evidence.where((e) => e.snippet != null && e.snippet!.isNotEmpty).map((e) {
                    return Container(
                      margin: const EdgeInsets.only(top: 8),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.slate950,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppColors.slate800),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${e.file}${e.lines != null ? ':${e.lines}' : ''}',
                            style: AppTextStyles.code.copyWith(
                              fontSize: 11,
                              color: AppColors.primaryMuted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            e.snippet!,
                            style: AppTextStyles.code.copyWith(
                              fontSize: 12,
                              color: AppColors.slate100,
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
