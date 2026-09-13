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
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.slate200),
      ),
      child: Row(
        children: [
          _MetricItem(
            label: 'Project Type',
            value: '$primaryLang Project',
            subtitle: '${metrics.languagesCount} languages detected',
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

  const _MetricItem({
    required this.label,
    required this.value,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: AppTextStyles.label.copyWith(
              fontSize: 12,
              color: AppColors.slate500,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: AppTextStyles.h2.copyWith(
              fontSize: 18,
              color: AppColors.slate900,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            subtitle,
            style: AppTextStyles.bodySmall.copyWith(
              fontSize: 12,
              color: AppColors.slate500,
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
      height: 36,
      width: 1,
      color: AppColors.slate200,
      margin: const EdgeInsets.symmetric(horizontal: 16),
    );
  }
}
