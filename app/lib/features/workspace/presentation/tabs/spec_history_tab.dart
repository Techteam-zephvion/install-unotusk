import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
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

  static const List<SpecHistoryItem> _demoSpecs = [
    SpecHistoryItem(
      id: 'spec-1',
      query: 'Why choose Postgres over Mongo in March?',
      isoDate: '2026-03-14',
      timestamp: 'Mar 14, 2026',
      ago: '5d ago',
      queryType: 'cold',
      confidence: 'confirmed',
      hasBDD: true,
      score: 0.94,
      fprDelta: 0.08,
    ),
    SpecHistoryItem(
      id: 'spec-2',
      query: 'Generate a BDD spec for rate-limiter',
      isoDate: '2026-03-12',
      timestamp: 'Mar 12, 2026',
      ago: '7d ago',
      queryType: 'warm',
      confidence: 'confirmed',
      hasBDD: true,
      score: 0.91,
      fprDelta: null,
    ),
    SpecHistoryItem(
      id: 'spec-3',
      query: 'Which team owns the auth service?',
      isoDate: '2026-03-10',
      timestamp: 'Mar 10, 2026',
      ago: '9d ago',
      queryType: 'hot',
      confidence: 'confirmed',
      hasBDD: false,
      score: 0.88,
      fprDelta: 0.04,
    ),
    SpecHistoryItem(
      id: 'spec-4',
      query: 'OIDC federation token exchange contract & verification',
      isoDate: '2026-03-05',
      timestamp: 'Mar 05, 2026',
      ago: '14d ago',
      queryType: 'cold',
      confidence: 'confirmed',
      hasBDD: true,
      score: 0.96,
      fprDelta: 0.12,
    ),
  ];

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

    final specsList = (realSpecs != null && realSpecs.isNotEmpty) ? realSpecs : _demoSpecs;
    final query = _searchController.text.toLowerCase();
    final filtered = specsList.where((s) {
      final matchesSearch = s.query.toLowerCase().contains(query);
      final matchesDate = _selectedDateFilter == null || s.isoDate == _selectedDateFilter;
      return matchesSearch && matchesDate;
    }).toList();

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
                  'Unotusk Core API · 67 days indexed',
                  style: AppTextStyles.caption,
                ),
                const SizedBox(height: 24),

                // Search & Filter Bar
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        decoration: BoxDecoration(
                          color: AppColors.bgElevated,
                          border: Border.all(color: AppColors.divider),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.search, size: 16, color: AppColors.textSecondary),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _searchController,
                                onChanged: (_) => setState(() {}),
                                style: AppTextStyles.inter(fontSize: 13),
                                decoration: const InputDecoration(
                                  hintText: 'Search specs…',
                                  hintStyle: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                                  border: InputBorder.none,
                                  isDense: true,
                                  contentPadding: EdgeInsets.symmetric(vertical: 12),
                                ),
                              ),
                            ),
                            if (_searchController.text.isNotEmpty)
                              InkWell(
                                onTap: () {
                                  _searchController.clear();
                                  setState(() {});
                                },
                                child: const Icon(Icons.close, size: 14, color: AppColors.textSecondary),
                              ),
                          ],
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

                // Recommendation Banner
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.accent.withValues(alpha: 0.08),
                    border: Border.all(color: AppColors.accent.withValues(alpha: 0.25)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.trending_up, size: 16, color: AppColors.accent),
                      const SizedBox(width: 12),
                      Expanded(
                        child: RichText(
                          text: TextSpan(
                            style: AppTextStyles.inter(fontSize: 12, color: AppColors.textSecondary),
                            children: const [
                              TextSpan(
                                text: 'Similar spec available — ',
                                style: TextStyle(color: AppColors.accent, fontWeight: FontWeight.w600),
                              ),
                              TextSpan(
                                text: 'OIDC federation contract matches 4 ontology edges with the rate-limiter spec.',
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // Specs List
                if (filtered.isEmpty)
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(40),
                      child: Text('No matching specs found.', style: AppTextStyles.caption),
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
