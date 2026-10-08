import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/workspace_models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

/// Architecture Screen — Component graph, layers, and dependency structure.
/// Ported from repo's architecture_tab using UnoPalette styling.
class ArchitectureScreen extends StatefulWidget {
  final UnoPalette palette;
  final Function(String filePath)? onNavigateToFile;

  const ArchitectureScreen({
    super.key,
    required this.palette,
    this.onNavigateToFile,
  });

  @override
  State<ArchitectureScreen> createState() => _ArchitectureScreenState();
}

class _ArchitectureScreenState extends State<ArchitectureScreen> {
  UnoPalette get p => widget.palette;

  bool _loading = true;
  String? _error;
  List<ComponentNode> _allComponents = [];
  ComponentNode? _selectedComponent;

  String _searchQuery = '';
  String _selectedLayer = 'ALL';

  final List<String> _layers = [
    'ALL',
    'PRESENTATION',
    'DOMAIN',
    'DATA',
    'CORE',
  ];

  @override
  void initState() {
    super.initState();
    _loadArchitectureData();
  }

  Future<void> _loadArchitectureData() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final deps = await ApiService.fetchProjectDependencies();
      final files = await ApiService.fetchProjectFiles();

      final components = ComponentNode.aggregateComponents(
        dependencies: deps,
        files: files,
      );

      if (mounted) {
        setState(() {
          _allComponents = components;
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
              'Mapping architectural components and dependencies…',
              style: UnoTypography.body(color: p.textSec, fontSize: 13),
            ),
          ],
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(LucideIcons.alertTriangle, size: 36, color: p.inferred),
            const SizedBox(height: 12),
            Text(
              'Failed to map architecture',
              style: UnoTypography.body(color: p.text, fontSize: 15, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            Text(_error!, style: UnoTypography.body(color: p.textSec, fontSize: 12)),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: _loadArchitectureData,
              style: ElevatedButton.styleFrom(
                backgroundColor: p.accent,
                foregroundColor: Colors.white,
              ),
              icon: const Icon(LucideIcons.refreshCcw, size: 14),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    // Filter components
    final filtered = _allComponents.where((comp) {
      final matchesSearch = _searchQuery.isEmpty ||
          comp.name.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          comp.path.toLowerCase().contains(_searchQuery.toLowerCase());

      final matchesLayer = _selectedLayer == 'ALL' ||
          comp.layer.toUpperCase() == _selectedLayer;

      return matchesSearch && matchesLayer;
    }).toList();

    return Row(
      children: [
        // ── Main Components Grid Column ──
        Expanded(
          flex: 6,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header & Search
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 20, 24, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Architecture & Components',
                            style: UnoTypography.body(color: p.text, fontSize: 18, fontWeight: FontWeight.w600),
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${_allComponents.length} detected architecture modules across clean layers',
                            style: UnoTypography.body(color: p.textSec, fontSize: 12),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    // Search box
                    Flexible(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 240),
                        child: Container(
                          height: 36,
                          decoration: BoxDecoration(
                            color: p.bgSurface,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: p.div),
                          ),
                          child: TextField(
                            textAlignVertical: TextAlignVertical.center,
                            style: UnoTypography.body(color: p.text, fontSize: 12),
                            decoration: InputDecoration(
                              isDense: true,
                              hintText: 'Search modules…',
                              hintStyle: UnoTypography.body(color: p.textSec, fontSize: 12),
                              prefixIcon: Icon(LucideIcons.search, size: 14, color: p.textSec),
                              prefixIconConstraints: const BoxConstraints(minWidth: 32, minHeight: 36),
                              border: InputBorder.none,
                              contentPadding: const EdgeInsets.only(right: 8),
                            ),
                            onChanged: (v) => setState(() => _searchQuery = v),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Layer Filter Bar
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
                    Text(
                      'Layer:',
                      style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                    ),
                    const SizedBox(width: 10),
                    ..._layers.map((layer) {
                      final isSel = _selectedLayer == layer;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: InkWell(
                          onTap: () => setState(() => _selectedLayer = layer),
                          borderRadius: BorderRadius.circular(6),
                          child: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: isSel ? p.accent.withValues(alpha: 0.15) : Colors.transparent,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: isSel ? p.accent : p.div,
                              ),
                            ),
                            child: Text(
                              layer,
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

              // Components Grid
              Expanded(
                child: filtered.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(LucideIcons.box, size: 36, color: p.div),
                            const SizedBox(height: 12),
                            Text(
                              'No components found',
                              style: UnoTypography.body(color: p.textSec, fontSize: 13),
                            ),
                          ],
                        ),
                      )
                    : GridView.builder(
                        padding: const EdgeInsets.all(20),
                        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                          maxCrossAxisExtent: 360,
                          mainAxisExtent: 160,
                          crossAxisSpacing: 14,
                          mainAxisSpacing: 14,
                        ),
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final comp = filtered[index];
                          final isSelected = _selectedComponent?.id == comp.id;

                          return InkWell(
                            onTap: () => setState(() => _selectedComponent = comp),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? p.accent.withValues(alpha: 0.08)
                                    : p.bgSurface,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: isSelected ? p.accent : p.div,
                                ),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      _layerBadge(comp.layer),
                                      const Spacer(),
                                      Text(
                                        '${comp.fileCount} ${comp.fileCount == 1 ? "file" : "files"}',
                                        style: UnoTypography.mono(color: p.textSec, fontSize: 10),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 10),
                                  Text(
                                    comp.name,
                                    style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w600),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 3),
                                  Text(
                                    comp.path,
                                    style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const Spacer(),
                                  Row(
                                    children: [
                                      _depCounter(LucideIcons.arrowUpRight, '${comp.outgoingDependencies.length} out'),
                                      const SizedBox(width: 8),
                                      _depCounter(LucideIcons.arrowDownLeft, '${comp.incomingDependencies.length} in'),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),

        // ── Component Detail Side Panel ──
        Container(
          width: 380,
          decoration: BoxDecoration(
            color: p.bgSurface,
            border: Border(left: BorderSide(color: p.div)),
          ),
          child: _selectedComponent == null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(LucideIcons.boxes, size: 36, color: p.div),
                      const SizedBox(height: 12),
                      Text(
                        'Select a component to inspect dependencies',
                        style: UnoTypography.body(color: p.textSec, fontSize: 13),
                      ),
                    ],
                  ),
                )
              : _buildComponentDetailPanel(_selectedComponent!),
        ),
      ],
    );
  }

  Widget _buildComponentDetailPanel(ComponentNode comp) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _layerBadge(comp.layer),
              IconButton(
                icon: Icon(LucideIcons.x, size: 16, color: p.textSec),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: () => setState(() => _selectedComponent = null),
              ),
            ],
          ),
          const SizedBox(height: 12),

