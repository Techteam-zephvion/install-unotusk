import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Discoveries Screen — Lists architecture & security findings, allows filtering,
/// status updates, detail inspection, and triggering proactive discovery scans.
/// Ported from repo's discoveries_tab using UnoPalette styling.
class DiscoveriesScreen extends StatefulWidget {
  final UnoPalette palette;
  final Function(String query)? onAskAboutFinding;

  const DiscoveriesScreen({
    super.key,
    required this.palette,
    this.onAskAboutFinding,
  });

  @override
  State<DiscoveriesScreen> createState() => _DiscoveriesScreenState();
}

class _DiscoveriesScreenState extends State<DiscoveriesScreen> {
  UnoPalette get p => widget.palette;

  bool _loading = true;
  String? _error;
  bool _isAnalyzing = false;

  DiscoverySummary? _summary;
  List<ProjectFinding> _findings = [];
  ProjectFinding? _selectedFinding;

  String? _selectedCategory;
  String? _selectedSeverity;
  String? _selectedStatus = 'OPEN';

  final List<String> _categories = [
    'ALL',
    'SECURITY',
    'ARCHITECTURE',
    'PERFORMANCE',
    'QUALITY',
    'TESTING',
  ];

  final List<String> _severities = [
    'ALL',
    'CRITICAL',
    'HIGH',
    'MEDIUM',
    'LOW',
  ];

  final List<String> _statuses = [
    'ALL',
    'OPEN',
    'RESOLVED',
    'DISMISSED',
  ];

  @override
  void initState() {
    super.initState();
    _loadDiscoveries();
  }

  Future<void> _loadDiscoveries() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final summary = await ApiService.fetchDiscoverySummary();
      final findings = await ApiService.fetchFindings(
        category: _selectedCategory,
        severity: _selectedSeverity,
        status: _selectedStatus == 'ALL' ? null : _selectedStatus,
      );

