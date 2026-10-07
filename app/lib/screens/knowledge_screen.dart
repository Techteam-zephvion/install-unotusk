import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Knowledge Screen — Project knowledge base, ADRs, business rules, and technical debt notes.
/// Ported from repo's knowledge_tab using UnoPalette styling.
class KnowledgeScreen extends StatefulWidget {
  final UnoPalette palette;
  final Function(String filePath)? onNavigateToFile;

  const KnowledgeScreen({
    super.key,
    required this.palette,
    this.onNavigateToFile,
  });

  @override
  State<KnowledgeScreen> createState() => _KnowledgeScreenState();
}

class _KnowledgeScreenState extends State<KnowledgeScreen> {
  UnoPalette get p => widget.palette;

  bool _loading = true;
  String? _error;
  List<ProjectKnowledge> _items = [];
  String _searchQuery = '';
  String? _selectedCategory;
  String _status = 'ACTIVE';

  final List<String> _categories = [
    'ALL',
    'ADR',
    'BUSINESS_RULE',
    'TECH_DEBT',
    'DOMAIN_CONCEPT',
    'CONVENTION',
  ];

  @override
  void initState() {
    super.initState();
    _loadKnowledge();
  }

  Future<void> _loadKnowledge() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final items = await ApiService.fetchKnowledge(
        category: _selectedCategory,
        status: _status,
      );

