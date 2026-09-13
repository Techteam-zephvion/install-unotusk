import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../core/widgets/error_state_view.dart';
import '../../../../core/widgets/loading_state_view.dart';
import '../../domain/project_finding.dart';
import '../../data/workspace_repository.dart';
import '../widgets/finding_card.dart';
import '../widgets/finding_detail_view.dart';
import '../workspace_controller.dart';

class DiscoveriesTab extends ConsumerStatefulWidget {
  final String projectId;
  final String projectName;
  final void Function(int tabIndex)? onNavigateToTab;
  final void Function(String query)? onAskAboutFinding;
  final void Function(String entity)? onNavigateToEntity;

  const DiscoveriesTab({
    super.key,
    required this.projectId,
    required this.projectName,
    this.onNavigateToTab,
    this.onAskAboutFinding,
    this.onNavigateToEntity,
  });

  @override
  ConsumerState<DiscoveriesTab> createState() => _DiscoveriesTabState();
}

class _DiscoveriesTabState extends ConsumerState<DiscoveriesTab> {
  String? _selectedCategory;
  String? _selectedSeverity;
  ProjectFinding? _selectedFinding;
  bool _isAnalyzing = false;

  Future<void> _triggerAnalysis() async {
    setState(() {
      _isAnalyzing = true;
    });

    try {
      await ref.read(workspaceRepositoryProvider).triggerDiscovery(widget.projectId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Proactive discovery analysis triggered')),
        );
      }
      ref.invalidate(projectFindingsListProvider);
      ref.invalidate(projectDiscoverySummaryProvider(widget.projectId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to trigger analysis: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isAnalyzing = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final findingsAsync = ref.watch(
      projectFindingsListProvider((
        projectId: widget.projectId,
        category: _selectedCategory,
        severity: _selectedSeverity,
        status: null,
      )),
    );

    final summaryAsync = ref.watch(projectDiscoverySummaryProvider(widget.projectId));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header & Controls
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Project Discoveries',
                    style: AppTextStyles.h2.copyWith(fontSize: 16, color: AppColors.slate900),
                  ),
                  const SizedBox(height: 2),
                  summaryAsync.when(
                    loading: () => Text('Loading summary...', style: AppTextStyles.bodySmall),
                    error: (e, s) => Text('Discoveries feed', style: AppTextStyles.bodySmall),
                    data: (summary) => Text(
                      '${summary.totalFindings} findings • ${summary.criticalCount} critical, ${summary.highCount} high',
                      style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),

            // Severity Filter Dropdown
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppColors.slate200),
              ),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String?>(
                  value: _selectedSeverity,
                  hint: Text('All Severities', style: AppTextStyles.bodySmall),
                  style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate800),
                  items: const [
                    DropdownMenuItem(value: null, child: Text('All Severities')),
                    DropdownMenuItem(value: 'CRITICAL', child: Text('Critical')),
                    DropdownMenuItem(value: 'HIGH', child: Text('High')),
                    DropdownMenuItem(value: 'MEDIUM', child: Text('Medium')),
                    DropdownMenuItem(value: 'LOW', child: Text('Low')),
                  ],
                  onChanged: (val) {
                    setState(() {
                      _selectedSeverity = val;
                    });
                  },
                ),
              ),
            ),
            const SizedBox(width: 12),

            // Run Analysis Button
            OutlinedButton.icon(
              onPressed: _isAnalyzing ? null : _triggerAnalysis,
              icon: _isAnalyzing
                  ? const SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.slate700),
                    )
                  : const Icon(Icons.refresh, size: 14),
              label: Text(_isAnalyzing ? 'Analyzing...' : 'Run Analysis'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.slate900,
                side: const BorderSide(color: AppColors.slate300),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Split Pane: Left Feed | Right Investigation
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Left Feed
              Expanded(
                flex: 4,
                child: findingsAsync.when(
                  loading: () => const LoadingStateView(message: 'Loading findings...'),
                  error: (err, stack) => ErrorStateView(
                    message: err.toString(),
                    onRetry: () => ref.invalidate(projectFindingsListProvider),
                  ),
                  data: (findings) {
                    if (findings.isEmpty) {
                      return Container(
                        padding: const EdgeInsets.all(32),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.slate200),
                        ),
                        child: Center(
                          child: Text(
                            'No findings matching the selected filters.',
                            style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate500),
                          ),
                        ),
                      );
                    }

                    return ListView.builder(
                      itemCount: findings.length,
                      itemBuilder: (context, index) {
                        final finding = findings[index];
                        final isSelected = _selectedFinding?.id == finding.id;

                        return FindingCard(
                          finding: finding,
                          isSelected: isSelected,
                          onTap: () {
                            setState(() {
                              _selectedFinding = finding;
                            });
                          },
                        );
                      },
                    );
                  },
                ),
              ),
              const SizedBox(width: 16),

              // Right Investigation Pane
              Expanded(
                flex: 6,
                child: _selectedFinding != null
                    ? FindingDetailView(
                        projectId: widget.projectId,
                        finding: _selectedFinding!,
                        onClose: () {
                          setState(() {
                            _selectedFinding = null;
                          });
                        },
                        onAskAboutFinding: (f) {
                          if (widget.onAskAboutFinding != null) {
                            widget.onAskAboutFinding!('What causes ${f.title}? How can we resolve it?');
                          } else {
                            widget.onNavigateToTab?.call(5);
                          }
                        },
                        onNavigateToEntity: (entity) {
                          if (widget.onNavigateToEntity != null) {
                            widget.onNavigateToEntity!(entity);
                          } else {
                            widget.onNavigateToTab?.call(3);
                          }
                        },
                      )
                    : Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppColors.slate200),
                        ),
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.find_in_page_outlined,
                                size: 36,
                                color: AppColors.slate300,
                              ),
                              const SizedBox(height: 12),
                              Text(
                                'Select a finding to investigate',
                                style: AppTextStyles.h2.copyWith(fontSize: 15, color: AppColors.slate700),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Review supporting evidence, affected components, and recommendations.',
                                style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate400),
                              ),
                            ],
                          ),
                        ),
                      ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
