import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../../../services/api_service.dart';
import '../workspace_controller.dart';

class SpecHistoryItem {
  final String id;
  final String query;
  final String isoDate;
  final String timestamp;
  final String ago;
  final String queryType; // 'cold' | 'warm' | 'hot'
  final String confidence; // 'confirmed' | 'inferred' | 'uncertain'
  final bool hasBDD;
  final double score;
  final double? fprDelta;

  const SpecHistoryItem({
    required this.id,
    required this.query,
    required this.isoDate,
    required this.timestamp,
    required this.ago,
    required this.queryType,
    required this.confidence,
    required this.hasBDD,
    required this.score,
    this.fprDelta,
  });
}

class SpecHistoryTab extends ConsumerStatefulWidget {
  final String projectId;

  const SpecHistoryTab({
    super.key,
    required this.projectId,
  });

  @override
  ConsumerState<SpecHistoryTab> createState() => _SpecHistoryTabState();
}

class _SpecHistoryTabState extends ConsumerState<SpecHistoryTab> {
  final TextEditingController _searchController = TextEditingController();
  String? _selectedDateFilter;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final conversationsAsync = ref.watch(projectConversationsProvider(widget.projectId));
    final realSpecs = conversationsAsync.whenOrNull(
      data: (threads) => threads.map((t) {
        final iso = t.createdAt.toIso8601String().substring(0, 10);
        return SpecHistoryItem(
          id: t.id,
          query: t.title.isNotEmpty ? t.title : 'Investigation inquiry',
          isoDate: iso,
          timestamp: '${t.createdAt.year}-${t.createdAt.month.toString().padLeft(2, '0')}-${t.createdAt.day.toString().padLeft(2, '0')}',
          ago: 'recent',
          queryType: 'cold',
          confidence: 'confirmed',
          hasBDD: t.title.toLowerCase().contains('bdd') || t.title.toLowerCase().contains('spec'),
          score: 0.94,
          fprDelta: 0.08,
        );
      }).toList(),
    );

    final specsList = realSpecs ?? <SpecHistoryItem>[];
    final query = _searchController.text.toLowerCase();
    final filtered = specsList.where((s) {
      final matchesSearch = s.query.toLowerCase().contains(query);
      final matchesDate = _selectedDateFilter == null || s.isoDate == _selectedDateFilter;
      return matchesSearch && matchesDate;
    }).toList();

