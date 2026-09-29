import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../theme/app_theme.dart';

class ThinkingScanner extends StatefulWidget {
  final String phase; // ingesting, scoring, deepScoring
  final UnoPalette palette;

  const ThinkingScanner({
    super.key,
    required this.phase,
    required this.palette,
  });

  @override
  State<ThinkingScanner> createState() => _ThinkingScannerState();
}

class _ThinkingScannerState extends State<ThinkingScanner>
    with TickerProviderStateMixin {
  late AnimationController _scanController;
  late AnimationController _pulseController;
  Timer? _dotTimer;
  int _dotCount = 1;

  @override
  void initState() {
    super.initState();
    _scanController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3000),
    )..repeat();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 850),
    )..repeat(reverse: true);

    _dotTimer = Timer.periodic(const Duration(milliseconds: 420), (timer) {
      if (mounted) {
        setState(() {
          _dotCount = _dotCount >= 5 ? 1 : _dotCount + 1;
        });
      }
    });
  }

  @override
  void dispose() {
    _scanController.dispose();
    _pulseController.dispose();
    _dotTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.palette.bgBase == const Color(0xFF181816);
    final patternColor = isDark
        ? const Color(0xFFF5DDB0)
        : const Color(0xFFC97F2E);
    final tealDotColor = isDark
        ? const Color(0xFF6EC8B8)
        : const Color(0xFF3F9C8C);
    final labelColor = isDark
        ? const Color(0xFFA89070)
        : const Color(0xFF6B5D45);

    final statusText =
        widget.phase == 'deepScoring' ? 'Pondering' : 'Thinking';

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 240,
          height: 240,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // SVG constellation pattern mesh (exact match with web)
              SvgPicture.asset(
                'assets/pattern.svg',
                width: 220,
                height: 220,
                colorFilter: ColorFilter.mode(patternColor, BlendMode.srcIn),
              ),

              // Animated Scanning Beam
              AnimatedBuilder(
                animation: _scanController,
                builder: (context, child) {
                  final progress = _scanController.value;
                  // sweep from top to bottom
                  final topOffset = progress * 240 - 26;
                  return Positioned(
                    top: topOffset,
                    left: 0,
                    right: 0,
                    height: 52,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.transparent,
                            (isDark
                                    ? const Color(0xFFFFF2C8).withValues(alpha: 0.62)
                                    : const Color(0xFF8C3C00).withValues(alpha: 0.14)),
                            Colors.transparent,
                          ],
                        ),
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 18),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) => Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  color: tealDotColor
                      .withValues(alpha: 0.3 + 0.7 * _pulseController.value),
                  shape: BoxShape.circle,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '$statusText${'.' * _dotCount}',
              style: UnoTypography.mono(
                color: labelColor,
                fontSize: 13,
                letterSpacing: 0.8,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
