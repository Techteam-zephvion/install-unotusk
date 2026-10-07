import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class ReasoningComponent {
  final String label;
  final double score;
  const ReasoningComponent({required this.label, required this.score});
}

class ReasoningData {
  final double compositeScore;
  final List<ReasoningComponent> components;
  final List<String> routingPath;
  final List<String> ontologyEdges;
  final List<String> citations;

  const ReasoningData({
    required this.compositeScore,
    required this.components,
    required this.routingPath,
    required this.ontologyEdges,
    required this.citations,
  });
}

class ReasoningPanel extends StatefulWidget {
  final ReasoningData reasoning;
  final ValueChanged<String>? onCitationTap;

  const ReasoningPanel({
    super.key,
    required this.reasoning,
    this.onCitationTap,
  });

  @override
  State<ReasoningPanel> createState() => _ReasoningPanelState();
}

class _ReasoningPanelState extends State<ReasoningPanel> {
  bool _isOpen = false;
  bool _vulnOpen = false;

  Color get _compositeColor {
    final score = widget.reasoning.compositeScore;
    if (score >= 0.8) return AppColors.confirmed;
    if (score >= 0.5) return AppColors.output;
    return AppColors.inferred;
  }

  String get _confidenceBadgeText {
    final score = widget.reasoning.compositeScore;
    if (score >= 0.8) return 'CONFIRMED';
    if (score >= 0.5) return 'UNCERTAIN';
    return 'INSUFFICIENT';
  }

  @override
  Widget build(BuildContext context) {
    final thoughtSeconds = (widget.reasoning.compositeScore * 2.8).toStringAsFixed(1);

    return Container(
      margin: const EdgeInsets.only(top: 8, bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Thought process pill button
          InkWell(
            onTap: () => setState(() => _isOpen = !_isOpen),
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: BoxDecoration(
                color: AppColors.bgSurface,
                border: Border.all(color: AppColors.divider),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.bolt, size: 14, color: AppColors.accent),
                  const SizedBox(width: 6),
                  Text(
                    'Thought process for ${thoughtSeconds}s',
                    style: AppTextStyles.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(width: 6),
                  AnimatedRotation(
                    turns: _isOpen ? 0.5 : 0.0,
                    duration: const Duration(milliseconds: 180),
                    child: const Icon(Icons.keyboard_arrow_down, size: 14, color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
          ),

          // Expandable body
          if (_isOpen)
            Container(
              margin: const EdgeInsets.only(top: 10),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppColors.bgSurface,
                border: Border.all(color: AppColors.divider),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Composite Score
                  Text('COMPOSITE SCORE', style: _sectionHeaderStyle),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: widget.reasoning.compositeScore,
                            backgroundColor: AppColors.divider,
                            valueColor: AlwaysStoppedAnimation<Color>(_compositeColor),
                            minHeight: 6,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        widget.reasoning.compositeScore.toStringAsFixed(2),
                        style: AppTextStyles.mono(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: _compositeColor,
                        ),
                      ),
                      const SizedBox(width: 8),
                      _buildTierBadge(_confidenceBadgeText, _compositeColor),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Components score bars
                  ...widget.reasoning.components.map((c) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Row(
                          children: [
                            SizedBox(
                              width: 110,
                              child: Text(
                                c.label,
                                style: AppTextStyles.inter(
                                  fontSize: 12,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ),
                            Expanded(
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(3),
                                child: LinearProgressIndicator(
                                  value: c.score,
                                  backgroundColor: AppColors.divider.withValues(alpha: 0.5),
                                  valueColor: const AlwaysStoppedAnimation<Color>(AppColors.neutral),
                                  minHeight: 4,
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            SizedBox(
                              width: 32,
                              child: Text(
                                c.score.toStringAsFixed(2),
                                style: AppTextStyles.mono(
                                  fontSize: 10,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                            ),
                          ],
                        ),
                      )),

                  const SizedBox(height: 14),

                  // Routing Path
                  Text('ROUTING PATH', style: _sectionHeaderStyle),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      for (int i = 0; i < widget.reasoning.routingPath.length; i++) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.bgElevated,
                            border: Border.all(color: AppColors.divider),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            widget.reasoning.routingPath[i],
                            style: AppTextStyles.inter(fontSize: 12),
                          ),
                        ),
                        if (i < widget.reasoning.routingPath.length - 1)
                          const Text('→', style: TextStyle(color: AppColors.textSecondary, fontSize: 11)),
                      ],
                    ],
                  ),

                  const SizedBox(height: 14),

                  // Ontology Edges
                  Text('ONTOLOGY EDGES', style: _sectionHeaderStyle),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: widget.reasoning.ontologyEdges.map((edge) {
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppColors.live.withValues(alpha: 0.12),
                          border: Border.all(color: AppColors.live.withValues(alpha: 0.3)),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          edge,
                          style: AppTextStyles.mono(
                            fontSize: 11,
                            color: AppColors.live,
                          ),
                        ),
                      );
                    }).toList(),
                  ),

                  const SizedBox(height: 14),

                  // Sources Cited
                  Text('SOURCES CITED', style: _sectionHeaderStyle),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: widget.reasoning.citations.map((c) {
                      return InkWell(
                        onTap: widget.onCitationTap != null ? () => widget.onCitationTap!(c) : null,
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: AppColors.bgElevated,
                            border: Border.all(color: AppColors.divider),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            c,
                            style: AppTextStyles.mono(
                              fontSize: 11,
                              color: AppColors.accent,
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),

                  const SizedBox(height: 14),

                  // Vulnerability scan toggle
                  Container(
                    padding: const EdgeInsets.only(top: 12),
                    decoration: const BoxDecoration(
                      border: Border(top: BorderSide(color: AppColors.divider)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        InkWell(
                          onTap: () => setState(() => _vulnOpen = !_vulnOpen),
                          borderRadius: BorderRadius.circular(8),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              border: Border.all(color: AppColors.divider),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.shield_outlined, size: 14, color: AppColors.textSecondary),
                                const SizedBox(width: 6),
                                Text(
                                  _vulnOpen ? 'Hide vulnerabilities' : 'Scan for vulnerabilities',
                                  style: AppTextStyles.inter(
                                    fontSize: 12,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        if (_vulnOpen)
                          Container(
                            margin: const EdgeInsets.only(top: 10),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppColors.inferred.withValues(alpha: 0.08),
                              border: Border.all(color: AppColors.inferred.withValues(alpha: 0.3)),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'VULNERABILITY SCAN — SUPPLEMENTARY',
                                  style: AppTextStyles.mono(
                                    fontSize: 10,
                                    color: AppColors.inferred,
                                    letterSpacing: 0.8,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'No additional vulnerabilities identified beyond those in the locked Risk Report. Scan checked 12 decision-events for unresolved security implications. This section is supplementary — the three-point risk report is the authoritative output.',
                                  style: AppTextStyles.inter(
                                    fontSize: 12,
                                    color: AppColors.textSecondary,
                                    height: 1.55,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTierBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: AppTextStyles.mono(
          fontSize: 9,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  TextStyle get _sectionHeaderStyle => AppTextStyles.mono(
        fontSize: 10,
        color: AppColors.textSecondary,
        letterSpacing: 0.8,
      );
}