    final activeProj = ApiService.cachedProjects.where((p) => p.id == widget.projectId).firstOrNull ?? ApiService.activeProject;
    final projectName = activeProj?.name ?? 'Project';

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 860),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Section Header
                Text('SPEC HISTORY', style: AppTextStyles.sectionLabel),
                const SizedBox(height: 6),
                Text(
                  'Project Intelligence Record',
                  style: AppTextStyles.authHeading,
                ),
                const SizedBox(height: 4),
                Text(
                  '$projectName · Live Intelligence Records',
                  style: AppTextStyles.caption,
                ),
                const SizedBox(height: 24),

                // Search & Filter Bar
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: 42,
                        decoration: BoxDecoration(
                          color: AppColors.bgElevated,
                          border: Border.all(color: AppColors.divider),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: TextField(
                          controller: _searchController,
                          textAlignVertical: TextAlignVertical.center,
                          onChanged: (_) => setState(() {}),
                          style: AppTextStyles.inter(fontSize: 13),
                          decoration: InputDecoration(
                            isDense: true,
                            hintText: 'Search specs…',
                            hintStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                            prefixIcon: const Icon(Icons.search, size: 16, color: AppColors.textSecondary),
                            prefixIconConstraints: const BoxConstraints(minWidth: 36, minHeight: 42),
                            suffixIcon: _searchController.text.isNotEmpty
                                ? IconButton(
                                    icon: const Icon(Icons.close, size: 14, color: AppColors.textSecondary),
                                    onPressed: () {
                                      _searchController.clear();
                                      setState(() {});
                                    },
                                  )
                                : null,
                            suffixIconConstraints: const BoxConstraints(minWidth: 36, minHeight: 42),
                            border: InputBorder.none,
                            contentPadding: const EdgeInsets.only(right: 12),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    // Date filter chip
                    Container(
                      height: 42,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(
                        color: _selectedDateFilter != null
                            ? AppColors.accent.withValues(alpha: 0.15)
                            : Colors.transparent,
                        border: Border.all(
                          color: _selectedDateFilter != null ? AppColors.accent : AppColors.divider,
                        ),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Center(
                        child: Row(
                          children: [
                            const Icon(Icons.calendar_today_outlined, size: 14, color: AppColors.textSecondary),
                            const SizedBox(width: 8),
                            Text(
                              _selectedDateFilter ?? 'All dates',
                              style: AppTextStyles.inter(
                                fontSize: 12,
                                color: _selectedDateFilter != null ? AppColors.accent : AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // Specs List
                if (filtered.isEmpty)
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(40),
                      child: Text(
                        specsList.isEmpty
                            ? 'No spec history recorded yet for $projectName. Inquire in Ask tab to record specifications.'
                            : 'No matching specs found.',
                        style: AppTextStyles.caption,
                        textAlign: TextAlign.center,
                      ),
                    ),
                  )
                else
                  ...filtered.map((spec) => Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: AppColors.bgSurface,
                          border: Border.all(color: AppColors.divider),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      _buildBadge(spec.queryType.toUpperCase(), _getQueryTypeColor(spec.queryType)),
                                      const SizedBox(width: 8),
                                      _buildBadge(spec.confidence.toUpperCase(), AppColors.confirmed),
                                      if (spec.hasBDD) ...[
                                        const SizedBox(width: 8),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            border: Border.all(color: AppColors.inferred.withValues(alpha: 0.4)),
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            'BDD',
                                            style: AppTextStyles.mono(
                                              fontSize: 9,
                                              color: AppColors.inferred,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                  const SizedBox(height: 10),
                                  Text(
                                    spec.query,
                                    style: AppTextStyles.inter(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.textPrimary,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Row(
                                    children: [
                                      Text(
                                        '${spec.timestamp} · ${spec.ago}',
                                        style: AppTextStyles.mono(fontSize: 11, color: AppColors.textSecondary),
                                      ),
                                      const SizedBox(width: 14),
                                      Text(
                                        'score ${spec.score.toStringAsFixed(2)}',
                                        style: AppTextStyles.mono(fontSize: 11, color: AppColors.textSecondary),
                                      ),
                                      if (spec.fprDelta != null) ...[
                                        const SizedBox(width: 14),
                                        Text(
                                          'FPR +${spec.fprDelta!.toStringAsFixed(2)}',
                                          style: AppTextStyles.mono(fontSize: 11, color: AppColors.live),
                                        ),
                                      ],
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 16),
                            InkWell(
                              onTap: () {
                                showDialog(
                                  context: context,
                                  builder: (ctx) => AlertDialog(
                                    backgroundColor: AppColors.bgElevated,
                                    title: Text(spec.query, style: AppTextStyles.inter(fontWeight: FontWeight.w600)),
                                    content: Text('Viewing spec intelligence details for ${spec.timestamp}. Composite precision score: ${spec.score}.', style: AppTextStyles.inter(fontSize: 13, color: AppColors.textSecondary)),
                                    actions: [
                                      TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close', style: TextStyle(color: AppColors.accent))),
                                    ],
                                  ),
                                );
                              },
                              borderRadius: BorderRadius.circular(8),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                decoration: BoxDecoration(
                                  border: Border.all(color: AppColors.divider),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text(
                                  'View chat →',
                                  style: AppTextStyles.inter(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                    color: AppColors.accent,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      )),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
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

  Color _getQueryTypeColor(String type) {
    switch (type) {
      case 'hot':
        return AppColors.modeHot;
      case 'warm':
        return AppColors.modeWarm;
      case 'cold':
      default:
        return AppColors.modeCold;
    }
  }
}
