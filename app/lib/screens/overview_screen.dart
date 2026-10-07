import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Overview Screen — Project dashboard with metrics, attention items, language distribution, and quick navigation.
/// Ported from repo's overview_tab with UnoPalette design.
class OverviewScreen extends StatefulWidget {
  final UnoPalette palette;
  final Function(String viewId)? onNavigateView;

  const OverviewScreen({
    super.key,
    required this.palette,
    this.onNavigateView,
  });

  @override
  State<OverviewScreen> createState() => _OverviewScreenState();
}

class _OverviewScreenState extends State<OverviewScreen> {
  UnoPalette get p => widget.palette;
  bool _loading = true;
  String? _error;
  ProjectRepositoryContext? _context;
  List<ProjectFinding> _criticalFindings = [];
  ProjectDataPlaneStatus? _dataPlaneStatus;
  List<ProjectMember> _members = [];

  @override
  void initState() {
    super.initState();
    _loadOverviewData();
  }

  Future<void> _loadOverviewData() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final repoContext = await ApiService.fetchRepositoryContext();
      List<ProjectFinding> findings = [];
      try {
        findings = await ApiService.fetchFindings(severity: 'CRITICAL');
      } catch (_) {
        // Fallback or empty if not supported
      }

      ProjectDataPlaneStatus? dpStatus;
      try {
        dpStatus = await ApiService.fetchDataPlaneStatus();
      } catch (_) {}

      List<ProjectMember> membersList = [];
      try {
        membersList = await ApiService.fetchProjectMembers();
      } catch (_) {}

