import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class BDDTestCase {
  final int id;
  final String desc;
  const BDDTestCase({required this.id, required this.desc});
}

class BDDRiskItem {
  final String tag; // CONFIRMED or INFERRED
  final String text;
  const BDDRiskItem({required this.tag, required this.text});
}

class BDDContractData {
  final String given;
  final String when;
  final String then;
  final String kpi;
  final String kpiTag;
  final String? kpiNote;
  final List<BDDTestCase> testCases;
  final List<BDDRiskItem> risks;

  const BDDContractData({
    required this.given,
    required this.when,
    required this.then,
    required this.kpi,
    required this.kpiTag,
    this.kpiNote,
    required this.testCases,
    required this.risks,
  });
}

class BDDContractCard extends StatelessWidget {
  final BDDContractData bdd;

  const BDDContractCard({
    super.key,
    required this.bdd,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: AppColors.bgSurface,
        border: Border.all(color: AppColors.divider),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.bgElevated,
          border: Border.all(color: AppColors.divider),
          borderRadius: BorderRadius.circular(12),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
              decoration: const BoxDecoration(
                color: AppColors.bgSurface,
                border: Border(bottom: BorderSide(color: AppColors.divider)),
              ),
              child: Row(
                children: [
                  Text(
                    'BDD Intent Contract',
                    style: AppTextStyles.instrumentSerif(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: 10),
                  _buildBadge('COLD TIER', AppColors.modeCold, AppColors.modeCold.withValues(alpha: 0.15)),
                  const SizedBox(width: 8),
                  _buildBadge('CONFIRMED', AppColors.confirmed, AppColors.confirmed.withValues(alpha: 0.15)),
                  const Spacer(),
                  Text(
                    'Verified Artifact',
                    style: AppTextStyles.monoBadge,
                  ),
                ],
              ),
            ),

            // Given section
            _buildSection('GIVEN', bdd.given),
            _buildSection('WHEN', bdd.when),
            _buildSection('THEN', bdd.then),

            // Suggested KPI
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.divider)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('SUGGESTED KPI', style: _labelStyle),
                  const SizedBox(height: 6),
                  RichText(
                    text: TextSpan(
                      style: AppTextStyles.body,
                      children: [
                        TextSpan(text: '${bdd.kpi} '),
                        TextSpan(
                          text: '[${bdd.kpiTag}${bdd.kpiNote != null ? " — ${bdd.kpiNote}" : ""}]',
                          style: AppTextStyles.mono(
                            fontSize: 11,
                            color: AppColors.inferred,
                            letterSpacing: 0.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Test Cases
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.divider)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('TEST CASES', style: _labelStyle),
                  const SizedBox(height: 10),
                  ...bdd.testCases.map((tc) => Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.bgSurface,
                          border: Border.all(color: AppColors.divider),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '0${tc.id}',
                              style: AppTextStyles.mono(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: AppColors.accent,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                tc.desc,
                                style: AppTextStyles.inter(fontSize: 13, height: 1.5),
                              ),
                            ),
                          ],
                        ),
                      )),
                ],
              ),
            ),

            // Risk Report
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('RISK REPORT', style: _labelStyle),
                  const SizedBox(height: 8),
                  ...bdd.risks.map((r) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: (r.tag == 'CONFIRMED' ? AppColors.confirmed : AppColors.inferred)
                                    .withValues(alpha: 0.16),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                '[${r.tag}]',
                                style: AppTextStyles.mono(
                                  fontSize: 10,
                                  color: r.tag == 'CONFIRMED' ? AppColors.confirmed : AppColors.inferred,
                                  letterSpacing: 0.4,
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                r.text,
                                style: AppTextStyles.inter(fontSize: 13, height: 1.5),
                              ),
                            ),
                          ],
                        ),
                      )),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSection(String label, String content) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.divider)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: _labelStyle),
          const SizedBox(height: 6),
          Text(content, style: AppTextStyles.body),
        ],
      ),
    );
  }

  Widget _buildBadge(String text, Color color, Color bg) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: AppTextStyles.mono(
          fontSize: 9,
          fontWeight: FontWeight.w600,
          color: color,
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  TextStyle get _labelStyle => AppTextStyles.mono(
        fontSize: 10,
        fontWeight: FontWeight.w600,
        color: AppColors.accent,
        letterSpacing: 0.8,
      );
}
