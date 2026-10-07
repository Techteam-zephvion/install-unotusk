import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class ScoreBar extends StatefulWidget {
  final String label;
  final double score;
  final Color color;
  final UnoPalette palette;

  const ScoreBar({
    super.key,
    required this.label,
    required this.score,
    required this.color,
    required this.palette,
  });

  @override
  State<ScoreBar> createState() => _ScoreBarState();
}

class _ScoreBarState extends State<ScoreBar>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 550),
    );
    _animation = Tween<double>(begin: 0, end: widget.score).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    _controller.forward();
  }

  @override
  void didUpdateWidget(covariant ScoreBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.score != widget.score) {
      _animation = Tween<double>(begin: 0, end: widget.score).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOut),
      );
      _controller.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          SizedBox(
            width: 56,
            child: Text(
              widget.label,
              style: UnoTypography.mono(
                color: widget.palette.textSec,
                fontSize: 10,
                letterSpacing: 0.3,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Container(
              height: 3,
              decoration: BoxDecoration(
                color: widget.palette.div,
                borderRadius: BorderRadius.circular(2),
              ),
              child: AnimatedBuilder(
                animation: _animation,
                builder: (context, child) => FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: _animation.value.clamp(0.0, 1.0),
                  child: Container(
                    decoration: BoxDecoration(
                      color: widget.color,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          SizedBox(
            width: 32,
            child: Text(
              widget.score.toStringAsFixed(2),
              textAlign: TextAlign.right,
              style: UnoTypography.mono(
                color: widget.palette.text,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