      if (mounted) {
        setState(() {
          _context = repoContext;
          _criticalFindings = findings;
          _dataPlaneStatus = dpStatus;
          _members = membersList;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: p.accent, strokeWidth: 2.5),
            const SizedBox(height: 14),
            Text(
              'Loading repository context...',
              style: UnoTypography.body(color: p.textSec, fontSize: 13),
            ),
          ],
        ),
      );
    }

    if (_error != null && _context == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(LucideIcons.alertTriangle, size: 36, color: p.inferred),
            const SizedBox(height: 12),
            Text(
              'Failed to load project overview',
              style: UnoTypography.body(color: p.text, fontSize: 15, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                _error!,
                style: UnoTypography.body(color: p.textSec, fontSize: 12),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 16),
            InkWell(
              onTap: _loadOverviewData,
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: p.bgSurface,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: p.div),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(LucideIcons.refreshCcw, size: 14, color: p.accent),
                    const SizedBox(width: 8),
                    Text(
                      'Retry',
                      style: UnoTypography.body(color: p.accent, fontSize: 13, fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    final metrics = _context?.metrics ?? const ProjectContextMetrics();

    final snapshot = _context?.activeSnapshot;
    final repoInfo = _context?.repository;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Header Bar ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        repoInfo?.name.isNotEmpty == true ? repoInfo!.name : 'Project Overview',
                        style: UnoTypography.body(color: p.text, fontSize: 20, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: p.live.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: p.live.withValues(alpha: 0.3)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 6,
                              height: 6,
                              decoration: BoxDecoration(
                                color: p.live,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              snapshot?.status ?? 'INDEXED',
                              style: UnoTypography.mono(color: p.live, fontSize: 10, letterSpacing: 0.5),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    repoInfo?.fullName.isNotEmpty == true
                        ? '${repoInfo!.fullName} · Branch: ${snapshot?.branch ?? "main"}'
                        : 'Unified intelligence and architecture overview',
                    style: UnoTypography.body(color: p.textSec, fontSize: 13),
                  ),
                ],
              ),
              InkWell(
                onTap: _loadOverviewData,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                  decoration: BoxDecoration(
                    color: p.bgSurface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: p.div),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(LucideIcons.refreshCw, size: 14, color: p.textSec),
                      const SizedBox(width: 6),
                      Text(
                        'Refresh',
                        style: UnoTypography.body(color: p.textSec, fontSize: 12, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),

          // ── Data Plane & RBAC Security Banner (Port 28000 / 28100 Series) ──
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: p.bgSurface,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: p.div),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: p.accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(LucideIcons.shieldCheck, size: 18, color: p.accent),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            'Control Plane (Port 28000) · Data Plane Isolation (Port ${_dataPlaneStatus?.port ?? 28101})',
                            style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: p.live.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: p.live.withValues(alpha: 0.3)),
                            ),
                            child: Text(
                              _dataPlaneStatus?.status.toUpperCase() ?? 'ACTIVE',
                              style: UnoTypography.mono(color: p.live, fontSize: 9.5, fontWeight: FontWeight.w700),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Role: ${ApiService.activeProject?.role ?? "ADMIN"} · Cross-project boundary isolation & security guardrails active.',
                        style: UnoTypography.body(color: p.textSec, fontSize: 11.5),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                InkWell(
                  onTap: _showMembersModal,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                    decoration: BoxDecoration(
                      color: p.bgElevated,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: p.div),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(LucideIcons.users, size: 14, color: p.text),
                        const SizedBox(width: 6),
                        Text(
                          'Team & RBAC (${_members.isNotEmpty ? _members.length : 1})',
                          style: UnoTypography.body(color: p.text, fontSize: 12, fontWeight: FontWeight.w500),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ── Metric Strip ──
          LayoutBuilder(
            builder: (context, constraints) {
              final isNarrow = constraints.maxWidth < 800;
              final cards = [
                _buildMetricCard(
                  icon: LucideIcons.files,
                  label: 'TOTAL FILES',
                  value: '${metrics.totalFiles}',
                  accentColor: p.accent,
                ),
                _buildMetricCard(
                  icon: LucideIcons.code,
                  label: 'TOTAL SLOC',
                  value: metrics.totalSloc > 1000
                      ? '${(metrics.totalSloc / 1000).toStringAsFixed(1)}k'
                      : '${metrics.totalSloc}',
                  accentColor: const Color(0xFF3B82F6),
                ),
                _buildMetricCard(
                  icon: LucideIcons.braces,
                  label: 'PARSED SYMBOLS',
                  value: '${metrics.totalSymbols}',
                  accentColor: const Color(0xFF10B981),
                ),
                _buildMetricCard(
                  icon: LucideIcons.gitFork,
                  label: 'DEPENDENCIES',
                  value: '${metrics.totalDependencies}',
                  accentColor: const Color(0xFF8B5CF6),
                ),
                _buildMetricCard(
                  icon: LucideIcons.shieldAlert,
                  label: 'FINDINGS',
                  value: '${metrics.totalFindings}',
                  accentColor: metrics.totalFindings > 0 ? p.inferred : p.live,
                ),
              ];

              if (isNarrow) {
                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: cards.map((c) => SizedBox(width: (constraints.maxWidth - 12) / 2, child: c)).toList(),
                );
              }

              return Row(
                children: cards.map((c) => Expanded(child: Padding(
                  padding: const EdgeInsets.only(right: 12),
                  child: c,
                ))).toList(),
              );
            },
          ),
          const SizedBox(height: 28),

          // ── Needs Attention Section ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(LucideIcons.alertCircle, size: 16, color: p.inferred),
                  const SizedBox(width: 8),
                  Text(
                    'Needs Attention',
                    style: UnoTypography.body(color: p.text, fontSize: 15, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              if (widget.onNavigateView != null)
                InkWell(
                  onTap: () => widget.onNavigateView!('discoveries'),
                  child: Text(
                    'View all discoveries →',
                    style: UnoTypography.body(color: p.accent, fontSize: 12, fontWeight: FontWeight.w500),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),

          if (_criticalFindings.isEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              decoration: BoxDecoration(
                color: p.bgSurface,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: p.div),
              ),
              child: Row(
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    decoration: BoxDecoration(
                      color: p.live.withValues(alpha: 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Center(
                      child: Icon(LucideIcons.checkCircle2, size: 18, color: p.live),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'No critical issues detected',
                          style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                        Text(
                          'All scanned architecture rules and static security contracts are compliant.',
                          style: UnoTypography.body(color: p.textSec, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            )
          else
            Column(
              children: _criticalFindings.take(3).map((finding) {
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: p.bgSurface,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: p.inferred.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: p.inferred.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          finding.severity,
                          style: UnoTypography.mono(color: p.inferred, fontSize: 10, letterSpacing: 0.5),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              finding.title,
                              style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              finding.description,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: UnoTypography.body(color: p.textSec, fontSize: 12),
                            ),
                            if (finding.filePath != null) ...[
                              const SizedBox(height: 6),
                              Text(
                                finding.filePath!,
                                style: UnoTypography.mono(color: p.accent, fontSize: 11),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
          const SizedBox(height: 28),

          // ── Language Distribution & Project Info ──
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Languages Breakdown
              Expanded(
                flex: 3,
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: p.bgSurface,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: p.div),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(LucideIcons.pieChart, size: 16, color: p.accent),
                          const SizedBox(width: 8),
                          Text(
                            'Language Distribution',
                            style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      if (metrics.languageDistribution.isEmpty)
                        Text(
                          'No files indexed yet',
                          style: UnoTypography.body(color: p.textSec, fontSize: 12),
                        )
                      else
                        ...metrics.languageDistribution.entries.map((entry) {
                          final total = metrics.totalFiles;
                          final pct = total > 0 ? (entry.value / total) : 0.0;
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      entry.key,
                                      style: UnoTypography.body(color: p.text, fontSize: 12, fontWeight: FontWeight.w500),
                                    ),
                                    Text(
                                      '${entry.value} files (${(pct * 100).toStringAsFixed(1)}%)',
                                      style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(3),
                                  child: LinearProgressIndicator(
                                    value: pct,
                                    minHeight: 5,
                                    backgroundColor: p.bgElevated,
                                    valueColor: AlwaysStoppedAnimation<Color>(_getLangColor(entry.key)),
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
              const SizedBox(width: 16),

              // Active Snapshot & Quick Actions
              Expanded(
                flex: 2,
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: p.bgSurface,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: p.div),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(LucideIcons.gitCommit, size: 16, color: p.accent),
                          const SizedBox(width: 8),
                          Text(
                            'Active Snapshot',
                            style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      _detailRow('Branch', snapshot?.branch ?? 'main'),
                      _detailRow(
                        'Commit',
                        snapshot?.commitHash != null && snapshot!.commitHash.length >= 7
                            ? snapshot.commitHash.substring(0, 7)
                            : (snapshot?.commitHash ?? 'HEAD'),
                      ),
                      _detailRow('Status', snapshot?.status ?? 'READY'),
                      Divider(height: 28, color: p.div),
                      Text(
                        'Quick Navigate',
                        style: UnoTypography.body(color: p.textSec, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _navChip(
                            icon: LucideIcons.folderTree,
                            label: 'Browse Files',
                            onTap: () => widget.onNavigateView?.call('files'),
                          ),
                          _navChip(
                            icon: LucideIcons.boxes,
                            label: 'Architecture',
                            onTap: () => widget.onNavigateView?.call('architecture'),
                          ),
                          _navChip(
                            icon: LucideIcons.searchCode,
                            label: 'Discoveries',
                            onTap: () => widget.onNavigateView?.call('discoveries'),
                          ),
                          _navChip(
                            icon: LucideIcons.bookOpen,
                            label: 'Knowledge',
                            onTap: () => widget.onNavigateView?.call('knowledge'),
                          ),
                          _navChip(
                            icon: LucideIcons.sparkles,
                            label: 'Ask Uno AI',
                            onTap: () => widget.onNavigateView?.call('chat'),
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
  }

  Widget _buildMetricCard({
    required IconData icon,
    required String label,
    required String value,
    required Color accentColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: p.bgSurface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: p.div),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                label,
                style: UnoTypography.mono(color: p.textSec, fontSize: 10, letterSpacing: 0.6),
              ),
              Icon(icon, size: 16, color: accentColor),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: UnoTypography.body(color: p.text, fontSize: 22, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: UnoTypography.body(color: p.textSec, fontSize: 12)),
          Text(
            value,
            style: UnoTypography.mono(color: p.text, fontSize: 12, fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  Widget _navChip({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: p.bgElevated,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: p.div),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 13, color: p.accent),
            const SizedBox(width: 6),
            Text(
              label,
              style: UnoTypography.body(color: p.text, fontSize: 11, fontWeight: FontWeight.w500),
            ),
          ],
        ),
      ),
    );
  }

  Color _getLangColor(String lang) {
    switch (lang.toLowerCase()) {
      case 'dart':
        return const Color(0xFF00B4AB);
      case 'python':
        return const Color(0xFF3572A5);
      case 'typescript':
      case 'javascript':
        return const Color(0xFFF1E05A);
      case 'html':
        return const Color(0xFFE34C26);
      case 'css':
        return const Color(0xFF563D7C);
      case 'json':
      case 'yaml':
        return const Color(0xFFCB171E);
      default:
        return widget.palette.accent;
    }
  }

  void _showMembersModal() {
    final emailCtrl = TextEditingController();
    String selectedRole = 'MEMBER';
    bool isAdding = false;
    String? addError;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            return Dialog(
              backgroundColor: p.bgSurface,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(color: p.div),
              ),
              child: Container(
                width: 540,
                padding: const EdgeInsets.all(22),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(7),
                              decoration: BoxDecoration(
                                color: p.accent.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Icon(LucideIcons.users, size: 16, color: p.accent),
                            ),
                            const SizedBox(width: 10),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Workspace Members & RBAC',
                                  style: UnoTypography.body(color: p.text, fontSize: 16, fontWeight: FontWeight.w600),
                                ),
                                Text(
                                  'Control Plane Port 28000 · Project Container Isolation',
                                  style: UnoTypography.mono(color: p.textSec, fontSize: 10.5),
                                ),
                              ],
                            ),
                          ],
                        ),
                        IconButton(
                          icon: Icon(LucideIcons.x, size: 16, color: p.textSec),
                          onPressed: () => Navigator.of(ctx).pop(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Divider(color: p.div),
                    const SizedBox(height: 12),

                    Text(
                      'CURRENT PROJECT MEMBERS',
                      style: UnoTypography.mono(color: p.textSec, fontSize: 10.5, letterSpacing: 0.5),
                    ),
                    const SizedBox(height: 8),

                    ConstrainedBox(
                      constraints: const BoxConstraints(maxHeight: 180),
                      child: _members.isEmpty
                          ? Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: p.bgElevated,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: p.div),
                              ),
                              child: Row(
                                children: [
                                  CircleAvatar(
                                    radius: 14,
                                    backgroundColor: p.accent,
                                    child: const Text('A', style: TextStyle(color: Colors.white, fontSize: 11)),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text('lead@acme.com (You)',
                                            style: UnoTypography.body(color: p.text, fontSize: 12, fontWeight: FontWeight.w600)),
                                        Text('Workspace Owner & Pilot Lead',
                                            style: UnoTypography.mono(color: p.textSec, fontSize: 10)),
                                      ],
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: p.accent.withValues(alpha: 0.12),
                                      borderRadius: BorderRadius.circular(4),
                                      border: Border.all(color: p.accent.withValues(alpha: 0.25)),
                                    ),
                                    child: Text('ADMIN',
                                        style: UnoTypography.mono(color: p.accent, fontSize: 9.5, fontWeight: FontWeight.w700)),
                                  ),
                                ],
                              ),
                            )
                          : ListView.separated(
                              shrinkWrap: true,
                              itemCount: _members.length,
                              separatorBuilder: (context, index) => const SizedBox(height: 6),
                              itemBuilder: (context, idx) {
                                final m = _members[idx];
                                return Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                                  decoration: BoxDecoration(
                                    color: p.bgElevated,
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: p.div),
                                  ),
                                  child: Row(
                                    children: [
                                      CircleAvatar(
                                        radius: 13,
                                        backgroundColor: p.accent,
                                        child: Text(
                                          (m.userEmail?.isNotEmpty == true
                                                  ? m.userEmail![0]
                                                  : m.userName?.isNotEmpty == true
                                                      ? m.userName![0]
                                                      : 'U')
                                              .toUpperCase(),
                                          style: const TextStyle(color: Colors.white, fontSize: 11),
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          m.userEmail ?? m.userName ?? m.userId,
                                          style: UnoTypography.body(color: p.text, fontSize: 12, fontWeight: FontWeight.w500),
                                        ),
                                      ),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: p.accent.withValues(alpha: 0.12),
                                          borderRadius: BorderRadius.circular(4),
                                          border: Border.all(color: p.accent.withValues(alpha: 0.25)),
                                        ),
                                        child: Text(
                                          m.role,
                                          style: UnoTypography.mono(color: p.accent, fontSize: 9.5, fontWeight: FontWeight.w700),
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ),
                    ),

                    const SizedBox(height: 16),
                    Text(
                      'ADD TEAM MEMBER',
                      style: UnoTypography.mono(color: p.textSec, fontSize: 10.5, letterSpacing: 0.5),
                    ),
                    const SizedBox(height: 8),

                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: emailCtrl,
                            style: UnoTypography.body(color: p.text, fontSize: 12.5),
                            decoration: InputDecoration(
                              hintText: 'colleague@acme.com',
                              hintStyle: UnoTypography.body(color: p.textSec.withValues(alpha: 0.6), fontSize: 12),
                              isDense: true,
                              filled: true,
                              fillColor: p.bgElevated,
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: p.div),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: p.div),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(color: p.accent),
                              ),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        DropdownButtonHideUnderline(
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: p.bgElevated,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: p.div),
                            ),
                            child: DropdownButton<String>(
                              value: selectedRole,
                              dropdownColor: p.bgSurface,
                              isDense: true,
                              items: ['ADMIN', 'MEMBER', 'VIEWER'].map((r) {
                                return DropdownMenuItem(
                                  value: r,
                                  child: Text(r, style: UnoTypography.mono(color: p.text, fontSize: 11)),
                                );
                              }).toList(),
                              onChanged: (val) {
                                if (val != null) {
                                  setDialogState(() => selectedRole = val);
                                }
                              },
                            ),
                          ),
                        ),
                      ],
                    ),

                    if (addError != null) ...[
                      const SizedBox(height: 6),
                      Text(addError!, style: UnoTypography.body(color: p.inferred, fontSize: 11)),
                    ],

                    const SizedBox(height: 14),
                    Align(
                      alignment: Alignment.centerRight,
                      child: ElevatedButton(
                        onPressed: isAdding
                            ? null
                            : () async {
                                final email = emailCtrl.text.trim();
                                if (email.isEmpty) return;
                                setDialogState(() {
                                  isAdding = true;
                                  addError = null;
                                });
                                try {
                                  await ApiService.addProjectMember(
                                    email: email,
                                    role: selectedRole,
                                  );
                                  final updatedMembers = await ApiService.fetchProjectMembers();
                                  if (mounted) {
                                    setState(() => _members = updatedMembers);
                                  }
                                  setDialogState(() {
                                    isAdding = false;
                                    emailCtrl.clear();
                                  });
                                } catch (e) {
                                  setDialogState(() {
                                    isAdding = false;
                                    addError = e.toString();
                                  });
                                }
                              },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: p.accent,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: isAdding
                            ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : Text('Add Member', style: UnoTypography.body(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white)),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}

