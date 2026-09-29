import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class OntologyGraphScreen extends StatefulWidget {
  final UnoPalette palette;

  const OntologyGraphScreen({super.key, required this.palette});

  @override
  State<OntologyGraphScreen> createState() => _OntologyGraphScreenState();
}

class _OntologyGraphScreenState extends State<OntologyGraphScreen> {
  // Default selected node: 0 (OIDC Decis…) to match the reference view
  int? _hoveredNodeId = 0;
  List<OntologyNode> _nodes = [];
  List<List<int>> _edges = [];

  @override
  void initState() {
    super.initState();
    _loadOntology();
  }

  void _loadOntology() async {
    final nodes = await ApiService.fetchOntologyNodes();
    final edges = await ApiService.fetchOntologyEdges();
    if (mounted) {
      setState(() {
        _nodes = nodes;
        _edges = edges;
      });
    }
  }

  Color _getNodeColor(int id) {
    switch (id) {
      case 0:
        return const Color(0xFFDA7756); // Warm terracotta
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
        return const Color(0xFF9E9E94); // Warm Gray / Tan (Persons)
      default:
        return const Color(0xFF9E9E94);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
      child: Center(
        child: Container(
          constraints: const BoxConstraints(maxWidth: 1040),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header Category Tag
              Text(
                'ONTOLOGY GRAPH',
                style: UnoTypography.mono(
                  color: widget.palette.textSec,
                  fontSize: 11,
                  letterSpacing: 0.8,
                ),
              ),
              const SizedBox(height: 6),

              // Title
              Text(
                'Knowledge Graph',
                style: UnoTypography.brandSerif(
                  palette: widget.palette,
                  fontSize: 28,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),

              // Subtitle
              Text(
                'Entity relationships indexed across commits, tickets, threads, and decisions.',
                style: UnoTypography.body(
                  color: widget.palette.textSec,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 24),

              // Main Graph Container Card
              Container(
                height: 560,
                decoration: BoxDecoration(
                  color: widget.palette.bgSurface,
                  border: Border.all(color: widget.palette.div),
                  borderRadius: BorderRadius.circular(16),
                ),
                padding: const EdgeInsets.all(20),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final scaleX = constraints.maxWidth / 1000.0;
                    final scaleY = constraints.maxHeight / 560.0;
                    final scale = math.min(scaleX, scaleY);
                    final offsetX = (constraints.maxWidth - 1000.0 * scale) / 2;
                    final offsetY = (constraints.maxHeight - 560.0 * scale) / 2;

                    return MouseRegion(
                      cursor: SystemMouseCursors.click,
                      child: GestureDetector(
                        behavior: HitTestBehavior.opaque,
                        onTapUp: (details) {
                          int? tappedId;
                          for (final node in _nodes) {
                            final nx = node.cx * scale + offsetX;
                            final ny = node.cy * scale + offsetY;
                            final distSq = (details.localPosition.dx - nx) *
                                    (details.localPosition.dx - nx) +
                                (details.localPosition.dy - ny) *
                                    (details.localPosition.dy - ny);
                            if (distSq < 1400) {
                              tappedId = node.id;
                              break;
                            }
                          }
                          setState(() {
                            if (tappedId != null) {
                              _hoveredNodeId =
                                  _hoveredNodeId == tappedId ? 0 : tappedId;
                            }
                          });
                        },
                        child: CustomPaint(
                          size: Size(constraints.maxWidth, constraints.maxHeight),
                          painter: _OntologyGraphPainter(
                            nodes: _nodes,
                            edges: _edges,
                            hoveredNodeId: _hoveredNodeId,
                            palette: widget.palette,
                            scale: scale,
                            offsetX: offsetX,
                            offsetY: offsetY,
                            getNodeColor: _getNodeColor,
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
      ),
    );
  }
}

class _OntologyGraphPainter extends CustomPainter {
  final List<OntologyNode> nodes;
  final List<List<int>> edges;
  final int? hoveredNodeId;
  final UnoPalette palette;
  final double scale;
  final double offsetX;
  final double offsetY;
  final Color Function(int) getNodeColor;

  _OntologyGraphPainter({
    required this.nodes,
    required this.edges,
    required this.hoveredNodeId,
    required this.palette,
    required this.scale,
    required this.offsetX,
    required this.offsetY,
    required this.getNodeColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (nodes.isEmpty) return;

    final isDark = palette.bgBase == const Color(0xFF181816);
    final inactiveEdgeColor =
        isDark ? const Color(0xFF2E2E2A) : palette.div.withValues(alpha: 0.6);
    const activeEdgeColor = Color(0xFFDA7756); // Warm terracotta

    // ─────────────────────────────────────────────────────────
    // 1. Draw Inactive Edges (behind)
    // ─────────────────────────────────────────────────────────
    final inactiveEdgePaint = Paint()
      ..color = inactiveEdgeColor
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    for (final edge in edges) {
      if (edge[0] >= nodes.length || edge[1] >= nodes.length) continue;
      final from = nodes[edge[0]];
      final to = nodes[edge[1]];

      final isHighlight = (hoveredNodeId != null &&
          (hoveredNodeId == from.id || hoveredNodeId == to.id));

      if (!isHighlight) {
        final p1 = Offset(from.cx * scale + offsetX, from.cy * scale + offsetY);
        final p2 = Offset(to.cx * scale + offsetX, to.cy * scale + offsetY);
        canvas.drawLine(p1, p2, inactiveEdgePaint);
      }
    }

    // ─────────────────────────────────────────────────────────
    // 2. Draw Active Edges (highlighted in terracotta)
    // ─────────────────────────────────────────────────────────
    final activeEdgePaint = Paint()
      ..color = activeEdgeColor
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    for (final edge in edges) {
      if (edge[0] >= nodes.length || edge[1] >= nodes.length) continue;
      final from = nodes[edge[0]];
      final to = nodes[edge[1]];

      final isHighlight = (hoveredNodeId != null &&
          (hoveredNodeId == from.id || hoveredNodeId == to.id));

      if (isHighlight) {
        final p1 = Offset(from.cx * scale + offsetX, from.cy * scale + offsetY);
        final p2 = Offset(to.cx * scale + offsetX, to.cy * scale + offsetY);
        canvas.drawLine(p1, p2, activeEdgePaint);
      }
    }

    // ─────────────────────────────────────────────────────────
    // 3. Draw Unselected Nodes (Hollow circles + monospace label)
    // ─────────────────────────────────────────────────────────
    for (final node in nodes) {
      if (node.id == hoveredNodeId) continue; // Drawn in step 4

      final center =
          Offset(node.cx * scale + offsetX, node.cy * scale + offsetY);
      final color = getNodeColor(node.id);
      const radius = 7.0;

      // Inner fill matches card background so line underneath is clipped
      final innerPaint = Paint()
        ..color = palette.bgSurface
        ..style = PaintingStyle.fill;
      canvas.drawCircle(center, radius, innerPaint);

      // Hollow ring stroke
      final strokePaint = Paint()
        ..color = color
        ..strokeWidth = 2.0
        ..style = PaintingStyle.stroke;
      canvas.drawCircle(center, radius, strokePaint);

      // Monospace label below
      final textSpan = TextSpan(
        text: node.label,
        style: const TextStyle(
          fontFamily: 'monospace',
          fontSize: 9.5,
          color: Color(0xFF8A8A82),
          letterSpacing: 0.2,
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();

      textPainter.paint(
        canvas,
        Offset(center.dx - textPainter.width / 2, center.dy + 14.0),
      );
    }

    // ─────────────────────────────────────────────────────────
    // 4. Draw Selected Active Node (Solid circle + glow + pill badge)
    // ─────────────────────────────────────────────────────────
    if (hoveredNodeId != null) {
      final activeIndex = nodes.indexWhere((n) => n.id == hoveredNodeId);
      if (activeIndex != -1) {
        final activeNode = nodes[activeIndex];
        final center = Offset(
            activeNode.cx * scale + offsetX, activeNode.cy * scale + offsetY);
        const radius = 8.5;

        // Glow halo (radial blur)
        final glowPaint = Paint()
          ..color = const Color(0xFFDA7756).withValues(alpha: 0.38)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14);
        canvas.drawCircle(center, 22.0, glowPaint);

        // Solid terracotta circle
        final fillPaint = Paint()
          ..color = const Color(0xFFDA7756)
          ..style = PaintingStyle.fill;
        canvas.drawCircle(center, radius, fillPaint);

        // Pill badge background with monospace label
        final textSpan = TextSpan(
          text: activeNode.label,
          style: const TextStyle(
            fontFamily: 'monospace',
            fontSize: 10.0,
            fontWeight: FontWeight.w600,
            color: Color(0xFFEDEDEA),
            letterSpacing: 0.2,
          ),
        );
        final textPainter = TextPainter(
          text: textSpan,
          textDirection: TextDirection.ltr,
        )..layout();

        final pillCenter = Offset(center.dx, center.dy + 18.0);
        final pillRect = Rect.fromCenter(
          center: pillCenter,
          width: textPainter.width + 12.0,
          height: textPainter.height + 6.0,
        );
        final rrect =
            RRect.fromRectAndRadius(pillRect, const Radius.circular(4.0));

        // Pill background
        final pillBgPaint = Paint()
          ..color = isDark ? const Color(0xFF141412) : palette.bgBase
          ..style = PaintingStyle.fill;
        canvas.drawRRect(rrect, pillBgPaint);

        // Pill border
        final pillBorderPaint = Paint()
          ..color = isDark ? const Color(0xFF383832) : palette.div
          ..strokeWidth = 1.0
          ..style = PaintingStyle.stroke;
        canvas.drawRRect(rrect, pillBorderPaint);

        // Center text inside the pill
        textPainter.paint(
          canvas,
          Offset(pillCenter.dx - textPainter.width / 2,
              pillCenter.dy - textPainter.height / 2),
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant _OntologyGraphPainter oldDelegate) {
    return oldDelegate.hoveredNodeId != hoveredNodeId ||
        oldDelegate.palette != palette ||
        oldDelegate.scale != scale ||
        oldDelegate.offsetX != offsetX ||
        oldDelegate.offsetY != offsetY ||
        oldDelegate.nodes != nodes ||
        oldDelegate.edges != edges;
  }
}
