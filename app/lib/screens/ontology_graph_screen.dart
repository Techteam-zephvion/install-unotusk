import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/mermaid_diagram.dart';

class OntologyGraphScreen extends StatefulWidget {
  final UnoPalette palette;
  final ValueChanged<String>? onNavigateToFile;
  final String? projectId;
  final String? projectName;

  const OntologyGraphScreen({
    super.key,
    required this.palette,
    this.onNavigateToFile,
    this.projectId,
    this.projectName,
  });

  @override
  State<OntologyGraphScreen> createState() => _OntologyGraphScreenState();
}

class _OntologyGraphScreenState extends State<OntologyGraphScreen> {
  int? _hoveredNodeId = 0;
  int? _draggingNodeId;
  List<OntologyNode> _nodes = [];
  List<List<int>> _edges = [];
  final Map<int, Offset> _positions = {};

  final TransformationController _transformController = TransformationController();
  double _currentZoom = 1.0;
  bool _isLoading = true;
  String _activeViewMode = 'diagram'; // 'diagram' or 'graph'
  String _mermaidCode = '';

  @override
  void initState() {
    super.initState();
    _loadOntology();
  }

  @override
  void didUpdateWidget(OntologyGraphScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.projectId != widget.projectId || oldWidget.projectName != widget.projectName) {
      _loadOntology();
    }
  }

  @override
  void dispose() {
    _transformController.dispose();
    super.dispose();
  }

  void _loadOntology() async {
    setState(() => _isLoading = true);
    try {
      final pid = widget.projectId;
      final pName = widget.projectName ?? ApiService.activeProject?.name ?? 'Project';

      final nodes = await ApiService.fetchOntologyNodes(projectId: pid);
      final edges = await ApiService.fetchOntologyEdges(projectId: pid);

      String cleanCode = '';
      try {
        final repoCtx = await ApiService.fetchRepositoryContext(pid);
        final files = repoCtx.files.map((f) => f.path).toList();

        final synth = ApiService.synthesizeMermaidDiagram(
          content: '',
          question: 'system architecture diagram and component topology for $pName',
          citations: files.take(8).toList(),
          evidence: [],
        );
        final mMatch = RegExp(r'```mermaid([\s\S]*?)```').firstMatch(synth);
        cleanCode = mMatch != null ? mMatch.group(1)!.trim() : synth;
      } catch (_) {}

      if (cleanCode.isEmpty) {
        cleanCode = '''
flowchart TD
    subgraph UI ["User Interface & Presentation Layer"]
        F_0["Client App / Web Shell"]
    end
    subgraph API ["Routing & API Layer"]
        F_1[":28000 Gateway & Auth Router"]
    end
    subgraph Logic ["Domain Logic & Intelligence"]
        F_2["Context & Discovery Engine"]
    end
    subgraph Data ["Data & Persistence Layer"]
        F_3[("PostgreSQL 16 & pgvector")]
    end
    F_0 -->|invokes| F_1
    F_1 -->|routes to| F_2
    F_2 -->|persists/queries| F_3
    classDef ui fill:#1E293B,stroke:#38BDF8,stroke-width:1.5px,color:#F8FAFC;
    classDef api fill:#2A1B3D,stroke:#A855F7,stroke-width:1.5px,color:#F8FAFC;
    classDef domain fill:#1A2E26,stroke:#10B981,stroke-width:1.5px,color:#F8FAFC;
    classDef data fill:#332200,stroke:#F59E0B,stroke-width:1.5px,color:#F8FAFC;
    class F_0 ui;
    class F_1 api;
    class F_2 domain;
    class F_3 data;
''';
      }

      if (mounted) {
        setState(() {
          _nodes = nodes;
          _edges = edges;
          _mermaidCode = cleanCode;
          _positions.clear();
          for (final n in nodes) {
            _positions[n.id] = Offset(n.cx, n.cy);
          }
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildViewModeButton(String mode, String label, IconData icon, UnoPalette p) {
    final active = _activeViewMode == mode;
    return InkWell(
      onTap: () => setState(() => _activeViewMode = mode),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: active ? p.accent.withValues(alpha: 0.18) : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 13, color: active ? p.accent : p.textSec),
            const SizedBox(width: 6),
            Text(
              label,
              style: UnoTypography.mono(
                color: active ? p.accent : p.textSec,
                fontSize: 11,
                fontWeight: active ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _getNodeColor(int id) {
    switch (id) {
      case 0:
        return widget.palette.accent;
      case 1:
      case 7:
        return const Color(0xFF5BA495); // Mint Teal (Services)
      case 2:
      case 4:
      case 5:
        return const Color(0xFFE5A93C); // Amber Gold (Commits / Decisions / DB)
      case 3:
      case 8:
        return const Color(0xFFE06C75); // Rose Pink (Tickets / Threads)
      case 6:
      case 9:
        return const Color(0xFF9E9E94); // Warm Gray / Tan (Persons / Packages)
      default:
        return const Color(0xFF5B8FF9);
    }
  }

  /// Finds all upstream caller nodes (who depends on selected node)
  List<int> _getCallerNodeIds(int targetId) {
    final callers = <int>[];
    for (final edge in _edges) {
      if (edge.length >= 2 && edge[1] == targetId) {
        callers.add(edge[0]);
      }
    }
    return callers;
  }

  /// Finds all downstream callee nodes (what selected node depends on)
  List<int> _getCalleeNodeIds(int targetId) {
    final callees = <int>[];
    for (final edge in _edges) {
      if (edge.length >= 2 && edge[0] == targetId) {
        callees.add(edge[1]);
      }
    }
    return callees;
  }

  void _zoomIn() {
    setState(() {
      _currentZoom = (_currentZoom * 1.25).clamp(0.4, 3.0);
      _transformController.value = Matrix4.diagonal3Values(_currentZoom, _currentZoom, 1.0);
    });
  }

  void _zoomOut() {
    setState(() {
      _currentZoom = (_currentZoom / 1.25).clamp(0.4, 3.0);
      _transformController.value = Matrix4.diagonal3Values(_currentZoom, _currentZoom, 1.0);
    });
  }

  void _resetZoom() {
    setState(() {
      _currentZoom = 1.0;
      _transformController.value = Matrix4.identity();
    });
  }

  int? _hitTestNode(Offset localPos) {
    int? hitId;
    double bestDistSq = 900.0; // 30px hit radius
    for (final node in _nodes) {
      final pos = _positions[node.id] ?? Offset(node.cx, node.cy);
      final dx = localPos.dx - pos.dx;
      final dy = localPos.dy - pos.dy;
      final distSq = dx * dx + dy * dy;
      if (distSq < bestDistSq) {
        bestDistSq = distSq;
        hitId = node.id;
      }
    }
    return hitId;
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.palette;
    final selectedNode = _nodes.where((n) => n.id == _hoveredNodeId).firstOrNull;
    final callers = _hoveredNodeId != null ? _getCallerNodeIds(_hoveredNodeId!) : <int>[];
    final callees = _hoveredNodeId != null ? _getCalleeNodeIds(_hoveredNodeId!) : <int>[];

    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 20, 28, 22),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Row
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'ARCHITECTURE & ONTOLOGY',
                          style: UnoTypography.mono(
                            color: p.textMuted,
                            fontSize: 10.5,
                            letterSpacing: 1.0,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Interactive Graph Visualizer',
                          style: UnoTypography.headingSerif(
                            color: p.text,
                            fontSize: 25,
                            fontWeight: FontWeight.w600,
                            height: 1.15,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Pan, zoom, drag nodes, and inspect live caller/callee dependencies across codebase entities.',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: UnoTypography.body(
                            color: p.textSec,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        decoration: BoxDecoration(
                          color: p.bgElevated.withValues(alpha: 0.85),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: p.div),
                        ),
                        padding: const EdgeInsets.all(3),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            _buildViewModeButton('diagram', 'Architecture Diagram', LucideIcons.layoutGrid, p),
                            const SizedBox(width: 4),
                            _buildViewModeButton('graph', '2D Topology Graph', LucideIcons.gitFork, p),
                          ],
                        ),
                      ),
                      if (_activeViewMode == 'graph' && _nodes.isNotEmpty) ...[
                        const SizedBox(width: 12),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                          decoration: BoxDecoration(
                            color: p.bgElevated.withValues(alpha: 0.75),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: p.div),
                          ),
                          child: Text(
                            '${_nodes.length} entities  ·  ${_edges.length} relationships',
                            style: UnoTypography.mono(
                              color: p.accentMuted,
                              fontSize: 11,
                              letterSpacing: 0.2,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Content Body
              Expanded(
                child: _isLoading
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 28,
                              height: 28,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.2,
                                color: p.accent,
                              ),
                            ),
                            const SizedBox(height: 14),
                            Text(
                              'Mapping system architecture for ${(widget.projectName != null && widget.projectName!.isNotEmpty) ? formatDisplayTitle(widget.projectName!) : "project"}...',
                              style: UnoTypography.mono(color: p.textSec, fontSize: 12),
                            ),
                          ],
                        ),
                      )
                    : _activeViewMode == 'diagram'
                        ? Container(
                            decoration: BoxDecoration(
                              gradient: p.sectionGradient,
                              border: Border.all(color: p.div),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            padding: const EdgeInsets.all(16),
                            clipBehavior: Clip.antiAlias,
                            child: SingleChildScrollView(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  Row(
                                    children: [
                                      Icon(LucideIcons.layoutGrid, size: 14, color: p.accent),
                                      const SizedBox(width: 8),
                                      Text(
                                        'System Architecture Blueprint — ${(widget.projectName != null && widget.projectName!.isNotEmpty) ? formatDisplayTitle(widget.projectName!) : "Active Project"}',
                                        style: UnoTypography.body(color: p.text, fontSize: 13, fontWeight: FontWeight.w600),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 12),
                                  MermaidDiagram(
                                    code: _mermaidCode,
                                    palette: p,
                                  ),
                                ],
                              ),
                            ),
                          )
                        : Container(
                            decoration: BoxDecoration(
                              gradient: p.sectionGradient,
                              border: Border.all(color: p.div),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            clipBehavior: Clip.antiAlias,
                            child: _nodes.isEmpty
                                ? Center(
                                    child: Column(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(LucideIcons.gitFork, size: 36, color: p.textMuted),
                                        const SizedBox(height: 12),
                                        Text(
                                          'No entities indexed yet for this project.',
                                          style: UnoTypography.body(color: p.text, fontSize: 14, fontWeight: FontWeight.w500),
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          'Trigger an ingestion reindex or view the Architecture Diagram tab above.',
                                          style: UnoTypography.mono(color: p.textSec, fontSize: 11),
                                        ),
                                        const SizedBox(height: 16),
                                        ElevatedButton.icon(
                                          onPressed: () => _loadOntology(),
                                          icon: const Icon(LucideIcons.refreshCw, size: 13),
                                          label: const Text('Refresh Architecture'),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor: p.accent,
                                            foregroundColor: Colors.white,
                                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                                          ),
                                        ),
                                      ],
                                    ),
                                  )
                                : Stack(
                                    children: [
                                      // Interactive Pan / Zoom / Drag Canvas
                      InteractiveViewer(
                        transformationController: _transformController,
                        minScale: 0.4,
                        maxScale: 3.0,
                        boundaryMargin: const EdgeInsets.all(500),
                        panEnabled: _draggingNodeId == null,
                        child: LayoutBuilder(
                          builder: (context, constraints) {
                            final size = Size(
                              math.max(constraints.maxWidth, 900),
                              math.max(constraints.maxHeight, 560),
                            );

                            return MouseRegion(
                              cursor: _draggingNodeId != null
                                  ? SystemMouseCursors.grabbing
                                  : SystemMouseCursors.grab,
                              child: GestureDetector(
                                behavior: HitTestBehavior.opaque,
                                onPanStart: (details) {
                                  final hit = _hitTestNode(details.localPosition);
                                  if (hit != null) {
                                    setState(() {
                                      _draggingNodeId = hit;
                                      _hoveredNodeId = hit;
                                    });
                                  }
                                },
                                onPanUpdate: (details) {
                                  if (_draggingNodeId != null) {
                                    setState(() {
                                      final current = _positions[_draggingNodeId!] ?? Offset.zero;
                                      _positions[_draggingNodeId!] = current + details.delta;
                                    });
                                  }
                                },
                                onPanEnd: (_) {
                                  setState(() => _draggingNodeId = null);
                                },
                                onTapUp: (details) {
                                  final tapped = _hitTestNode(details.localPosition);
                                  if (tapped != null) {
                                    setState(() {
                                      _hoveredNodeId =
                                          _hoveredNodeId == tapped ? null : tapped;
                                    });
                                  }
                                },
                                child: CustomPaint(
                                  size: size,
                                  painter: _InteractiveOntologyGraphPainter(
                                    nodes: _nodes,
                                    edges: _edges,
                                    positions: _positions,
                                    hoveredNodeId: _hoveredNodeId,
                                    callers: callers,
                                    callees: callees,
                                    palette: p,
                                    getNodeColor: _getNodeColor,
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                      ),

                      // Canvas Floating Controls (Zoom In, Zoom Out, Reset, Legend)
                      Positioned(
                        top: 14,
                        right: 14,
                        child: Container(
                          decoration: BoxDecoration(
                            color: p.bgElevated.withValues(alpha: 0.90),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: p.div),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.15),
                                blurRadius: 8,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              IconButton(
                                icon: const Icon(LucideIcons.zoomIn, size: 16),
                                tooltip: 'Zoom In',
                                color: p.text,
                                onPressed: _zoomIn,
                              ),
                              Container(width: 1, height: 18, color: p.div),
                              IconButton(
                                icon: const Icon(LucideIcons.zoomOut, size: 16),
                                tooltip: 'Zoom Out',
                                color: p.text,
                                onPressed: _zoomOut,
                              ),
                              Container(width: 1, height: 18, color: p.div),
                              IconButton(
                                icon: const Icon(LucideIcons.rotateCcw, size: 15),
                                tooltip: 'Reset View',
                                color: p.text,
                                onPressed: _resetZoom,
                              ),
                            ],
                          ),
                        ),
                      ),

                      // Floating Interactive Legend
                      Positioned(
                        bottom: 14,
                        left: 14,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                          decoration: BoxDecoration(
                            color: p.bgElevated.withValues(alpha: 0.88),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: p.div),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              _buildLegendDot(const Color(0xFF5BA495), 'Callers (Upstream)'),
                              const SizedBox(width: 12),
                              _buildLegendDot(const Color(0xFFE5A93C), 'Callees (Downstream)'),
                              const SizedBox(width: 12),
                              _buildLegendDot(p.accent, 'Selected Entity'),
                            ],
                          ),
                        ),
                      ),

                      // Sliding Node Detail Inspector Panel
                      if (selectedNode != null)
                        Positioned(
                          top: 14,
                          left: 14,
                          child: Container(
                            width: 290,
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: p.bgElevated.withValues(alpha: 0.96),
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: p.accent.withValues(alpha: 0.40)),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withValues(alpha: 0.20),
                                  blurRadius: 16,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Row(
                                  children: [
                                    Container(
                                      width: 10,
                                      height: 10,
                                      decoration: BoxDecoration(
                                        color: _getNodeColor(selectedNode.id),
                                        shape: BoxShape.circle,
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Text(
                                        selectedNode.label,
                                        style: UnoTypography.body(
                                          color: p.text,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w600,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    InkWell(
                                      onTap: () => setState(() => _hoveredNodeId = null),
                                      child: Icon(LucideIcons.x, size: 14, color: p.textMuted),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  selectedNode.subtitle ?? selectedNode.type,
                                  style: UnoTypography.mono(
                                    color: p.textSec,
                                    fontSize: 11,
                                  ),
                                ),
                                const SizedBox(height: 10),
                                Divider(height: 1, color: p.div),
                                const SizedBox(height: 10),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      'Callers (Inbound): ${callers.length}',
                                      style: UnoTypography.mono(
                                        color: const Color(0xFF5BA495),
                                        fontSize: 11,
                                      ),
                                    ),
                                    Text(
                                      'Callees (Outbound): ${callees.length}',
                                      style: UnoTypography.mono(
                                        color: const Color(0xFFE5A93C),
                                        fontSize: 11,
                                      ),
                                    ),
                                  ],
                                ),
                                if (widget.onNavigateToFile != null) ...[
                                  const SizedBox(height: 12),
                                  InkWell(
                                    onTap: () => widget.onNavigateToFile?.call(selectedNode.subtitle ?? selectedNode.label),
                                    borderRadius: BorderRadius.circular(6),
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                      decoration: BoxDecoration(
                                        color: p.accent.withValues(alpha: 0.12),
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(color: p.accent.withValues(alpha: 0.35)),
                                      ),
                                      child: Row(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Icon(LucideIcons.fileCode, size: 13, color: p.accent),
                                          const SizedBox(width: 6),
                                          Text(
                                            'Inspect in Files Browser',
                                            style: UnoTypography.body(
                                              color: p.accent,
                                              fontSize: 11.5,
                                              fontWeight: FontWeight.w500,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLegendDot(Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: UnoTypography.mono(
            color: widget.palette.textSec,
            fontSize: 10,
          ),
        ),
      ],
    );
  }
}

class _InteractiveOntologyGraphPainter extends CustomPainter {
  final List<OntologyNode> nodes;
  final List<List<int>> edges;
  final Map<int, Offset> positions;
  final int? hoveredNodeId;
  final List<int> callers;
  final List<int> callees;
  final UnoPalette palette;
  final Color Function(int) getNodeColor;

  _InteractiveOntologyGraphPainter({
    required this.nodes,
    required this.edges,
    required this.positions,
    required this.hoveredNodeId,
    required this.callers,
    required this.callees,
    required this.palette,
    required this.getNodeColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (nodes.isEmpty) return;

    final isDark = palette.isDark;
    final inactiveEdgePaint = Paint()
      ..color = isDark ? palette.div.withValues(alpha: 0.45) : palette.div.withValues(alpha: 0.6)
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    final callerEdgePaint = Paint()
      ..color = const Color(0xFF5BA495)
      ..strokeWidth = 2.4
      ..style = PaintingStyle.stroke;

    final calleeEdgePaint = Paint()
      ..color = const Color(0xFFE5A93C)
      ..strokeWidth = 2.4
      ..style = PaintingStyle.stroke;

    final activeEdgePaint = Paint()
      ..color = palette.accent
      ..strokeWidth = 2.2
      ..style = PaintingStyle.stroke;

    // 1. Draw Inactive Background Edges
    for (final edge in edges) {
      if (edge.length < 2) continue;
      final fromId = edge[0];
      final toId = edge[1];

      final isCaller = hoveredNodeId != null && toId == hoveredNodeId;
      final isCallee = hoveredNodeId != null && fromId == hoveredNodeId;
      final isGeneralActive = hoveredNodeId != null && (fromId == hoveredNodeId || toId == hoveredNodeId);

      if (!isCaller && !isCallee && !isGeneralActive) {
        final p1 = positions[fromId];
        final p2 = positions[toId];
        if (p1 != null && p2 != null) {
          canvas.drawLine(p1, p2, inactiveEdgePaint);
        }
      }
    }

    // 2. Draw Active / Caller / Callee Highlighted Edges
    for (final edge in edges) {
      if (edge.length < 2) continue;
      final fromId = edge[0];
      final toId = edge[1];

      final isCaller = hoveredNodeId != null && toId == hoveredNodeId;
      final isCallee = hoveredNodeId != null && fromId == hoveredNodeId;
      final isGeneralActive = hoveredNodeId != null && (fromId == hoveredNodeId || toId == hoveredNodeId);

      if (isCaller || isCallee || isGeneralActive) {
        final p1 = positions[fromId];
        final p2 = positions[toId];
        if (p1 != null && p2 != null) {
          final paintToUse = isCaller
              ? callerEdgePaint
              : (isCallee ? calleeEdgePaint : activeEdgePaint);
          canvas.drawLine(p1, p2, paintToUse);

          // Draw direction indicator dot
          final mid = Offset((p1.dx + p2.dx) / 2, (p1.dy + p2.dy) / 2);
          canvas.drawCircle(mid, 3.0, Paint()..color = paintToUse.color);
        }
      }
    }

    // 3. Draw Nodes
    for (final node in nodes) {
      final center = positions[node.id] ?? Offset(node.cx, node.cy);
      final isSelected = node.id == hoveredNodeId;
      final isCaller = callers.contains(node.id);
      final isCallee = callees.contains(node.id);
      final isDimmed = hoveredNodeId != null && !isSelected && !isCaller && !isCallee;

      final baseColor = isCaller
          ? const Color(0xFF5BA495)
          : (isCallee ? const Color(0xFFE5A93C) : getNodeColor(node.id));

      final radius = isSelected ? 12.0 : (isCaller || isCallee ? 9.5 : 7.0);

      // Node shadow / glow
      if (isSelected || isCaller || isCallee) {
        canvas.drawCircle(
          center,
          radius + 4.0,
          Paint()
            ..color = baseColor.withValues(alpha: 0.35)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
        );
      }

      // Outer node ring
      canvas.drawCircle(
        center,
        radius,
        Paint()
          ..color = isDimmed ? baseColor.withValues(alpha: 0.25) : baseColor
          ..style = PaintingStyle.fill,
      );

      // Inner core
      canvas.drawCircle(
        center,
        radius * 0.45,
        Paint()
          ..color = palette.bgBase
          ..style = PaintingStyle.fill,
      );

      // Text label
      final textSpan = TextSpan(
        text: node.label,
        style: UnoTypography.mono(
          color: isDimmed
              ? palette.textMuted.withValues(alpha: 0.45)
              : (isSelected ? palette.text : palette.textSec),
          fontSize: isSelected ? 12 : 10,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
        ),
      );

      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(
        canvas,
        Offset(center.dx - textPainter.width / 2, center.dy + radius + 4),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _InteractiveOntologyGraphPainter oldDelegate) {
    return true;
  }
}
