import 'package:flutter/material.dart';

class UnotuskLogo extends StatelessWidget {
  final double size;
  final bool onDark;

  const UnotuskLogo({
    super.key,
    this.size = 28,
    this.onDark = false,
  });

  @override
  Widget build(BuildContext context) {
    final assetPath = onDark ? 'assets/logo_light.png' : 'assets/logo_dark.png';
    final fallbackAssetPath =
        onDark ? 'assets/images/unotusk_logo_light.png' : 'assets/images/unotusk_logo_dark.png';

    return Image.asset(
      assetPath,
      width: size,
      height: size,
      fit: BoxFit.contain,
      errorBuilder: (context, error, stackTrace) {
        return Image.asset(
          fallbackAssetPath,
          width: size,
          height: size,
          fit: BoxFit.contain,
          errorBuilder: (context, error, stackTrace) {
            return CustomPaint(
              size: Size(size, size),
              painter: _UnotuskElephantPainter(
                color: onDark ? const Color(0xFFEDEDEB) : const Color(0xFF1C1917),
              ),
            );
          },
        );
      },
    );
  }
}

/// Fallback vector painter rendering the official Unotusk elephant emblem.
/// This guarantees the official brand emblem is rendered even if image assets
/// have not yet been bundled into the active build runner.
class _UnotuskElephantPainter extends CustomPainter {
  final Color color;

  _UnotuskElephantPainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill
      ..isAntiAlias = true;

    // ViewBox of SVG path in original design: [10, 60] to [40, 100] (width ~30, height ~40)
    canvas.save();
    final scale = size.width / 32.0;
    canvas.scale(scale, scale);
    canvas.translate(-9.0, -62.0);

    final path = Path();
    path.moveTo(37.95, 95.43);
    path.cubicTo(37.13, 94.93, 36.59, 94.08, 36.59, 93.11);
    path.cubicTo(36.59, 92.91, 36.61, 92.71, 36.66, 92.52);
    path.cubicTo(36.81, 91.89, 36.43, 91.26, 35.80, 91.12);
    path.cubicTo(31.85, 90.18, 28.93, 86.81, 28.93, 82.79);
    path.cubicTo(28.93, 81.26, 29.36, 79.82, 30.10, 78.57);
    path.cubicTo(30.84, 77.32, 31.91, 76.27, 33.19, 75.51);
    path.cubicTo(36.15, 74.41, 38.24, 71.73, 38.24, 68.60);
    path.cubicTo(38.24, 64.49, 34.64, 61.16, 30.20, 61.16);
    path.cubicTo(28.13, 61.16, 26.25, 61.88, 24.82, 63.07);
    path.cubicTo(20.40, 66.48, 17.59, 71.65, 17.59, 77.45);
    path.cubicTo(17.59, 77.53, 17.59, 77.62, 17.59, 77.70);
    path.cubicTo(16.18, 78.62, 14.49, 79.30, 12.62, 79.69);
    path.cubicTo(11.53, 79.91, 10.38, 80.03, 9.19, 80.03);
    path.cubicTo(8.96, 80.03, 8.73, 80.03, 8.50, 80.02);
    path.cubicTo(8.42, 80.02, 8.34, 80.04, 8.28, 80.08);
    path.cubicTo(8.22, 80.12, 8.16, 80.18, 8.13, 80.25);
    path.cubicTo(8.15, 80.34, 8.18, 80.42, 8.23, 80.50);
    path.cubicTo(8.86, 81.79, 11.64, 82.76, 14.98, 82.76);
    path.cubicTo(15.73, 82.76, 16.45, 82.71, 17.12, 82.62);
    path.cubicTo(17.54, 82.56, 17.95, 82.49, 18.33, 82.40);
    path.cubicTo(18.92, 82.26, 19.48, 82.04, 20.02, 81.76);
    path.cubicTo(20.62, 81.45, 21.23, 81.15, 21.85, 80.88);
    path.lineTo(24.24, 79.84);
    path.cubicTo(25.01, 79.50, 25.50, 78.79, 25.59, 78.01);
    path.cubicTo(25.71, 78.93, 25.18, 79.86, 24.24, 80.24);
    path.lineTo(21.85, 81.22);
    path.cubicTo(21.23, 81.47, 20.62, 81.75, 20.02, 82.04);
    path.cubicTo(19.48, 82.30, 18.92, 82.50, 18.33, 82.64);
    path.cubicTo(20.71, 90.37, 28.26, 96.01, 37.21, 96.01);
    path.cubicTo(37.52, 96.01, 37.83, 96.01, 38.14, 95.99);
    path.cubicTo(38.17, 95.99, 38.20, 95.96, 38.20, 95.92);
    path.cubicTo(38.20, 95.71, 38.09, 95.53, 37.92, 95.45);
    path.close();

    // Eye dot
    path.moveTo(25.24, 70.93);
    path.cubicTo(24.81, 71.20, 24.41, 71.23, 24.48, 70.56);
    path.cubicTo(24.54, 70.01, 25.15, 69.51, 25.57, 69.22);
    path.cubicTo(26.17, 68.80, 26.93, 68.58, 27.64, 68.75);
    path.cubicTo(28.35, 68.93, 28.96, 69.55, 29.00, 70.29);
    path.cubicTo(27.65, 69.82, 26.40, 70.19, 25.24, 70.93);
    path.close();

    canvas.drawPath(path, paint);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _UnotuskElephantPainter oldDelegate) =>
      oldDelegate.color != color;
}