      if (mounted) {
        setState(() {
          _summary = summary;
          _findings = findings;
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

  Future<void> _triggerAnalysis() async {
    setState(() => _isAnalyzing = true);
    try {
      await ApiService.triggerDiscovery();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Proactive discovery scan initiated', style: TextStyle(color: Colors.white)),
            backgroundColor: p.bgElevated,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
      await _loadDiscoveries();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to trigger scan: $e', style: const TextStyle(color: Colors.white)),
            backgroundColor: p.inferred,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isAnalyzing = false);
    }
  }

  Future<void> _updateFindingStatus(ProjectFinding finding, String newStatus) async {
    try {
      final updated = await ApiService.updateFindingStatus(finding.id, newStatus);
      setState(() {
        final idx = _findings.indexWhere((f) => f.id == finding.id);
        if (idx != -1) {
          _findings[idx] = updated;
        }
        if (_selectedFinding?.id == finding.id) {
          _selectedFinding = updated;
        }
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Finding marked as $newStatus', style: const TextStyle(color: Colors.white)),
            backgroundColor: p.bgElevated,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update status: $e', style: const TextStyle(color: Colors.white)),
            backgroundColor: p.inferred,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        // ── Main Findings List Column ──
        Expanded(
          flex: 6,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header with trigger button
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Project Discoveries',
                          style: UnoTypography.body(color: p.text, fontSize: 18, fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _summary != null
                              ? '${_summary!.totalFindings} findings detected (${_summary!.criticalCount} critical, ${_summary!.highCount} high)'
                              : 'Static analysis and architecture discovery findings',
                          style: UnoTypography.body(color: p.textSec, fontSize: 12),
                        ),
                      ],
                    ),
                    ElevatedButton.icon(
                      onPressed: _isAnalyzing ? null : _triggerAnalysis,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: p.accent,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      icon: _isAnalyzing
                          ? const SizedBox(
                              width: 14,
                              height: 14,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            )
                          : const Icon(LucideIcons.radar, size: 15),
                      label: Text(
                        _isAnalyzing ? 'Scanning…' : 'Trigger Scan',
                        style: UnoTypography.body(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),

              // Filter Controls Strip
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
                decoration: BoxDecoration(
                  color: p.bgSurface,
                  border: Border(
                    top: BorderSide(color: p.div),
                    bottom: BorderSide(color: p.div),
                  ),
                ),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      Text(
                        'Category:',
                        style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                      ),
                      const SizedBox(width: 8),
                      ..._categories.map((cat) {
                        final isSel = (_selectedCategory == null && cat == 'ALL') ||
                            (_selectedCategory == cat);
                        return Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: InkWell(
                            onTap: () {
                              setState(() {
                                _selectedCategory = cat == 'ALL' ? null : cat;
                              });
                              _loadDiscoveries();
                            },
                            borderRadius: BorderRadius.circular(6),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                              decoration: BoxDecoration(
                                color: isSel ? p.accent.withValues(alpha: 0.15) : Colors.transparent,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: isSel ? p.accent : p.div,
                                ),
                              ),
                              child: Text(
                                cat,
                                style: UnoTypography.mono(
                                  color: isSel ? p.accent : p.textSec,
                                  fontSize: 10,
                                  fontWeight: isSel ? FontWeight.w600 : FontWeight.w400,
                                ),
                              ),
                            ),
                          ),
                        );
                      }),
                      const SizedBox(width: 16),
                      Text(
                        'Severity:',
                        style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                      ),
                      const SizedBox(width: 8),
                      ..._severities.map((sev) {
                        final isSel = (_selectedSeverity == null && sev == 'ALL') ||
                            (_selectedSeverity == sev);
                        return Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: InkWell(
                            onTap: () {
                              setState(() {
                                _selectedSeverity = sev == 'ALL' ? null : sev;
                              });
                              _loadDiscoveries();
                            },
                            borderRadius: BorderRadius.circular(6),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                              decoration: BoxDecoration(
                                color: isSel ? p.accent.withValues(alpha: 0.15) : Colors.transparent,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: isSel ? p.accent : p.div,
                                ),
                              ),
                              child: Text(
                                sev,
                                style: UnoTypography.mono(
                                  color: isSel ? p.accent : p.textSec,
                                  fontSize: 10,
                                  fontWeight: isSel ? FontWeight.w600 : FontWeight.w400,
                                ),
                              ),
                            ),
                          ),
                        );
                      }),
                      const SizedBox(width: 16),
                      Text(
                        'Status:',
                        style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                      ),
                      const SizedBox(width: 8),
                      ..._statuses.map((st) {
                        final isSel = _selectedStatus == st;
                        return Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: InkWell(
                            onTap: () {
                              setState(() {
                                _selectedStatus = st;
                              });
                              _loadDiscoveries();
                            },
                            borderRadius: BorderRadius.circular(6),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                              decoration: BoxDecoration(
                                color: isSel ? p.accent.withValues(alpha: 0.15) : Colors.transparent,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: isSel ? p.accent : p.div,
                                ),
                              ),
                              child: Text(
                                st,
                                style: UnoTypography.mono(
                                  color: isSel ? p.accent : p.textSec,
                                  fontSize: 10,
                                  fontWeight: isSel ? FontWeight.w600 : FontWeight.w400,
                                ),
                              ),
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              ),

              // Findings List
              Expanded(
                child: _loading
                    ? Center(child: CircularProgressIndicator(color: p.accent, strokeWidth: 2))
                    : _error != null
                        ? Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(LucideIcons.alertTriangle, size: 32, color: p.inferred),
                                const SizedBox(height: 10),
                                Text('Failed to load findings', style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600)),
                                const SizedBox(height: 4),
                                Text(_error!, style: UnoTypography.body(color: p.textSec, fontSize: 12)),
                                const SizedBox(height: 12),
                                TextButton.icon(
                                  onPressed: _loadDiscoveries,
                                  icon: Icon(LucideIcons.refreshCcw, size: 14, color: p.accent),
                                  label: Text('Retry', style: UnoTypography.body(color: p.accent, fontSize: 12)),
                                ),
                              ],
                            ),
                          )
                        : _findings.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(LucideIcons.shieldCheck, size: 40, color: p.live),
                                    const SizedBox(height: 12),
                                    Text(
                                      'No findings match the current filter',
                                      style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w600),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      'Try resetting filters or trigger a new discovery scan.',
                                      style: UnoTypography.body(color: p.textSec, fontSize: 12),
                                    ),
                                  ],
                                ),
                              )
                            : ListView.builder(
                                padding: const EdgeInsets.all(20),
                                itemCount: _findings.length,
                                itemBuilder: (context, index) {
                                  final finding = _findings[index];
                                  final isSelected = _selectedFinding?.id == finding.id;

                                  return Container(
                                    margin: const EdgeInsets.only(bottom: 12),
                                    decoration: BoxDecoration(
                                      color: isSelected
                                          ? p.accent.withValues(alpha: 0.08)
                                          : p.bgSurface,
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(
                                        color: isSelected ? p.accent : p.div,
                                      ),
                                    ),
                                    child: InkWell(
                                      onTap: () => setState(() => _selectedFinding = finding),
                                      borderRadius: BorderRadius.circular(10),
                                      child: Padding(
                                        padding: const EdgeInsets.all(16),
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            // Top row: severity + category + status
                                            Row(
                                              children: [
                                                _severityPill(finding.severity),
                                                const SizedBox(width: 8),
                                                Container(
                                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                  decoration: BoxDecoration(
                                                    color: p.bgElevated,
                                                    borderRadius: BorderRadius.circular(4),
                                                  ),
                                                  child: Text(
                                                    finding.category,
                                                    style: UnoTypography.mono(color: p.textSec, fontSize: 10),
                                                  ),
                                                ),
                                                const Spacer(),
                                                Text(
                                                  finding.status,
                                                  style: UnoTypography.mono(
                                                    color: finding.status == 'OPEN' ? p.live : p.textSec,
                                                    fontSize: 10,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                ),
                                              ],
                                            ),
                                            const SizedBox(height: 10),
                                            Text(
                                              finding.title,
                                              style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w600),
                                            ),
                                            const SizedBox(height: 6),
                                            Text(
                                              finding.description,
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                              style: UnoTypography.body(color: p.textSec, fontSize: 12),
                                            ),
                                            if (finding.filePath != null) ...[
                                              const SizedBox(height: 8),
                                              Row(
                                                children: [
                                                  Icon(LucideIcons.fileText, size: 12, color: p.accent),
                                                  const SizedBox(width: 6),
                                                  Expanded(
                                                    child: Text(
                                                      '${finding.filePath!}${finding.lineStart != null ? ":${finding.lineStart}" : ""}',
                                                      style: UnoTypography.mono(color: p.accent, fontSize: 11),
                                                      overflow: TextOverflow.ellipsis,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                    ),
                                  );
                                },
                              ),
              ),
            ],
          ),
        ),

        // ── Finding Detail Side Panel ──
        Container(
          width: 380,
          decoration: BoxDecoration(
            color: p.bgSurface,
            border: Border(left: BorderSide(color: p.div)),
          ),
          child: _selectedFinding == null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(LucideIcons.fileSearch, size: 36, color: p.div),
                      const SizedBox(height: 12),
                      Text(
                        'Select a finding to inspect details',
                        style: UnoTypography.body(color: p.textSec, fontSize: 13),
                      ),
                    ],
                  ),
                )
              : _buildFindingDetailPanel(_selectedFinding!),
        ),
      ],
    );
  }

  Widget _buildFindingDetailPanel(ProjectFinding finding) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _severityPill(finding.severity),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  finding.category,
                  style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                ),
              ),
              IconButton(
                icon: Icon(LucideIcons.x, size: 16, color: p.textSec),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: () => setState(() => _selectedFinding = null),
              ),
            ],
          ),
          const SizedBox(height: 14),

          Text(
            finding.title,
            style: UnoTypography.body(color: p.text, fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 14),

          // Status selector buttons
          Row(
            children: [
              Text('Status:', style: UnoTypography.body(color: p.textSec, fontSize: 12)),
              const SizedBox(width: 8),
              _statusChip(finding, 'OPEN'),
              const SizedBox(width: 6),
              _statusChip(finding, 'RESOLVED'),
              const SizedBox(width: 6),
              _statusChip(finding, 'DISMISSED'),
            ],
          ),
          Divider(height: 28, color: p.div),

          // Description
          Text(
            'Description',
            style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          Text(
            finding.description,
            style: UnoTypography.body(color: p.textSec, fontSize: 12, height: 1.5),
          ),
          const SizedBox(height: 16),

          // Location
          if (finding.filePath != null) ...[
            Text(
              'Location',
              style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: p.bgElevated,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: p.div),
              ),
              child: Row(
                children: [
                  Icon(LucideIcons.fileCode, size: 14, color: p.accent),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${finding.filePath!}${finding.lineStart != null ? " : ${finding.lineStart}–${finding.lineEnd ?? finding.lineStart}" : ""}',
                      style: UnoTypography.mono(color: p.text, fontSize: 11),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Recommendation / Remediation
          if (finding.recommendation.isNotEmpty) ...[
            Text(
              'Recommendation',
              style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: p.bgElevated,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: p.div),
              ),
              child: Text(
                finding.recommendation,
                style: UnoTypography.body(color: p.text, fontSize: 12, height: 1.4),
              ),
            ),
            const SizedBox(height: 20),
          ],

          // Action Button: Ask Uno AI
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: () {
                final query = 'How should we resolve finding "${finding.title}" in ${finding.filePath ?? "the codebase"}?';
                widget.onAskAboutFinding?.call(query);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: p.accent,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              icon: const Icon(LucideIcons.sparkles, size: 15),
              label: Text(
                'Ask Uno AI to Fix',
                style: UnoTypography.body(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _severityPill(String severity) {
    Color bg;
    Color fg;
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        bg = const Color(0xFFEF4444).withValues(alpha: 0.15);
        fg = const Color(0xFFEF4444);
        break;
      case 'HIGH':
        bg = const Color(0xFFF97316).withValues(alpha: 0.15);
        fg = const Color(0xFFF97316);
        break;
      case 'MEDIUM':
        bg = const Color(0xFFF59E0B).withValues(alpha: 0.15);
        fg = const Color(0xFFF59E0B);
        break;
      case 'LOW':
      default:
        bg = p.bgElevated;
        fg = p.textSec;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        severity,
        style: UnoTypography.mono(color: fg, fontSize: 10, letterSpacing: 0.5),
      ),
    );
  }

  Widget _statusChip(ProjectFinding finding, String status) {
    final isCurrent = finding.status == status;
    return InkWell(
      onTap: isCurrent ? null : () => _updateFindingStatus(finding, status),
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: isCurrent ? p.accent.withValues(alpha: 0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: isCurrent ? p.accent : p.div,
          ),
        ),
        child: Text(
          status,
          style: UnoTypography.mono(
            color: isCurrent ? p.accent : p.textSec,
            fontSize: 10,
            fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}
