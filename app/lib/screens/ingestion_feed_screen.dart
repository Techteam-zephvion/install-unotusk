import 'dart:async';
import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/badges.dart';

class IngestionFeedScreen extends StatefulWidget {
  final UnoPalette palette;

  const IngestionFeedScreen({super.key, required this.palette});

  @override
  State<IngestionFeedScreen> createState() => _IngestionFeedScreenState();
}

class _IngestionFeedScreenState extends State<IngestionFeedScreen> {
  List<ProjectItem> _projects = [];
  List<ActivityItem> _activities = [];
  String? _processingProjectId;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() async {
    final projects = await ApiService.fetchProjects();
    final activities = await ApiService.fetchActivities();
    if (mounted) {
      setState(() {
        _projects = projects;
        _activities = activities;
      });
    }
  }

  Future<void> _triggerIngestion(String id) async {
    setState(() {
      _processingProjectId = id;
    });

    try {
      await ApiService.triggerReindex(id);
      await Future.delayed(const Duration(milliseconds: 1000));
      final projects = await ApiService.fetchProjects();
      final activities = await ApiService.fetchActivities();
      if (mounted) {
        setState(() {
          _projects = projects;
          _activities = activities;
          _processingProjectId = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Reindex initiated on backend http://10.0.0.59:8000'),
            backgroundColor: Color(0xFF1B5E20),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _processingProjectId = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Reindex error: $e'),
            backgroundColor: const Color(0xFFB71C1C),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 36),
      child: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Text(
                'INGESTION FEED',
                style: UnoTypography.mono(
                  color: widget.palette.textSec,
                  fontSize: 10,
                  letterSpacing: 0.8,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Project Dashboard',
                style: UnoTypography.brandSerif(
                  palette: widget.palette,
                  fontSize: 26,
                ),
              ),
              const SizedBox(height: 28),

              // Project Cards Grid
              LayoutBuilder(
                builder: (context, constraints) {
                  final isWide = constraints.maxWidth > 580;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: isWide ? 2 : 1,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: isWide ? 1.6 : 1.9,
                    ),
                    itemCount: _projects.length,
                    itemBuilder: (context, index) {
                      final p = _projects[index];
                      final isProcessing =
                          p.ingestionStatus == 'ingesting' ||
                              _processingProjectId == p.id;
                      final fprColor = p.fpr >= 0.6
                          ? widget.palette.live
                          : p.fpr >= 0.5
                              ? widget.palette.output
                              : widget.palette.inferred;

                      return Container(
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: widget.palette.bgSurface,
                          border: Border.all(color: widget.palette.div),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            // Top Row: Name and Status Dots
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  p.name,
                                  style: UnoTypography.body(
                                    color: widget.palette.text,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Row(
                                  children: [
                                    StatusDot(
                                        status: p.upsStatus,
                                        palette: widget.palette),
                                    const SizedBox(width: 5),
                                    Text(
                                      'UPS ${p.upsStatus.toUpperCase()}',
                                      style: UnoTypography.mono(
                                        color: p.upsStatus == 'active'
                                            ? widget.palette.live
                                            : widget.palette.inferred,
                                        fontSize: 9,
                                      ),
                                    ),
                                    Container(
                                      width: 1,
                                      height: 10,
                                      color: widget.palette.div,
                                      margin: const EdgeInsets.symmetric(
                                          horizontal: 8),
                                    ),
                                    StatusDot(
                                        status: p.ingestionStatus,
                                        palette: widget.palette),
                                    const SizedBox(width: 5),
                                    Text(
                                      p.ingestionStatus.toUpperCase(),
                                      style: UnoTypography.mono(
                                        color: p.ingestionStatus == 'live'
                                            ? widget.palette.live
                                            : p.ingestionStatus == 'ingesting'
                                                ? widget.palette.accent
                                                : widget.palette.inferred,
                                        fontSize: 9,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),

                            // Stats Row
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'FPR',
                                      style: UnoTypography.mono(
                                        color: widget.palette.textSec,
                                        fontSize: 9,
                                        letterSpacing: 0.5,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      p.fpr.toStringAsFixed(2),
                                      style: UnoTypography.mono(
                                        color: fprColor,
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'DAYS INDEXED',
                                      style: UnoTypography.mono(
                                        color: widget.palette.textSec,
                                        fontSize: 9,
                                        letterSpacing: 0.5,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '${p.days}',
                                      style: UnoTypography.mono(
                                        color: widget.palette.text,
                                        fontSize: 16,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'LAST INGESTION',
                                      style: UnoTypography.mono(
                                        color: widget.palette.textSec,
                                        fontSize: 9,
                                        letterSpacing: 0.5,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      p.lastIngestion,
                                      style: UnoTypography.mono(
                                        color: widget.palette.textSec,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),

                            // Progress Bar
                            Container(
                              height: 3,
                              decoration: BoxDecoration(
                                color: widget.palette.div,
                                borderRadius: BorderRadius.circular(2),
                              ),
                              child: FractionallySizedBox(
                                alignment: Alignment.centerLeft,
                                widthFactor: p.fpr.clamp(0.0, 1.0),
                                child: Container(
                                  decoration: BoxDecoration(
                                    color: fprColor,
                                    borderRadius: BorderRadius.circular(2),
                                  ),
                                ),
                              ),
                            ),

                            // Processing or Action Button
                            if (isProcessing) ...[
                              Row(
                                children: [
                                  SizedBox(
                                    width: 12,
                                    height: 12,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation<Color>(
                                          widget.palette.accent),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'PROCESSING…',
                                    style: UnoTypography.mono(
                                      color: widget.palette.accent,
                                      fontSize: 9,
                                      letterSpacing: 0.6,
                                    ),
                                  ),
                                ],
                              ),
                            ] else if (p.upsStatus == 'active') ...[
                              OutlinedButton(
                                onPressed: () => _triggerIngestion(p.id),
                                style: OutlinedButton.styleFrom(
                                  side: BorderSide(color: widget.palette.div),
                                  shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(6)),
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 6),
                                ),
                                child: Text(
                                  'Trigger Ingestion',
                                  style: UnoTypography.body(
                                    color: widget.palette.textSec,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ] else ...[
                              Container(
                                padding: const EdgeInsets.symmetric(vertical: 6),
                                alignment: Alignment.center,
                                child: Text(
                                  'OFFLINE',
                                  style: UnoTypography.mono(
                                    color: widget.palette.inferred,
                                    fontSize: 10,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                      );
                    },
                  );
                },
              ),
              const SizedBox(height: 36),

              // Recent Ingestion Activity
              Text(
                'RECENT INGESTION ACTIVITY',
                style: UnoTypography.mono(
                  color: widget.palette.textSec,
                  fontSize: 10,
                  letterSpacing: 0.8,
                ),
              ),
              const SizedBox(height: 14),

              ..._activities.map((act) => Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: widget.palette.bgSurface,
                      border: Border.all(color: widget.palette.div),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 22,
                          height: 22,
                          decoration: BoxDecoration(
                            color: act.color.withValues(alpha: 0.15),
                            shape: BoxShape.circle,
                          ),
                          child: Center(
                            child: Text(
                              act.icon,
                              style: TextStyle(
                                color: act.color,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Text(
                            act.text,
                            style: UnoTypography.body(
                              color: widget.palette.text,
                              fontSize: 13,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          act.time,
                          style: UnoTypography.mono(
                            color: widget.palette.textSec,
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  )),
            ],
          ),
        ),
      ),
    );
  }
}
