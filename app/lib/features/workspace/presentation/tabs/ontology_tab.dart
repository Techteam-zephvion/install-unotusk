import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';
import '../../domain/project_graph.dart';
import '../workspace_controller.dart';
import '../widgets/constellation_loader.dart';

class PositionedNode {
  final ProjectGraphNode node;
  final double x;
  final double y;

  const PositionedNode({
    required this.node,
    required this.x,
    required this.y,
  });
}

class OntologyTab extends ConsumerStatefulWidget {
  final String projectId;

  const OntologyTab({
    super.key,
    required this.projectId,
  });

  @override
  ConsumerState<OntologyTab> createState() => _OntologyTabState();
}

class _OntologyTabState extends ConsumerState<OntologyTab> {
  String? _hoveredNodeId;
  ProjectGraphNode? _selectedNode;

  static const Map<String, Color> nodeTypeColors = {
    'SERVICE': Color(0xFF6EC8B8),
    'REPOSITORY': Color(0xFF5B8FF9),
    'FILE': Color(0xFFE8A455),
    'CLASS': Color(0xFFD4A843),
    'FUNCTION': Color(0xFFD4909A),
    'METHOD': Color(0xFFD4909A),
    'INTERFACE': Color(0xFFD4A843),
    'EXTERNAL_PACKAGE': Color(0xFFA89070),
    'TYPE': Color(0xFFA89070),
    'MODULE': Color(0xFFE8A455),
  };

  Color _getNodeColor(String type) {
    return nodeTypeColors[type.toUpperCase()] ?? const Color(0xFF6EC8B8);
  }

  int _getTier(String type) {
    switch (type.toUpperCase()) {
      case 'SERVICE':
        return 0;
      case 'REPOSITORY':
        return 1;
      case 'FILE':
      case 'MODULE':
        return 2;
      default:
        return 3;
    }
  }

  Map<String, PositionedNode> _calculateLayout(
    List<ProjectGraphNode> nodes,
    double width,
    double height,
  ) {
    final Map<int, List<ProjectGraphNode>> tiers = {};
    for (final node in nodes) {
      final tier = _getTier(node.type);
      tiers.setdefault(tier, []).add(node);
    }

    final activeTiers = tiers.keys.toList()..sort();
    final Map<String, PositionedNode> positions = {};

    if (activeTiers.isEmpty) return positions;

    final double colSpacing = activeTiers.length > 1
        ? (width - 160) / (activeTiers.length - 1)
        : width / 2;

    for (int tIdx = 0; tIdx < activeTiers.length; tIdx++) {
      final tierKey = activeTiers[tIdx];
      final tierNodes = tiers[tierKey]!;
      final double colX = activeTiers.length > 1
          ? 80 + (tIdx * colSpacing)
          : width / 2;

      final int count = tierNodes.length;
      final double rowSpacing = count > 1 ? (height - 120) / (count - 1) : 0;

      for (int i = 0; i < count; i++) {
        final node = tierNodes[i];
        final double nodeY = count > 1 ? 60 + (i * rowSpacing) : height / 2;
        positions[node.id] = PositionedNode(
          node: node,
          x: colX,
          y: nodeY,
        );
      }
    }

    return positions;
  }

