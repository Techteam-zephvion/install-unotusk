import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../core/widgets/error_state_view.dart';
import '../../../../core/widgets/loading_state_view.dart';
import '../widgets/overview_attention_card.dart';
import '../widgets/overview_metric_strip.dart';
import '../workspace_controller.dart';

class OverviewTab extends ConsumerWidget {
  final String projectId;
  final String projectName;
  final void Function(int tabIndex)? onNavigateToTab;

  const OverviewTab({
    super.key,
    required this.projectId,
    required this.projectName,
    this.onNavigateToTab,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final contextAsync = ref.watch(projectContextProvider(projectId));
    final findingsAsync = ref.watch(projectCriticalFindingsProvider(projectId));

    return contextAsync.when(
      loading: () => const LoadingStateView(message: 'Loading project context...'),
      error: (err, stack) => ErrorStateView(
        message: err.toString(),
        onRetry: () {
          ref.invalidate(projectContextProvider(projectId));
          ref.invalidate(projectCriticalFindingsProvider(projectId));
        },
      ),
      data: (projectContext) {
        return SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. Metric Strip
              OverviewMetricStrip(context: projectContext),
              const SizedBox(height: 28),

              // 2. Needs Attention Section
              Text(
                'Needs attention',
                style: AppTextStyles.h2.copyWith(fontSize: 16, color: AppColors.slate900),
              ),
              const SizedBox(height: 12),
              findingsAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: LinearProgressIndicator(color: AppColors.slate400),
                ),
                error: (err, stack) => Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.slate50,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppColors.slate200),
                  ),
                  child: Text(
                    'Unable to load attention items: $err',
                    style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500),
                  ),
                ),
                data: (findings) {
                  if (findings.isEmpty) {
                    return Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.slate200),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle_outline, size: 18, color: AppColors.success),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              'No critical structural issues or circular dependencies detected.',
                              style: AppTextStyles.bodyMedium.copyWith(color: AppColors.slate700),
                            ),
                          ),
                        ],
                      ),
                    );
                  }

                  return Column(
                    children: findings.map((finding) {
                      return OverviewAttentionCard(
                        finding: finding,
                        onOpen: () {
                          // Navigate to Discoveries tab (tab 1)
                          onNavigateToTab?.call(1);
                        },
                      );
                    }).toList(),
                  );
                },
              ),
              const SizedBox(height: 28),

              // 3. Project Structure & Environment
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Language Distribution
                  Expanded(
                    flex: 3,
                    child: Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.slate200),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Language Distribution',
                            style: AppTextStyles.bodyMedium.copyWith(
                              fontWeight: FontWeight.w600,
                              color: AppColors.slate900,
                            ),
                          ),
                          const SizedBox(height: 14),
                          if (projectContext.metrics.languageDistribution.isEmpty)
                            Text('No files indexed yet', style: AppTextStyles.bodySmall)
                          else
                            ...projectContext.metrics.languageDistribution.entries.map((entry) {
                              final total = projectContext.metrics.totalFiles;
                              final pct = total > 0 ? (entry.value / total) : 0.0;
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 10),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text(
                                          entry.key,
                                          style: AppTextStyles.bodySmall.copyWith(
                                            fontWeight: FontWeight.w500,
                                            color: AppColors.slate800,
                                          ),
                                        ),
                                        Text(
                                          '${entry.value} files (${(pct * 100).toStringAsFixed(1)}%)',
                                          style: AppTextStyles.bodySmall.copyWith(
                                            color: AppColors.slate500,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(2),
                                      child: LinearProgressIndicator(
                                        value: pct,
                                        minHeight: 4,
                                        backgroundColor: AppColors.slate100,
                                        valueColor: const AlwaysStoppedAnimation<Color>(AppColors.slate700),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            }),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 20),

                  // Active Snapshot & Quick Actions
                  Expanded(
                    flex: 2,
                    child: Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.slate200),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Active Snapshot',
                            style: AppTextStyles.bodyMedium.copyWith(
                              fontWeight: FontWeight.w600,
                              color: AppColors.slate900,
                            ),
                          ),
                          const SizedBox(height: 12),
                          _DetailRow(
                            label: 'Branch',
                            value: projectContext.activeSnapshot?.branch ?? 'default',
                          ),
                          _DetailRow(
                            label: 'Commit',
                            value: projectContext.activeSnapshot?.commitHash.substring(0, 7) ?? 'latest',
                          ),
                          _DetailRow(
                            label: 'Status',
                            value: projectContext.activeSnapshot?.status ?? 'READY',
                          ),
                          const Divider(height: 24, color: AppColors.slate200),
                          Text(
                            'Explore Project',
                            style: AppTextStyles.bodySmall.copyWith(
                              fontWeight: FontWeight.w600,
                              color: AppColors.slate500,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              ActionChip(
                                label: const Text('Browse Files'),
                                avatar: const Icon(Icons.folder_outlined, size: 14),
                                onPressed: () => onNavigateToTab?.call(3),
                              ),
                              ActionChip(
                                label: const Text('Architecture'),
                                avatar: const Icon(Icons.account_tree_outlined, size: 14),
                                onPressed: () => onNavigateToTab?.call(2),
                              ),
                              ActionChip(
                                label: const Text('Ask / Search'),
                                avatar: const Icon(Icons.search, size: 14),
                                onPressed: () => onNavigateToTab?.call(5),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: AppTextStyles.bodySmall.copyWith(color: AppColors.slate500)),
          Text(
            value,
            style: AppTextStyles.code.copyWith(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppColors.slate900,
            ),
          ),
        ],
      ),
    );
  }
}
