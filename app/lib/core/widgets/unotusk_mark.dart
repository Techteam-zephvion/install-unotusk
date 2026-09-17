import 'package:flutter/material.dart';

class UnotuskMark extends StatelessWidget {
  final double size;
  final bool isDark;

  const UnotuskMark({
    super.key,
    this.size = 28,
    this.isDark = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: const Color(0xFF21211E),
        borderRadius: BorderRadius.circular(size * 0.24),
        border: Border.all(
          color: const Color(0xFF33332E),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.15),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: CustomPaint(
          size: Size(size * 0.65, size * 0.65),
          painter: _UnotuskMarkPainter(
            accentColor: const Color(0xFFDA7756),
            strokeColor: const Color(0xFFF0EFEA),
          ),
        ),
      ),
    );
  }
}

class _UnotuskMarkPainter extends CustomPainter {
  final Color accentColor;
  final Color strokeColor;

  _UnotuskMarkPainter({
    required this.accentColor,
    required this.strokeColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width;
    final h = size.height;

    // Paint the stylish Unotusk stylized 'U' glyph with tusk angle
    final paint = Paint()
      ..color = accentColor
      ..style = PaintingStyle.fill;

    final path = Path();
    path.moveTo(w * 0.2, h * 0.15);
    path.lineTo(w * 0.4, h * 0.15);
    path.lineTo(w * 0.4, h * 0.55);
    path.quadraticBezierTo(w * 0.4, h * 0.85, w * 0.65, h * 0.85);
    path.quadraticBezierTo(w * 0.9, h * 0.85, w * 0.9, h * 0.55);
    path.lineTo(w * 0.9, h * 0.15);
    path.lineTo(w * 0.72, h * 0.15);
    path.lineTo(w * 0.72, h * 0.52);
    path.quadraticBezierTo(w * 0.72, h * 0.68, w * 0.65, h * 0.68);
    path.quadraticBezierTo(w * 0.58, h * 0.68, w * 0.58, h * 0.52);
    path.lineTo(w * 0.58, h * 0.15);
    path.lineTo(w * 0.2, h * 0.15);
    path.close();

    canvas.drawPath(path, paint);

    // Accent tusk dot
    final dotPaint = Paint()
      ..color = strokeColor
      ..style = PaintingStyle.fill;
    canvas.drawCircle(Offset(w * 0.3, h * 0.28), w * 0.08, dotPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
