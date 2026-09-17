import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class ProjectFeedItem {
  final String id;
  final String name;
  final String upsStatus; // active | degraded
  final String ingestionStatus; // live | ingesting | error
  final double fpr;
  final int days;
  final String lastIngestion;

  const ProjectFeedItem({
    required this.id,
    required this.name,
    required this.upsStatus,
    required this.ingestionStatus,
    required this.fpr,
    required this.days,
    required this.lastIngestion,
  });
}

class IngestionFeedTab extends StatefulWidget {
  final String projectId;

  const IngestionFeedTab({
    super.key,
    required this.projectId,
  });

  @override
  State<IngestionFeedTab> createState() => _IngestionFeedTabState();
}

class _IngestionFeedTabState extends State<IngestionFeedTab> {
  String? _reingestingId;

  static const List<ProjectFeedItem> _projects = [
    ProjectFeedItem(
      id: 'proj-1',
      name: 'Unotusk Auth Service (US)',
      upsStatus: 'active',
      ingestionStatus: 'live',
      fpr: 0.88,
      days: 67,
      lastIngestion: '4m ago',
    ),
    ProjectFeedItem(
      id: 'proj-2',
      name: 'Unotusk Company Server (UPS)',
      upsStatus: 'active',
      ingestionStatus: 'live',
      fpr: 0.92,
      days: 67,
      lastIngestion: '12m ago',
    ),
    ProjectFeedItem(
      id: 'proj-3',
      name: 'AI PIE Intelligence Engine',
      upsStatus: 'active',
      ingestionStatus: 'live',
      fpr: 0.95,
      days: 58,
      lastIngestion: '1h ago',
    ),
    ProjectFeedItem(
      id: 'proj-4',
      name: 'Unotusk Employee Client (UCA)',
      upsStatus: 'active',
      ingestionStatus: 'live',
      fpr: 0.85,
      days: 42,
      lastIngestion: '2h ago',
    ),
  ];

  void _triggerReingest(String id) async {
    setState(() => _reingestingId = id);
    await Future.delayed(const Duration(seconds: 3));
    if (mounted) {
      setState(() => _reingestingId = null);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Ingestion scan completed successfully'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Section Header
                Text('INGESTION FEED', style: AppTextStyles.sectionLabel),
                const SizedBox(height: 6),
                Text(
                  'Project Dashboard',
                  style: AppTextStyles.authHeading,
                ),
                const SizedBox(height: 24),

                // Project Cards Grid
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 14,
                    mainAxisSpacing: 14,
                    childAspectRatio: 1.6,
                  ),
                  itemCount: _projects.length,
                  itemBuilder: (context, index) {
                    final proj = _projects[index];
                    final isReingesting = _reingestingId == proj.id;
                    final fprColor = proj.fpr >= 0.9
                        ? AppColors.live
                        : proj.fpr >= 0.8
                            ? AppColors.output
                            : AppColors.inferred;

                    return Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: AppColors.bgSurface,
                        border: Border.all(color: AppColors.divider),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          // Header: Name + Status Dots
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Expanded(
                                child: Text(
                                  proj.name,
                                  style: AppTextStyles.inter(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.textPrimary,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              Row(
                                children: [
                                  _buildStatusIndicator(
                                    label: 'UPS ${proj.upsStatus.toUpperCase()}',
                                    isActive: proj.upsStatus == 'active',
                                  ),
                                  const SizedBox(width: 8),
                                  _buildStatusIndicator(
                                    label: proj.ingestionStatus.toUpperCase(),
                                    isActive: proj.ingestionStatus == 'live',
                                  ),
                                ],
                              ),
                            ],
                          ),

                          // Metrics strip
                          Row(
                            children: [
                              _buildMetricItem('FPR', proj.fpr.toStringAsFixed(2), fprColor),
                              const SizedBox(width: 24),
                              _buildMetricItem('DAYS INDEXED', '${proj.days}', AppColors.textPrimary),
                              const SizedBox(width: 24),
                              _buildMetricItem('LAST INGESTION', proj.lastIngestion, AppColors.textSecondary),
                            ],
                          ),

                          // FPR Linear Progress Bar
                          ClipRRect(
                            borderRadius: BorderRadius.circular(2),
                            child: LinearProgressIndicator(
                              value: proj.fpr,
                              backgroundColor: AppColors.divider,
                              valueColor: AlwaysStoppedAnimation<Color>(fprColor),
                              minHeight: 4,
                            ),
                          ),

                          // Action button
                          Align(
                            alignment: Alignment.centerRight,
                            child: InkWell(
                              onTap: isReingesting ? null : () => _triggerReingest(proj.id),
                              borderRadius: BorderRadius.circular(6),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  border: Border.all(color: AppColors.divider),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (isReingesting) ...[
                                      const SizedBox(
                                        width: 10,
                                        height: 10,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 1.5,
                                          valueColor: AlwaysStoppedAnimation<Color>(AppColors.accent),
                                        ),
                                      ),
                                      const SizedBox(width: 6),
                                    ],
                                    Text(
                                      isReingesting ? 'Scanning…' : 'Re-ingest ↺',
                                      style: AppTextStyles.mono(
                                        fontSize: 10,
                                        color: isReingesting ? AppColors.accent : AppColors.textSecondary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatusIndicator({required String label, required bool isActive}) {
    final color = isActive ? AppColors.live : AppColors.inferred;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 5,
          height: 5,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: AppTextStyles.mono(
            fontSize: 9,
            color: color,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }

  Widget _buildMetricItem(String label, String value, Color valueColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.sectionLabel),
        const SizedBox(height: 3),
        Text(
          value,
          style: AppTextStyles.mono(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: valueColor,
          ),
        ),
      ],
    );
  }
}
