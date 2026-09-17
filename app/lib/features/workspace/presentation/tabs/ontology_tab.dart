import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class GraphNode {
  final int id;
  final double x;
  final double y;
  final String label;
  final String type; // Service, Decision, Commit, Ticket, Thread, Person

  const GraphNode({
    required this.id,
    required this.x,
    required this.y,
    required this.label,
    required this.type,
  });
}

class OntologyTab extends StatefulWidget {
  final String projectId;

  const OntologyTab({
    super.key,
    required this.projectId,
  });

  @override
  State<OntologyTab> createState() => _OntologyTabState();
}

class _OntologyTabState extends State<OntologyTab> {
  int? _hoveredNodeId;

  static const List<GraphNode> nodes = [
    GraphNode(id: 0, x: 100, y: 200, label: 'Auth Service', type: 'Service'),
    GraphNode(id: 1, x: 280, y: 100, label: 'OIDC Decision', type: 'Decision'),
    GraphNode(id: 2, x: 280, y: 300, label: 'Postgres Decision', type: 'Decision'),
    GraphNode(id: 3, x: 480, y: 80, label: 'GH #7210', type: 'Commit'),
    GraphNode(id: 4, x: 480, y: 180, label: 'ENG-1042', type: 'Ticket'),
    GraphNode(id: 5, x: 480, y: 300, label: 'ADR #7', type: 'Commit'),
    GraphNode(id: 6, x: 480, y: 380, label: '#arch-decisions', type: 'Thread'),
    GraphNode(id: 7, x: 680, y: 140, label: '@sam', type: 'Person'),
    GraphNode(id: 8, x: 680, y: 300, label: 'Billing Service', type: 'Service'),
  ];

  static const List<List<int>> edges = [
    [0, 1], [0, 2],
    [1, 3], [1, 4],
    [2, 5], [2, 6],
    [3, 7], [5, 7],
    [5, 8], [6, 8], [4, 8],
  ];

  static const Map<String, Color> nodeTypeColors = {
    'Service': Color(0xFF6EC8B8),
    'Decision': Color(0xFFE8A455),
    'Commit': Color(0xFFD4A843),
    'Ticket': Color(0xFFD4909A),
    'Thread': Color(0xFFD4725A),
    'Person': Color(0xFFA89070),
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 960),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Text('ONTOLOGY GRAPH', style: AppTextStyles.sectionLabel),
                const SizedBox(height: 6),
                Text(
                  'Knowledge Graph',
                  style: AppTextStyles.authHeading,
                ),
                const SizedBox(height: 4),
                Text(
                  'Entity relationships indexed across commits, tickets, threads, and decisions.',
                  style: AppTextStyles.caption,
                ),
                const SizedBox(height: 24),

                // Interactive Graph Canvas Container
                Container(
                  height: 480,
                  decoration: BoxDecoration(
                    color: AppColors.bgSurface,
                    border: Border.all(color: AppColors.divider),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Stack(
                      children: [
                        // Custom Painter for Graph Edges & Background Grid
                        CustomPaint(
                          size: const Size(double.infinity, 480),
                          painter: _OntologyGraphPainter(
                            nodes: nodes,
                            edges: edges,
                            hoveredNodeId: _hoveredNodeId,
                          ),
                        ),

                        // Interactive Nodes
                        ...nodes.map((node) {
                          final color = nodeTypeColors[node.type] ?? AppColors.accent;
                          final isHovered = _hoveredNodeId == node.id;

                          return Positioned(
                            left: node.x - 40,
                            top: node.y - 20,
                            child: MouseRegion(
                              onEnter: (_) => setState(() => _hoveredNodeId = node.id),
                              onExit: (_) => setState(() => _hoveredNodeId = null),
                              child: GestureDetector(
                                onTap: () => setState(() => _hoveredNodeId = node.id),
                                child: Container(
                                  width: 80,
                                  alignment: Alignment.center,
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      AnimatedContainer(
                                        duration: const Duration(milliseconds: 150),
                                        width: isHovered ? 20 : 14,
                                        height: isHovered ? 20 : 14,
                                        decoration: BoxDecoration(
                                          shape: BoxShape.circle,
                                          color: isHovered ? color : AppColors.bgElevated,
                                          border: Border.all(
                                            color: color,
                                            width: isHovered ? 2.5 : 1.5,
                                          ),
                                          boxShadow: isHovered
                                              ? [
                                                  BoxShadow(
                                                    color: color.withValues(alpha: 0.4),
                                                    blurRadius: 10,
                                                  ),
                                                ]
                                              : null,
                                        ),
                                      ),
                                      const SizedBox(height: 6),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                        decoration: BoxDecoration(
                                          color: isHovered
                                              ? AppColors.bgElevated
                                              : Colors.transparent,
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(
                                          node.label,
                                          style: AppTextStyles.mono(
                                            fontSize: 10,
                                            fontWeight: isHovered ? FontWeight.w600 : FontWeight.w400,
                                            color: isHovered ? AppColors.textPrimary : AppColors.textSecondary,
                                          ),
                                          textAlign: TextAlign.center,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
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
                const SizedBox(height: 20),

                // Legend Bar
                Wrap(
                  spacing: 18,
                  runSpacing: 10,
                  children: nodeTypeColors.entries.map((entry) {
                    return Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: entry.value,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          entry.key.toUpperCase(),
                          style: AppTextStyles.mono(
                            fontSize: 10,
                            letterSpacing: 0.6,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _OntologyGraphPainter extends CustomPainter {
  final List<GraphNode> nodes;
  final List<List<int>> edges;
  final int? hoveredNodeId;

  _OntologyGraphPainter({
    required this.nodes,
    required this.edges,
    this.hoveredNodeId,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Subtle background grid dots
    final gridPaint = Paint()
      ..color = AppColors.divider.withValues(alpha: 0.35)
      ..strokeWidth = 1;

    for (double x = 20; x < size.width; x += 30) {
      for (double y = 20; y < size.height; y += 30) {
        canvas.drawCircle(Offset(x, y), 0.75, gridPaint);
      }
    }

    // Edges
    for (final edge in edges) {
      final na = nodes[edge[0]];
      final nb = nodes[edge[1]];

      final bool isActive = hoveredNodeId == edge[0] || hoveredNodeId == edge[1];

      final linePaint = Paint()
        ..color = isActive
            ? AppColors.accent.withValues(alpha: 0.85)
            : AppColors.divider.withValues(alpha: 0.4)
        ..strokeWidth = isActive ? 2.0 : 1.0
        ..style = PaintingStyle.stroke;

      canvas.drawLine(
        Offset(na.x, na.y),
        Offset(nb.x, nb.y),
        linePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _OntologyGraphPainter oldDelegate) =>
      oldDelegate.hoveredNodeId != hoveredNodeId;
}
