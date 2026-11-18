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
        return const Color(0xFF9E9E94); // Warm Gray / Tan (Persons)
      default:
        return const Color(0xFF9E9E94);
    }
  }

  /// Computes transform (scale, offsetX, offsetY) from the actual bounding box
  /// of all nodes so every node and label fits cleanly inside the frame with
  /// zero scrolling and zero clipping at any window size.
  ({double scale, double offsetX, double offsetY}) _computeViewportTransform(
      Size size) {
    if (_nodes.isEmpty) {
      return (scale: 1.0, offsetX: 0.0, offsetY: 0.0);
    }

    double minX = _nodes.first.cx;
    double maxX = _nodes.first.cx;
    double minY = _nodes.first.cy;
    double maxY = _nodes.first.cy;

    for (final n in _nodes) {
      if (n.cx < minX) minX = n.cx;
      if (n.cx > maxX) maxX = n.cx;
      if (n.cy < minY) minY = n.cy;
      if (n.cy > maxY) maxY = n.cy;
    }

    final spanX = math.max(maxX - minX, 120.0);
    final spanY = math.max(maxY - minY, 120.0);

    const padX = 64.0;
    const padTop = 34.0;
    const padBottom = 48.0;

    final availW = math.max(size.width - padX * 2, 80.0);
    final availH = math.max(size.height - padTop - padBottom, 80.0);

    final scale = math.min(availW / spanX, availH / spanY);
    final drawnW = spanX * scale;
    final drawnH = spanY * scale;

    final offsetX = padX + (availW - drawnW) / 2 - minX * scale;
    final offsetY = padTop + (availH - drawnH) / 2 - minY * scale;

    return (scale: scale, offsetX: offsetX, offsetY: offsetY);
  }

  int? _hitTestNode(Offset localPos, double scale, double offsetX, double offsetY) {
    int? hitId;
    double bestDistSq = 1200.0;
    for (final node in _nodes) {
      final nx = node.cx * scale + offsetX;
      final ny = node.cy * scale + offsetY;
      final dx = localPos.dx - nx;
      final dy = localPos.dy - ny;
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

    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 20, 28, 22),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Compact Editorial Header Row
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'ARCHITECTURE',
                          style: UnoTypography.mono(
                            color: p.textMuted,
                            fontSize: 10.5,
                            letterSpacing: 1.0,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Architecture',
                          style: UnoTypography.headingSerif(
                            color: p.text,
                            fontSize: 25,
                            fontWeight: FontWeight.w600,
                            height: 1.15,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Entity relationships indexed across commits, tickets, threads, and decisions.',
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
                  if (_nodes.isNotEmpty) ...[
                    const SizedBox(width: 16),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 11, vertical: 6),
                      decoration: BoxDecoration(
                        color: p.bgElevated.withValues(alpha: 0.75),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: p.div),
                      ),
                      child: Text(
                        '${_nodes.length} entities  ·  ${_edges.length} links',
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
              const SizedBox(height: 16),

              // Main Graph Container — Fills remaining viewport height cleanly (no scroll)
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    gradient: p.sectionGradient,
                    border: Border.all(color: p.div),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final size =
                          Size(constraints.maxWidth, constraints.maxHeight);
                      final vp = _computeViewportTransform(size);

                      return MouseRegion(
                        cursor: SystemMouseCursors.click,
                        onHover: (event) {
                          final hit = _hitTestNode(
                            event.localPosition,
                            vp.scale,
                            vp.offsetX,
                            vp.offsetY,
                          );
                          if (hit != null && hit != _hoveredNodeId) {
                            setState(() => _hoveredNodeId = hit);
                          }
                        },
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTapUp: (details) {
                            final tappedId = _hitTestNode(
                              details.localPosition,
                              vp.scale,
                              vp.offsetX,
                              vp.offsetY,
                            );
                            if (tappedId != null) {
                              setState(() {
                                _hoveredNodeId =
                                    _hoveredNodeId == tappedId ? 0 : tappedId;
                              });
                            }
                          },
                          child: CustomPaint(
                            size: size,
                            painter: _OntologyGraphPainter(
                              nodes: _nodes,
                              edges: _edges,
                              hoveredNodeId: _hoveredNodeId,
                              palette: p,
                              scale: vp.scale,
                              offsetX: vp.offsetX,
                              offsetY: vp.offsetY,
                              getNodeColor: _getNodeColor,
                            ),
                          ),
                        ),
                      );
                    },
                  ),
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

    final isDark = palette.isDark;
    final inactiveEdgeColor =
        isDark ? palette.div : palette.div.withValues(alpha: 0.6);
    final activeEdgeColor = palette.accent;

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
        style: TextStyle(
          fontFamily: 'monospace',
          fontSize: 9.5,
          color: palette.textSec,
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
          ..color = palette.accent.withValues(alpha: 0.38)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14);
        canvas.drawCircle(center, 22.0, glowPaint);

        // Solid accent circle
        final fillPaint = Paint()
          ..color = palette.accent
          ..style = PaintingStyle.fill;
        canvas.drawCircle(center, radius, fillPaint);

        // Pill badge background with monospace label
        final textSpan = TextSpan(
          text: activeNode.label,
          style: TextStyle(
            fontFamily: 'monospace',
            fontSize: 10.0,
            fontWeight: FontWeight.w600,
            color: palette.text,
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
          ..color = palette.bgBase
          ..style = PaintingStyle.fill;
        canvas.drawRRect(rrect, pillBgPaint);

        // Pill border
        final pillBorderPaint = Paint()
          ..color = palette.div
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
