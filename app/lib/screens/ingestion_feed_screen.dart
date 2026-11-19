import 'dart:async';
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
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
  final ScrollController _scrollController = ScrollController();
  List<ProjectItem> _projects = [];
  List<ActivityItem> _activities = [];
  String? _processingProjectId;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
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
          SnackBar(
            content: const Text('Repository reindex initiated'),
            backgroundColor: const Color(0xFF15803D),
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
    final p = widget.palette;

    return ScrollConfiguration(
      behavior: ScrollConfiguration.of(context).copyWith(scrollbars: false),
      child: RawScrollbar(
        controller: _scrollController,
        thumbVisibility: false,
        trackVisibility: false,
        thickness: 2.0,
        radius: const Radius.circular(2),
        thumbColor: p.textSec.withValues(alpha: 0.25),
        fadeDuration: const Duration(milliseconds: 250),
        padding: const EdgeInsets.only(right: 4, top: 8, bottom: 8),
        child: SingleChildScrollView(
          controller: _scrollController,
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 960),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Header
                  Text(
                    'INGESTION FEED',
                    style: UnoTypography.mono(
                      color: p.textMuted,
                      fontSize: 10.5,
                      letterSpacing: 1.0,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    'Ingestion Pipeline',
                    style: UnoTypography.headingSerif(
                      color: p.text,
                      fontSize: 26,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Live indexing health, coverage metrics, and recent workspace events.',
                    style: UnoTypography.body(
                      color: p.textSec,
                      fontSize: 13.5,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Project Cards Grid
                  if (_projects.isNotEmpty) ...[
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final isWide = constraints.maxWidth > 580;
                        return GridView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          gridDelegate:
                              SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: isWide ? 2 : 1,
                            crossAxisSpacing: 14,
                            mainAxisSpacing: 14,
                            childAspectRatio: isWide ? 1.7 : 2.0,
                          ),
                          itemCount: _projects.length,
                          itemBuilder: (context, index) {
                            final proj = _projects[index];
                            final isProcessing =
                                proj.ingestionStatus == 'ingesting' ||
                                    _processingProjectId == proj.id;
                            final fprColor = proj.fpr >= 0.6
                                ? p.live
                                : proj.fpr >= 0.5
                                    ? p.accent
                                    : p.textSec;

                            return Container(
                              padding: const EdgeInsets.all(20),
                              decoration: BoxDecoration(
                                gradient: p.sectionGradient,
                                border: Border.all(color: p.div),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  // Top Row: Name and Status Dots
                                  Row(
                                    mainAxisAlignment:
                                        MainAxisAlignment.spaceBetween,
                                    children: [
                                      Flexible(
                                        child: Text(
                                          formatDisplayTitle(proj.name),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: UnoTypography.body(
                                            color: p.text,
                                            fontSize: 15,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          StatusDot(
                                              status: proj.upsStatus,
                                              palette: p),
                                          const SizedBox(width: 5),
                                          Text(
                                            'UPS ${proj.upsStatus.toUpperCase()}',
                                            style: UnoTypography.mono(
                                              color: proj.upsStatus == 'active'
                                                  ? p.live
                                                  : p.textSec,
                                              fontSize: 9.5,
                                            ),
                                          ),
                                          Container(
                                            width: 1,
                                            height: 10,
                                            color: p.div,
                                            margin: const EdgeInsets.symmetric(
                                                horizontal: 8),
                                          ),
                                          StatusDot(
                                              status: proj.ingestionStatus,
                                              palette: p),
                                          const SizedBox(width: 5),
                                          Text(
                                            proj.ingestionStatus.toUpperCase(),
                                            style: UnoTypography.mono(
                                              color: proj.ingestionStatus ==
                                                      'live'
                                                  ? p.live
                                                  : proj.ingestionStatus ==
                                                          'ingesting'
                                                      ? p.accent
                                                      : p.textSec,
                                              fontSize: 9.5,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),

                                  // Stats Row
                                  Row(
                                    mainAxisAlignment:
                                        MainAxisAlignment.spaceBetween,
                                    children: [
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'FPR',
                                            style: UnoTypography.mono(
                                              color: p.textMuted,
                                              fontSize: 9.5,
                                              letterSpacing: 0.6,
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            proj.fpr.toStringAsFixed(2),
                                            style: UnoTypography.mono(
                                              color: fprColor,
                                              fontSize: 16,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                        ],
                                      ),
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'DAYS INDEXED',
                                            style: UnoTypography.mono(
                                              color: p.textMuted,
                                              fontSize: 9.5,
                                              letterSpacing: 0.6,
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            '${proj.days}',
                                            style: UnoTypography.mono(
                                              color: p.text,
                                              fontSize: 16,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                        ],
                                      ),
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'LAST INGESTION',
                                            style: UnoTypography.mono(
                                              color: p.textMuted,
                                              fontSize: 9.5,
                                              letterSpacing: 0.6,
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            proj.lastIngestion,
                                            style: UnoTypography.mono(
                                              color: p.textSec,
                                              fontSize: 12,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),

                                  // Progress Bar
                                  Container(
                                    height: 3.5,
                                    decoration: BoxDecoration(
                                      color: p.div,
                                      borderRadius: BorderRadius.circular(2),
                                    ),
                                    child: FractionallySizedBox(
                                      alignment: Alignment.centerLeft,
                                      widthFactor: proj.fpr.clamp(0.0, 1.0),
                                      child: Container(
                                        decoration: BoxDecoration(
                                          color: fprColor,
                                          borderRadius:
                                              BorderRadius.circular(2),
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
                                            valueColor:
                                                AlwaysStoppedAnimation<Color>(
                                                    p.accent),
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          'PROCESSING…',
                                          style: UnoTypography.mono(
                                            color: p.accent,
                                            fontSize: 10,
                                            letterSpacing: 0.6,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ] else if (proj.upsStatus == 'active') ...[
                                    OutlinedButton.icon(
                                      onPressed: () =>
                                          _triggerIngestion(proj.id),
                                      style: OutlinedButton.styleFrom(
                                        side: BorderSide(color: p.div),
                                        shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(8),
                                        ),
                                        padding: const EdgeInsets.symmetric(
                                            vertical: 9),
                                      ),
                                      icon: Icon(
                                        LucideIcons.refreshCw,
                                        size: 13,
                                        color: p.accentMuted,
                                      ),
                                      label: Text(
                                        'Trigger Ingestion',
                                        style: UnoTypography.body(
                                          color: p.text,
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                    ),
                                  ] else ...[
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                          vertical: 6),
                                      alignment: Alignment.center,
                                      child: Text(
                                        'OFFLINE',
                                        style: UnoTypography.mono(
                                          color: p.textMuted,
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
                    const SizedBox(height: 32),
                  ],

                  // Recent Ingestion Activity Section Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'RECENT INGESTION ACTIVITY',
                        style: UnoTypography.mono(
                          color: p.textMuted,
                          fontSize: 10.5,
                          letterSpacing: 1.0,
                        ),
                      ),
                      if (_activities.isNotEmpty)
                        Text(
                          '${_activities.length} ${_activities.length == 1 ? 'event' : 'events'}',
                          style: UnoTypography.body(
                            color: p.textMuted,
                            fontSize: 12,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Unified Elevated Activity Log Panel
                  if (_activities.isEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 24, vertical: 40),
                      decoration: BoxDecoration(
                        gradient: p.sectionGradient,
                        border: Border.all(color: p.div),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Column(
                        children: [
                          Icon(
                            LucideIcons.activity,
                            size: 22,
                            color: p.textMuted,
                          ),
                          const SizedBox(height: 10),
                          Text(
                            'No recent ingestion activity yet',
                            style: UnoTypography.body(
                              color: p.textSec,
                              fontSize: 13.5,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    Container(
                      decoration: BoxDecoration(
                        gradient: p.sectionGradient,
                        border: Border.all(color: p.div),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      clipBehavior: Clip.antiAlias,
                      child: Column(
                        children: [
                          for (int i = 0; i < _activities.length; i++) ...[
                            _ActivityFeedRow(
                              item: _activities[i],
                              palette: p,
                            ),
                            if (i < _activities.length - 1)
                              Divider(
                                height: 1,
                                thickness: 1,
                                indent: 64,
                                endIndent: 18,
                                color: p.div.withValues(alpha: 0.65),
                              ),
                          ],
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ActivityFeedRow extends StatefulWidget {
  final ActivityItem item;
  final UnoPalette palette;

  const _ActivityFeedRow({
    required this.item,
    required this.palette,
  });

  @override
  State<_ActivityFeedRow> createState() => _ActivityFeedRowState();
}

class _ActivityFeedRowState extends State<_ActivityFeedRow> {
  bool _hovered = false;

  IconData _resolveIcon(String key) {
    switch (key.toLowerCase().trim()) {
      case 'cpu':
      case 'discovery':
      case 'scan':
        return LucideIcons.cpu;
      case 'message-square':
      case 'message':
      case 'chat':
      case 'thread':
        return LucideIcons.messageSquare;
      case 'git-commit':
      case 'commit':
        return LucideIcons.gitCommitHorizontal;
      case 'git-branch':
      case 'branch':
        return LucideIcons.gitBranch;
      case 'file':
      case 'file-code':
      case 'code':
        return LucideIcons.fileCode;
      case 'database':
      case 'index':
        return LucideIcons.database;
      case 'shield':
      case 'security':
        return LucideIcons.shieldCheck;
      default:
        return LucideIcons.activity;
    }
  }

  String _resolveCategory(String key) {
    switch (key.toLowerCase().trim()) {
      case 'cpu':
      case 'discovery':
      case 'scan':
        return 'Discovery';
      case 'message-square':
      case 'message':
      case 'chat':
      case 'thread':
        return 'Conversation';
      case 'git-commit':
      case 'commit':
      case 'git-branch':
        return 'Repository';
      case 'database':
      case 'index':
        return 'Index';
      default:
        return 'Event';
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final item = widget.item;
    final isDark = p.isDark;
    final isLive = item.time.toLowerCase() == 'active';
    final hoverBase = isDark ? p.accent : p.text;

    final iconData = _resolveIcon(item.icon);
    final category = _resolveCategory(item.icon);

    final iconTileBg = isDark
        ? const Color(0xFF1C253C)
        : const Color(0xFFF4EFE6);
    final iconColor = isLive
        ? p.live
        : (isDark ? p.accent : p.text);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        curve: Curves.easeOutCubic,
        color: hoverBase.withValues(alpha: _hovered ? 0.04 : 0.0),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Crisp Tonal Icon Tile (real Lucide vector icon, never raw string text)
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: iconTileBg,
                borderRadius: BorderRadius.circular(9),
                border: Border.all(
                  color: _hovered
                      ? p.accent.withValues(alpha: isDark ? 0.28 : 0.22)
                      : p.div.withValues(alpha: 0.85),
                ),
              ),
              alignment: Alignment.center,
              child: Icon(
                iconData,
                size: 15.5,
                color: iconColor,
              ),
            ),

            const SizedBox(width: 14),

            // Message & Subtle Category Meta
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    item.text,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: UnoTypography.body(
                      color: p.text,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    category,
                    style: UnoTypography.body(
                      color: p.textMuted,
                      fontSize: 11.5,
                      height: 1.2,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(width: 16),

            // Clean Timestamp / Live Status Pill
            if (isLive)
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 9, vertical: 3.5),
                decoration: BoxDecoration(
                  color: p.live.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: p.live.withValues(alpha: 0.26),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 5.5,
                      height: 5.5,
                      decoration: BoxDecoration(
                        color: p.live,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      'Active',
                      style: UnoTypography.body(
                        color: isDark
                            ? const Color(0xFF6EE7B7)
                            : const Color(0xFF15803D),
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              )
            else
              Text(
                item.time,
                style: UnoTypography.mono(
                  color: p.textMuted,
                  fontSize: 11.5,
                  letterSpacing: 0.1,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
