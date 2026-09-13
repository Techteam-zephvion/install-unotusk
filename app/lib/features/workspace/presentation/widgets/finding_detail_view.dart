import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/project_finding.dart';
import '../../data/workspace_repository.dart';
import '../workspace_controller.dart';

class FindingDetailView extends ConsumerStatefulWidget {
  final String projectId;
  final ProjectFinding finding;
  final VoidCallback onClose;
  final void Function(ProjectFinding finding)? onAskAboutFinding;
  final void Function(String entity)? onNavigateToEntity;

  const FindingDetailView({
    super.key,
    required this.projectId,
    required this.finding,
    required this.onClose,
    this.onAskAboutFinding,
    this.onNavigateToEntity,
  });

  @override
  ConsumerState<FindingDetailView> createState() => _FindingDetailViewState();
}

class _FindingDetailViewState extends ConsumerState<FindingDetailView> {
  late ProjectFinding _currentFinding;
  bool _isUpdating = false;

  @override
  void initState() {
    super.initState();
    _currentFinding = widget.finding;
  }

  @override
  void didUpdateWidget(covariant FindingDetailView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.finding.id != widget.finding.id) {
      _currentFinding = widget.finding;
    }
  }

  Future<void> _updateStatus(String newStatus) async {
    setState(() {
      _isUpdating = true;
    });

    try {
      final updated = await ref
          .read(workspaceRepositoryProvider)
          .updateFindingStatus(widget.projectId, _currentFinding.id, newStatus);
      setState(() {
        _currentFinding = updated;
        _isUpdating = false;
      });
      // Invalidate findings lists to refresh UI
      ref.invalidate(projectCriticalFindingsProvider(widget.projectId));
    } catch (e) {
      setState(() {
        _isUpdating = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update status: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final finding = _currentFinding;
    final isCritical = finding.severity == 'CRITICAL';
    final isHigh = finding.severity == 'HIGH';

    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.slate200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.slate200)),
              ),
              child: Row(
                children: [
                  Expanded(
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
                              style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: finding.status == 'OPEN' ? AppColors.slate100 : AppColors.successBg,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                finding.status,
                                style: AppTextStyles.bodySmall.copyWith(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: finding.status == 'OPEN' ? AppColors.slate700 : AppColors.success,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          finding.title,
                          style: AppTextStyles.h2.copyWith(fontSize: 16, color: AppColors.slate900),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 16, color: AppColors.slate500),
                    onPressed: widget.onClose,
                  ),
                ],
              ),
            ),

            // Action Bar: Lifecycle buttons + Ask button
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              decoration: const BoxDecoration(
                color: AppColors.slate50,
                border: Border(bottom: BorderSide(color: AppColors.slate200)),
              ),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    if (finding.status == 'OPEN') ...[
                      _ActionButton(
                        label: 'Acknowledge',
                        isLoading: _isUpdating,
                        onPressed: () => _updateStatus('ACKNOWLEDGED'),
                      ),
                      const SizedBox(width: 8),
                      _ActionButton(
                        label: 'Resolve',
                        isLoading: _isUpdating,
                        onPressed: () => _updateStatus('RESOLVED'),
                      ),
                      const SizedBox(width: 8),
                      _ActionButton(
                        label: 'Dismiss',
                        isLoading: _isUpdating,
                        onPressed: () => _updateStatus('DISMISSED'),
                      ),
                    ] else ...[
                      _ActionButton(
                        label: 'Reopen Finding',
                        isLoading: _isUpdating,
                        onPressed: () => _updateStatus('OPEN'),
                      ),
                    ],
                    const SizedBox(width: 16),
                    OutlinedButton.icon(
                      onPressed: () => widget.onAskAboutFinding?.call(finding),
                      icon: const Icon(Icons.search, size: 14),
                      label: const Text('Ask about finding'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: AppColors.slate900,
                        side: const BorderSide(color: AppColors.slate300),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // Investigation Details
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  // Description
                  Text(
                    'What was detected',
                    style: AppTextStyles.bodyMedium.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.slate900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(finding.description, style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate700)),

                  const Divider(height: 28, color: AppColors.slate200),

                  // Why it matters
                  Text(
                    'Why it matters',
                    style: AppTextStyles.bodyMedium.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.slate900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(finding.whyItMatters, style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate700)),

                  const Divider(height: 28, color: AppColors.slate200),

                  // Recommendation
                  Text(
                    'Actionable Recommendation',
                    style: AppTextStyles.bodyMedium.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.slate900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(finding.recommendation, style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate700)),

                  if (finding.relatedEntities.isNotEmpty) ...[
                    const Divider(height: 28, color: AppColors.slate200),
                    Text(
                      'Affected Components / Files',
                      style: AppTextStyles.bodyMedium.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.slate900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: finding.relatedEntities.map((entity) {
                        return InkWell(
                          onTap: () => widget.onNavigateToEntity?.call(entity),
                          borderRadius: BorderRadius.circular(4),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: AppColors.slate100,
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: AppColors.slate200),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.insert_drive_file_outlined, size: 13, color: AppColors.primary),
                                const SizedBox(width: 6),
                                Text(
                                  entity,
                                  style: AppTextStyles.code.copyWith(
                                    fontSize: 12,
                                    color: AppColors.primary,
                                    decoration: TextDecoration.underline,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],

                  if (finding.evidence.isNotEmpty) ...[
                    const Divider(height: 28, color: AppColors.slate200),
                    Text(
                      'Supporting Evidence',
                      style: AppTextStyles.bodyMedium.copyWith(
                        fontWeight: FontWeight.w600,
                        color: AppColors.slate900,
                      ),
                    ),
                    const SizedBox(height: 10),
                    ...finding.evidence.map((item) {
                      final snippet = item['snippet'] ?? item['code'] ?? item['evidence_text'];
                      final filePath = item['file_path'] ?? item['file'];
                      final line = item['line_start'] ?? item['line_number'] ?? item['line'];

                      return Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.slate950,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: AppColors.slate800),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (filePath != null || line != null)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 6),
                                child: Text(
                                  '${filePath ?? ''}${line != null ? ' : line $line' : ''}',
                                  style: AppTextStyles.code.copyWith(
                                    fontSize: 11,
                                    color: AppColors.primaryMuted,
                                  ),
                                ),
                              ),
                            if (snippet != null)
                              Text(
                                snippet.toString(),
                                style: AppTextStyles.code.copyWith(
                                  fontSize: 12,
                                  color: AppColors.slate200,
                                ),
                              )
                            else
                              Text(
                                item.entries.map((e) => '${e.key}: ${e.value}').join(' • '),
                                style: AppTextStyles.code.copyWith(
                                  fontSize: 12,
                                  color: AppColors.slate200,
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
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final bool isLoading;
  final VoidCallback onPressed;

  const _ActionButton({
    required this.label,
    required this.isLoading,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: isLoading ? null : onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.slate900,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      ),
      child: Text(label, style: AppTextStyles.bodySmall.copyWith(color: Colors.white, fontWeight: FontWeight.w500)),
    );
  }
}
