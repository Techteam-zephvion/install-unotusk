import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class QueryTierBadge extends StatelessWidget {
  final String tier;

  const QueryTierBadge({super.key, required this.tier});

  @override
  Widget build(BuildContext context) {
    Color color;
    switch (tier.toLowerCase()) {
      case 'hot':
        color = UnoPalette.queryHot;
        break;
      case 'warm':
        color = UnoPalette.queryWarm;
        break;
      case 'cold':
      default:
        color = UnoPalette.queryCold;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.transparent,
        border: Border.all(color: color.withValues(alpha: 0.44)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        tier.toUpperCase(),
        style: UnoTypography.mono(
          color: color,
          fontSize: 9,
          letterSpacing: 0.8,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class ConfidenceBadge extends StatelessWidget {
  final String tier;

  const ConfidenceBadge({super.key, required this.tier});

  @override
  Widget build(BuildContext context) {
    Color color;
    String label;
    switch (tier.toLowerCase()) {
      case 'insufficient':
        color = UnoPalette.confInsufficient;
        label = 'INSUFFICIENT';
        break;
      case 'uncertain':
        color = UnoPalette.confUncertain;
        label = 'UNCERTAIN';
        break;
      case 'confirmed':
      default:
        color = UnoPalette.confConfirmed;
        label = 'CONFIRMED';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: UnoTypography.mono(
          color: color,
          fontSize: 9,
          letterSpacing: 0.8,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class TagBadge extends StatelessWidget {
  final String tag;
  final UnoPalette palette;

  const TagBadge({
    super.key,
    required this.tag,
    required this.palette,
  });

  @override
  Widget build(BuildContext context) {
    final isConfirmed = tag.toUpperCase() == 'CONFIRMED';
    final color = isConfirmed ? palette.confirmed : palette.inferred;

    return Container(
      margin: const EdgeInsets.only(left: 6),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        border: Border.all(color: color.withValues(alpha: 0.28)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        tag.toUpperCase(),
        style: UnoTypography.mono(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

class StatusDot extends StatefulWidget {
  final String status;
  final UnoPalette palette;

  const StatusDot({
    super.key,
    required this.status,
    required this.palette,
  });

  @override
  State<StatusDot> createState() => _StatusDotState();
}

class _StatusDotState extends State<StatusDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    );
    _animation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
    if (widget.status == 'ingesting') {
      _controller.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(covariant StatusDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.status == 'ingesting' && !_controller.isAnimating) {
      _controller.repeat(reverse: true);
    } else if (widget.status != 'ingesting' && _controller.isAnimating) {
      _controller.stop();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    Color color;
    switch (widget.status.toLowerCase()) {
      case 'active':
      case 'live':
        color = widget.palette.live;
        break;
      case 'ingesting':
        color = widget.palette.accent;
        break;
      default:
        color = widget.palette.inferred;
        break;
    }

    if (widget.status == 'ingesting') {
      return AnimatedBuilder(
        animation: _animation,
        builder: (context, child) => Opacity(
          opacity: _animation.value,
          child: Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
        ),
      );
    }

    return Container(
      width: 7,
      height: 7,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
    );
  }
}