          Text(
            comp.name,
            style: UnoTypography.body(color: p.text, fontSize: 17, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          Text(
            comp.path,
            style: UnoTypography.mono(color: p.textSec, fontSize: 11),
          ),
          Divider(height: 28, color: p.div),

          // Outgoing dependencies
          Row(
            children: [
              Icon(LucideIcons.arrowUpRight, size: 14, color: p.accent),
              const SizedBox(width: 6),
              Text(
                'Depends On (${comp.outgoingDependencies.length})',
                style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (comp.outgoingDependencies.isEmpty)
            Text('No outgoing dependencies', style: UnoTypography.body(color: p.textSec, fontSize: 12))
          else
            ...comp.outgoingDependencies.take(8).map((dep) => Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: p.bgElevated,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: p.div),
                  ),
                  child: Row(
                    children: [
                      Icon(LucideIcons.chevronRight, size: 12, color: p.textSec),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          dep.targetPath ?? dep.externalPackage ?? dep.id,
                          style: UnoTypography.mono(color: p.text, fontSize: 11),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                )),
          const SizedBox(height: 20),

          // Incoming dependencies
          Row(
            children: [
              Icon(LucideIcons.arrowDownLeft, size: 14, color: const Color(0xFF10B981)),
              const SizedBox(width: 6),
              Text(
                'Used By (${comp.incomingDependencies.length})',
                style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (comp.incomingDependencies.isEmpty)
            Text('No incoming dependencies (leaf module)', style: UnoTypography.body(color: p.textSec, fontSize: 12))
          else
            ...comp.incomingDependencies.take(8).map((dep) => Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: p.bgElevated,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: p.div),
                  ),
                  child: Row(
                    children: [
                      Icon(LucideIcons.chevronLeft, size: 12, color: p.textSec),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          dep.sourcePath ?? dep.id,
                          style: UnoTypography.mono(color: p.text, fontSize: 11),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                )),
          const SizedBox(height: 24),

          // Action: Jump to Files
          if (widget.onNavigateToFile != null)
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => widget.onNavigateToFile!(comp.path),
                style: OutlinedButton.styleFrom(
                  side: BorderSide(color: p.div),
                  foregroundColor: p.text,
                  padding: const EdgeInsets.symmetric(vertical: 11),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                icon: const Icon(LucideIcons.folderTree, size: 14),
                label: Text(
                  'Browse Component Files',
                  style: UnoTypography.body(color: p.text, fontSize: 12, fontWeight: FontWeight.w500),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _layerBadge(String layer) {
    Color bg;
    Color fg;
    switch (layer.toUpperCase()) {
      case 'PRESENTATION':
        bg = const Color(0xFF3B82F6).withValues(alpha: 0.15);
        fg = const Color(0xFF3B82F6);
        break;
      case 'DOMAIN':
        bg = const Color(0xFF10B981).withValues(alpha: 0.15);
        fg = const Color(0xFF10B981);
        break;
      case 'DATA':
        bg = const Color(0xFFF59E0B).withValues(alpha: 0.15);
        fg = const Color(0xFFF59E0B);
        break;
      case 'CORE':
        bg = const Color(0xFF8B5CF6).withValues(alpha: 0.15);
        fg = const Color(0xFF8B5CF6);
        break;
      default:
        bg = p.bgElevated;
        fg = p.textSec;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        layer.toUpperCase(),
        style: UnoTypography.mono(color: fg, fontSize: 9, letterSpacing: 0.5),
      ),
    );
  }

  Widget _depCounter(IconData icon, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: p.textSec),
        const SizedBox(width: 4),
        Text(
          label,
          style: UnoTypography.mono(color: p.textSec, fontSize: 10),
        ),
      ],
    );
  }
}