      if (mounted) {
        setState(() {
          _items = items;
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

  Future<void> _toggleArchive(ProjectKnowledge item) async {
    try {
      if (item.status == 'ACTIVE') {
        await ApiService.archiveKnowledge(item.id);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Archived "${item.title}"', style: const TextStyle(color: Colors.white)),
              backgroundColor: p.bgElevated,
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      } else {
        await ApiService.restoreKnowledge(item.id);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Restored "${item.title}"', style: const TextStyle(color: Colors.white)),
              backgroundColor: p.bgElevated,
              behavior: SnackBarBehavior.floating,
            ),
          );
        }
      }
      _loadKnowledge();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Action failed: $e', style: const TextStyle(color: Colors.white)),
            backgroundColor: p.inferred,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  void _showCreateDialog() {
    final titleCtrl = TextEditingController();
    final contentCtrl = TextEditingController();
    final fileCtrl = TextEditingController();
    final symbolCtrl = TextEditingController();
    String category = 'ADR';

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: p.bgSurface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: p.div),
          ),
          title: Row(
            children: [
              Icon(LucideIcons.bookPlus, size: 18, color: p.accent),
              const SizedBox(width: 8),
              Text(
                'Record Knowledge',
                style: UnoTypography.body(color: p.text, fontSize: 16, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          content: SizedBox(
            width: 480,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Category', style: UnoTypography.body(color: p.textSec, fontSize: 12)),
                  const SizedBox(height: 6),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      color: p.bgElevated,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: p.div),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        value: category,
                        isExpanded: true,
                        dropdownColor: p.bgElevated,
                        style: UnoTypography.body(color: p.text, fontSize: 13),
                        items: ['ADR', 'BUSINESS_RULE', 'TECH_DEBT', 'DOMAIN_CONCEPT', 'CONVENTION']
                            .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                            .toList(),
                        onChanged: (v) {
                          if (v != null) setDialogState(() => category = v);
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),

                  Text('Title', style: UnoTypography.body(color: p.textSec, fontSize: 12)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: titleCtrl,
                    style: UnoTypography.body(color: p.text, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: 'e.g. ADR #7: PostgreSQL for event telemetry',
                      hintStyle: UnoTypography.body(color: p.textSec, fontSize: 13),
                      filled: true,
                      fillColor: p.bgElevated,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.accent)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                  ),
                  const SizedBox(height: 14),

                  Text('Content (Markdown / Text)', style: UnoTypography.body(color: p.textSec, fontSize: 12)),
                  const SizedBox(height: 6),
                  TextField(
                    controller: contentCtrl,
                    maxLines: 5,
                    style: UnoTypography.body(color: p.text, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: 'Describe rationale, context, constraints, and consequences…',
                      hintStyle: UnoTypography.body(color: p.textSec, fontSize: 13),
                      filled: true,
                      fillColor: p.bgElevated,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.accent)),
                      contentPadding: const EdgeInsets.all(12),
                    ),
                  ),
                  const SizedBox(height: 14),

                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Related File (optional)', style: UnoTypography.body(color: p.textSec, fontSize: 12)),
                            const SizedBox(height: 6),
                            TextField(
                              controller: fileCtrl,
                              style: UnoTypography.mono(color: p.text, fontSize: 11),
                              decoration: InputDecoration(
                                hintText: 'lib/services/api.dart',
                                hintStyle: UnoTypography.mono(color: p.textSec, fontSize: 11),
                                filled: true,
                                fillColor: p.bgElevated,
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.accent)),
                                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Related Symbol (optional)', style: UnoTypography.body(color: p.textSec, fontSize: 12)),
                            const SizedBox(height: 6),
                            TextField(
                              controller: symbolCtrl,
                              style: UnoTypography.mono(color: p.text, fontSize: 11),
                              decoration: InputDecoration(
                                hintText: 'AuthService',
                                hintStyle: UnoTypography.mono(color: p.textSec, fontSize: 11),
                                filled: true,
                                fillColor: p.bgElevated,
                                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.div)),
                                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: p.accent)),
                                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: Text('Cancel', style: TextStyle(color: p.textSec)),
            ),
            ElevatedButton(
              onPressed: () async {
                if (titleCtrl.text.trim().isEmpty || contentCtrl.text.trim().isEmpty) return;
                Navigator.of(ctx).pop();
                try {
                  await ApiService.createKnowledge(
                    category: category,
                    title: titleCtrl.text.trim(),
                    content: contentCtrl.text.trim(),
                    relatedFilePath: fileCtrl.text.trim().isEmpty ? null : fileCtrl.text.trim(),
                    relatedSymbol: symbolCtrl.text.trim().isEmpty ? null : symbolCtrl.text.trim(),
                  );
                  _loadKnowledge();
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Failed to save knowledge: $e'), backgroundColor: p.inferred),
                    );
                  }
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: p.accent,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
              child: const Text('Save Knowledge'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _items.where((item) {
      if (_searchQuery.isEmpty) return true;
      final q = _searchQuery.toLowerCase();
      return item.title.toLowerCase().contains(q) ||
          item.content.toLowerCase().contains(q) ||
          (item.relatedFilePath?.toLowerCase().contains(q) ?? false);
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── Top Header ──
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Knowledge Base',
                    style: UnoTypography.body(color: p.text, fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Architectural decision records, domain conventions, and team knowledge',
                    style: UnoTypography.body(color: p.textSec, fontSize: 12),
                  ),
                ],
              ),
              Row(
                children: [
                  // Status toggle (Active / Archived)
                  Container(
                    decoration: BoxDecoration(
                      color: p.bgSurface,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: p.div),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _statusToggleBtn('ACTIVE', 'Active'),
                        _statusToggleBtn('ARCHIVED', 'Archived'),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  ElevatedButton.icon(
                    onPressed: _showCreateDialog,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: p.accent,
                      foregroundColor: Colors.white,
                      elevation: 0,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    icon: const Icon(LucideIcons.plus, size: 15),
                    label: Text(
                      'Record Knowledge',
                      style: UnoTypography.body(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        // ── Filter & Search Strip ──
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          decoration: BoxDecoration(
            color: p.bgSurface,
            border: Border(
              top: BorderSide(color: p.div),
              bottom: BorderSide(color: p.div),
            ),
          ),
          child: Row(
            children: [
              Text('Category:', style: UnoTypography.mono(color: p.textSec, fontSize: 11)),
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
                      _loadKnowledge();
                    },
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                      decoration: BoxDecoration(
                        color: isSel ? p.accent.withValues(alpha: 0.15) : Colors.transparent,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: isSel ? p.accent : p.div),
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
              const Spacer(),
              // Search input
              Container(
                width: 220,
                height: 32,
                decoration: BoxDecoration(
                  color: p.bgElevated,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: p.div),
                ),
                child: TextField(
                  style: UnoTypography.body(color: p.text, fontSize: 12),
                  decoration: InputDecoration(
                    hintText: 'Search knowledge…',
                    hintStyle: UnoTypography.body(color: p.textSec, fontSize: 12),
                    prefixIcon: Icon(LucideIcons.search, size: 14, color: p.textSec),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.symmetric(vertical: 8),
                  ),
                  onChanged: (v) => setState(() => _searchQuery = v),
                ),
              ),
            ],
          ),
        ),

        // ── Knowledge Cards Grid ──
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
                          Text('Failed to load knowledge', style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600)),
                          const SizedBox(height: 4),
                          Text(_error!, style: UnoTypography.body(color: p.textSec, fontSize: 12)),
                          const SizedBox(height: 12),
                          TextButton.icon(
                            onPressed: _loadKnowledge,
                            icon: Icon(LucideIcons.refreshCcw, size: 14, color: p.accent),
                            label: Text('Retry', style: UnoTypography.body(color: p.accent, fontSize: 12)),
                          ),
                        ],
                      ),
                    )
                  : filtered.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(LucideIcons.bookOpen, size: 40, color: p.div),
                              const SizedBox(height: 12),
                              Text(
                                'No knowledge records found',
                                style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Record architectural decisions, business rules, or conventions.',
                                style: UnoTypography.body(color: p.textSec, fontSize: 12),
                              ),
                            ],
                          ),
                        )
                      : GridView.builder(
                          padding: const EdgeInsets.all(24),
                          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                            maxCrossAxisExtent: 460,
                            mainAxisExtent: 220,
                            crossAxisSpacing: 16,
                            mainAxisSpacing: 16,
                          ),
                          itemCount: filtered.length,
                          itemBuilder: (context, index) {
                            final item = filtered[index];
                            return _buildKnowledgeCard(item);
                          },
                        ),
        ),
      ],
    );
  }

  Widget _buildKnowledgeCard(ProjectKnowledge item) {
    return Container(
      padding: const EdgeInsets.all(18),
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
              _categoryPill(item.category),
              const Spacer(),
              PopupMenuButton<String>(
                icon: Icon(LucideIcons.moreVertical, size: 15, color: p.textSec),
                padding: EdgeInsets.zero,
                color: p.bgElevated,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                  side: BorderSide(color: p.div),
                ),
                onSelected: (action) {
                  if (action == 'archive' || action == 'restore') {
                    _toggleArchive(item);
                  }
                },
                itemBuilder: (context) => [
                  PopupMenuItem(
                    value: item.status == 'ACTIVE' ? 'archive' : 'restore',
                    child: Text(
                      item.status == 'ACTIVE' ? 'Archive item' : 'Restore item',
                      style: UnoTypography.body(color: p.text, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            item.title,
            style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w600),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 6),
          Expanded(
            child: Text(
              item.content,
              style: UnoTypography.body(color: p.textSec, fontSize: 12, height: 1.4),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              if (item.relatedFilePath != null)
                Expanded(
                  child: InkWell(
                    onTap: () => widget.onNavigateToFile?.call(item.relatedFilePath!),
                    child: Row(
                      children: [
                        Icon(LucideIcons.fileText, size: 12, color: p.accent),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            item.relatedFilePath!,
                            style: UnoTypography.mono(color: p.accent, fontSize: 11),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              Text(
                item.author.isNotEmpty ? item.author : 'Automated',
                style: UnoTypography.mono(color: p.textSec, fontSize: 10),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _categoryPill(String category) {
    Color color;
    switch (category.toUpperCase()) {
      case 'ADR':
        color = const Color(0xFF3B82F6);
        break;
      case 'BUSINESS_RULE':
        color = const Color(0xFF10B981);
        break;
      case 'TECH_DEBT':
        color = const Color(0xFFEF4444);
        break;
      case 'DOMAIN_CONCEPT':
        color = const Color(0xFF8B5CF6);
        break;
      default:
        color = widget.palette.accent;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        category,
        style: UnoTypography.mono(color: color, fontSize: 10, letterSpacing: 0.5),
      ),
    );
  }

  Widget _statusToggleBtn(String statusVal, String label) {
    final isSel = _status == statusVal;
    return InkWell(
      onTap: () {
        setState(() => _status = statusVal);
        _loadKnowledge();
      },
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSel ? p.accent.withValues(alpha: 0.15) : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          label,
          style: UnoTypography.mono(
            color: isSel ? p.accent : p.textSec,
            fontSize: 11,
            fontWeight: isSel ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}
