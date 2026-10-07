import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/repository_context.dart';

class OverviewMetricStrip extends StatelessWidget {
  final ProjectRepositoryContext context;

  const OverviewMetricStrip({super.key, required this.context});

  @override
  Widget build(BuildContext context) {
    final metrics = this.context.metrics;
    final primaryLang = metrics.languageDistribution.isNotEmpty
        ? metrics.languageDistribution.entries.reduce((a, b) => a.value > b.value ? a : b).key
        : 'Unknown';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Row(
        children: [
          _MetricItem(
            label: 'Project Type',
            value: '$primaryLang Project',
            subtitle: '${metrics.languagesCount} languages detected',
            isAccent: true,
          ),
          const _VerticalDivider(),
          _MetricItem(
            label: 'Files',
            value: '${metrics.totalFiles}',
            subtitle: 'Tracked in snapshot',
          ),
          const _VerticalDivider(),
          _MetricItem(
            label: 'Symbols',
            value: '${metrics.symbolsCount}',
            subtitle: 'Classes & functions',
          ),
          const _VerticalDivider(),
          _MetricItem(
            label: 'Dependencies',
            value: '${metrics.dependenciesCount}',
            subtitle: 'Internal & external',
          ),
        ],
      ),
    );
  }
}

class _MetricItem extends StatelessWidget {
  final String label;
  final String value;
  final String subtitle;
  final bool isAccent;

  const _MetricItem({
    required this.label,
    required this.value,
    required this.subtitle,
    this.isAccent = false,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTextStyles.monoBadge.copyWith(
              fontSize: 11,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: AppTextStyles.h2.copyWith(
              fontSize: 18,
              color: isAccent ? AppColors.accent : AppColors.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              fontSize: 11,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _VerticalDivider extends StatelessWidget {
  const _VerticalDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 42,
      width: 1,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      color: Theme.of(context).colorScheme.outline,
    );
  }
}
