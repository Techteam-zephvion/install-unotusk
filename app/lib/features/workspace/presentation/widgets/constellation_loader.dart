import 'package:flutter/material.dart';
import '../../../../app/theme/app_colors.dart';
import '../../../../app/theme/app_text_styles.dart';

class ConstellationLoader extends StatefulWidget {
  final String phase; // 'ingesting', 'scoring', 'deepScoring'
  final bool isDark;

  const ConstellationLoader({
    super.key,
    this.phase = 'scoring',
    this.isDark = true,
  });

  @override
  State<ConstellationLoader> createState() => _ConstellationLoaderState();
}

class _ConstellationLoaderState extends State<ConstellationLoader>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String _getPhaseLabel() {
    switch (widget.phase) {
      case 'ingesting':
        return 'INGESTING ΔDOC';
      case 'deepScoring':
        return 'DEEP ONTOLOGY SCORING';
      case 'scoring':
      default:
        return 'SCORING GRAPH CITATIONS';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 226,
          height: 80,
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              return CustomPaint(
                painter: _ConstellationPainter(
                  progress: _controller.value,
                  phase: widget.phase,
                  isDark: widget.isDark,
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.2, end: 1.0),
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeInOut,
              builder: (context, value, child) {
                return Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.live.withValues(alpha: value),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.live.withValues(alpha: value * 0.5),
                        blurRadius: 6,
                      ),
                    ],
                  ),
                );
              },
            ),
            const SizedBox(width: 8),
            Text(
              _getPhaseLabel(),
              style: AppTextStyles.monoPhaseLabel,
            ),
          ],
        ),
      ],
    );
  }
}

class _ConstellationPainter extends CustomPainter {
  final double progress;
  final String phase;
  final bool isDark;

  static const List<Offset> nodes = [
    Offset(24, 40),
    Offset(70, 20),
    Offset(70, 60),
    Offset(120, 16),
    Offset(120, 40),
    Offset(120, 64),
    Offset(170, 28),
    Offset(170, 52),
    Offset(206, 40),
  ];

  static const List<List<int>> edges = [
    [0, 1], [0, 2],
    [1, 3], [1, 4],
    [2, 4], [2, 5],
    [3, 6], [4, 6], [4, 7], [5, 7],
    [6, 8], [7, 8],
  ];

  static const List<Color> nodeColors = [
    Color(0xFFDA7756), // 0: Terracotta
    Color(0xFF6EC8B8), // 1: Sage
    Color(0xFFE8A455), // 2: Amber
    Color(0xFF52B788), // 3: Green
    Color(0xFFDA7756), // 4: Terracotta
    Color(0xFF68A090), // 5: Teal
    Color(0xFFE8A455), // 6: Amber
    Color(0xFF6EC8B8), // 7: Sage
    Color(0xFF52B788), // 8: Green
  ];

  _ConstellationPainter({
    required this.progress,
    required this.phase,
    required this.isDark,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final activeThreshold = progress * nodes.length;

    // Draw lines
    for (final edge in edges) {
      final a = edge[0];
      final b = edge[1];
      final na = nodes[a];
      final nb = nodes[b];

      final bool isEdgeActive = a <= activeThreshold && b <= activeThreshold;

      final linePaint = Paint()
        ..color = isEdgeActive
            ? AppColors.neutral.withValues(alpha: 0.75)
            : AppColors.divider.withValues(alpha: 0.3)
        ..strokeWidth = isEdgeActive ? 1.5 : 1.0
        ..style = PaintingStyle.stroke;

      canvas.drawLine(na, nb, linePaint);
    }

    // Draw nodes
    for (int i = 0; i < nodes.length; i++) {
      final node = nodes[i];
      final bool isActive = i <= activeThreshold;
      final nodeColor = nodeColors[i];

      final double radius = isActive ? 6.0 : 4.0;
      final fillPaint = Paint()
        ..color = isActive ? nodeColor : AppColors.bgSurface
        ..style = PaintingStyle.fill;

      final strokePaint = Paint()
        ..color = isActive ? nodeColor : AppColors.divider
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke;

      canvas.drawCircle(node, radius, fillPaint);
      canvas.drawCircle(node, radius, strokePaint);

      if (isActive && (i == (activeThreshold.floor() % nodes.length))) {
        // Pulse ring around current leading node
        final pulsePaint = Paint()
          ..color = nodeColor.withValues(alpha: 0.4)
          ..strokeWidth = 1.5
          ..style = PaintingStyle.stroke;
        canvas.drawCircle(node, radius + 4, pulsePaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _ConstellationPainter oldDelegate) => true;
}