  @override
  Widget build(BuildContext context) {
    final graphAsync = ref.watch(projectGraphProvider(widget.projectId));

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1040),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('ONTOLOGY GRAPH', style: AppTextStyles.sectionLabel),
                        const SizedBox(height: 6),
                        Text(
                          'Knowledge Graph',
                          style: AppTextStyles.authHeading,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Live service & codebase ontology: Service → Repository → File → Symbol.',
                          style: AppTextStyles.caption,
                        ),
                      ],
                    ),
                    IconButton(
                      tooltip: 'Refresh Graph',
                      icon: const Icon(Icons.refresh, size: 18, color: AppColors.textSecondary),
                      onPressed: () => ref.refresh(projectGraphProvider(widget.projectId)),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                // Interactive Graph Canvas Container
                Container(
                  height: 520,
                  decoration: BoxDecoration(
                    color: AppColors.bgSurface,
                    border: Border.all(color: AppColors.divider),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: graphAsync.when(
                      loading: () => const Center(
                        child: ConstellationLoader(
                          phase: 'deepScoring',
                        ),
                      ),
                      error: (err, _) => Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.error_outline, size: 36, color: AppColors.error),
                              const SizedBox(height: 12),
                              Text(
                                'Unable to load ontology graph',
                                style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                err.toString(),
                                style: AppTextStyles.caption,
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 16),
                              OutlinedButton.icon(
                                onPressed: () => ref.refresh(projectGraphProvider(widget.projectId)),
                                icon: const Icon(Icons.refresh, size: 16),
                                label: const Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      ),
                      data: (graph) {
                        if (graph.nodes.isEmpty) {
                          return Center(
                            child: Padding(
                              padding: const EdgeInsets.all(32),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.hub_outlined, size: 48, color: AppColors.textMuted.withValues(alpha: 0.5)),
                                  const SizedBox(height: 16),
                                  Text(
                                    'No Ontology Entities Indexed',
                                    style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    'Define services or ingest a repository to populate the real knowledge graph.',
                                    style: AppTextStyles.caption,
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                              ),
                            ),
                          );
                        }

                        return LayoutBuilder(
                          builder: (context, constraints) {
                            final width = constraints.maxWidth;
                            final height = constraints.maxHeight;
                            final positionedNodes = _calculateLayout(graph.nodes, width, height);

                            return Stack(
                              children: [
                                // Edges Custom Painter
                                CustomPaint(
                                  size: Size(width, height),
                                  painter: _RealGraphPainter(
                                    positionedNodes: positionedNodes,
                                    edges: graph.edges,
                                    hoveredNodeId: _hoveredNodeId,
                                    selectedNodeId: _selectedNode?.id,
                                  ),
                                ),

                                // Interactive Nodes
                                ...positionedNodes.values.map((pNode) {
                                  final node = pNode.node;
                                  final color = _getNodeColor(node.type);
                                  final isHovered = _hoveredNodeId == node.id;
                                  final isSelected = _selectedNode?.id == node.id;
                                  final isService = node.type.toUpperCase() == 'SERVICE';
                                  final isRepo = node.type.toUpperCase() == 'REPOSITORY';

                                  final double size = isService ? 28 : (isRepo ? 22 : 16);
                                  final double activeSize = size + (isHovered || isSelected ? 6 : 0);

                                  return Positioned(
                                    left: pNode.x - 50,
                                    top: pNode.y - (activeSize / 2),
                                    child: MouseRegion(
                                      onEnter: (_) => setState(() => _hoveredNodeId = node.id),
                                      onExit: (_) => setState(() {
                                        if (_hoveredNodeId == node.id) _hoveredNodeId = null;
                                      }),
                                      child: GestureDetector(
                                        onTap: () => setState(() {
                                          _selectedNode = _selectedNode?.id == node.id ? null : node;
                                        }),
                                        child: SizedBox(
                                          width: 100,
                                          child: Column(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              AnimatedContainer(
                                                duration: const Duration(milliseconds: 150),
                                                width: activeSize,
                                                height: activeSize,
                                                decoration: BoxDecoration(
                                                  shape: isService ? BoxShape.rectangle : BoxShape.circle,
                                                  borderRadius: isService ? BorderRadius.circular(8) : null,
                                                  color: (isHovered || isSelected)
                                                      ? color
                                                      : (isService ? color.withValues(alpha: 0.25) : AppColors.bgElevated),
                                                  border: Border.all(
                                                    color: color,
                                                    width: (isHovered || isSelected) ? 2.5 : 1.5,
                                                  ),
                                                  boxShadow: (isHovered || isSelected || isService)
                                                      ? [
                                                          BoxShadow(
                                                            color: color.withValues(alpha: isService ? 0.35 : 0.4),
                                                            blurRadius: isService ? 12 : 8,
                                                          ),
                                                        ]
                                                      : null,
                                                ),
                                                child: isService
                                                    ? Center(
                                                        child: Icon(
                                                          Icons.cloud_outlined,
                                                          size: activeSize * 0.55,
                                                          color: (isHovered || isSelected) ? AppColors.bgSurface : color,
                                                        ),
                                                      )
                                                    : null,
                                              ),
                                              const SizedBox(height: 6),
                                              Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                                                decoration: BoxDecoration(
                                                  color: (isHovered || isSelected)
                                                      ? AppColors.bgElevated
                                                      : Colors.transparent,
                                                  borderRadius: BorderRadius.circular(4),
                                                ),
                                                child: Text(
                                                  node.label,
                                                  style: AppTextStyles.mono(
                                                    fontSize: isService ? 11 : 9.5,
                                                    fontWeight: (isHovered || isSelected || isService)
                                                        ? FontWeight.w600
                                                        : FontWeight.w400,
                                                    color: (isHovered || isSelected)
                                                        ? AppColors.textPrimary
                                                        : (isService ? AppColors.textPrimary : AppColors.textSecondary),
                                                  ),
                                                  textAlign: TextAlign.center,
                                                  maxLines: 2,
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
                            );
                          },
                        );
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 18),

                // Selected Node Inspector Card (if a node is selected)
                if (_selectedNode != null) ...[
                  _buildNodeInspector(_selectedNode!),
                  const SizedBox(height: 18),
                ],

                // Legend Bar
                Wrap(
                  spacing: 18,
                  runSpacing: 10,
                  children: [
                    _legendItem('SERVICE', const Color(0xFF6EC8B8), isService: true),
                    _legendItem('REPOSITORY', const Color(0xFF5B8FF9)),
                    _legendItem('FILE', const Color(0xFFE8A455)),
                    _legendItem('SYMBOL', const Color(0xFFD4A843)),
                    _legendItem('EXT PACKAGE', const Color(0xFFA89070)),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _legendItem(String label, Color color, {bool isService = false}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(
            shape: isService ? BoxShape.rectangle : BoxShape.circle,
            borderRadius: isService ? BorderRadius.circular(2) : null,
            color: color,
          ),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: AppTextStyles.mono(
            fontSize: 10,
            letterSpacing: 0.6,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildNodeInspector(ProjectGraphNode node) {
    final color = _getNodeColor(node.type);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.bgSurface,
        border: Border.all(color: color.withValues(alpha: 0.5)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: color.withValues(alpha: 0.4)),
                ),
                child: Text(
                  node.type.toUpperCase(),
                  style: AppTextStyles.mono(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: color,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  node.label,
                  style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 16, color: AppColors.textMuted),
                onPressed: () => setState(() => _selectedNode = null),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ),
          if (node.metadata.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Divider(color: AppColors.divider, height: 1),
            const SizedBox(height: 10),
            Wrap(
              spacing: 16,
              runSpacing: 8,
              children: node.metadata.entries.map((entry) {
                if (entry.value == null) return const SizedBox.shrink();
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '${entry.key}: ',
                      style: AppTextStyles.caption.copyWith(
                        color: AppColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                    Text(
                      '${entry.value}',
                      style: AppTextStyles.mono(
                        fontSize: 11,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ],
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

extension _TiersMapExt on Map<int, List<ProjectGraphNode>> {
  List<ProjectGraphNode> setdefault(int key, List<ProjectGraphNode> defaultValue) {
    if (!containsKey(key)) {
      this[key] = defaultValue;
    }
    return this[key]!;
  }
}

class _RealGraphPainter extends CustomPainter {
  final Map<String, PositionedNode> positionedNodes;
  final List<ProjectGraphEdge> edges;
  final String? hoveredNodeId;
  final String? selectedNodeId;

  _RealGraphPainter({
    required this.positionedNodes,
    required this.edges,
    this.hoveredNodeId,
    this.selectedNodeId,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Background dot grid
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
      final pSource = positionedNodes[edge.source];
      final pTarget = positionedNodes[edge.target];

      if (pSource == null || pTarget == null) continue;

      final bool isConnectedToHovered =
          hoveredNodeId == edge.source || hoveredNodeId == edge.target;
      final bool isConnectedToSelected =
          selectedNodeId == edge.source || selectedNodeId == edge.target;
      final bool isActive = isConnectedToHovered || isConnectedToSelected;

      Color edgeColor;
      if (isActive) {
        edgeColor = AppColors.accent;
      } else if (edge.type == 'CONTAINS') {
        edgeColor = AppColors.divider.withValues(alpha: 0.55);
      } else if (edge.type == 'DEPENDS_ON') {
        edgeColor = const Color(0xFFE8A455).withValues(alpha: 0.4);
      } else {
        edgeColor = AppColors.divider.withValues(alpha: 0.35);
      }

      final linePaint = Paint()
        ..color = edgeColor
        ..strokeWidth = isActive ? 2.2 : 1.2
        ..style = PaintingStyle.stroke;

      // Draw subtle bezier curved path between columns
      final path = Path();
      path.moveTo(pSource.x, pSource.y);

      final double midX = (pSource.x + pTarget.x) / 2;
      path.cubicTo(
        midX,
        pSource.y,
        midX,
        pTarget.y,
        pTarget.x,
        pTarget.y,
      );

      canvas.drawPath(path, linePaint);

      // Draw directional dot at target
      final dotPaint = Paint()
        ..color = isActive ? AppColors.accent : edgeColor
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(pTarget.x, pTarget.y), isActive ? 3.0 : 2.0, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RealGraphPainter oldDelegate) =>
      oldDelegate.hoveredNodeId != hoveredNodeId ||
      oldDelegate.selectedNodeId != selectedNodeId ||
      oldDelegate.edges.length != edges.length;
}
