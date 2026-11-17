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
        color: isDark ? const Color(0xFF161A29) : const Color(0xFFF5F2EB),
        borderRadius: BorderRadius.circular(size * 0.24),
        border: Border.all(
          color: isDark ? const Color(0xFF2E313C) : const Color(0xFFE4DFD6),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.06),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: CustomPaint(
          size: Size(size * 0.65, size * 0.65),
          painter: _UnotuskMarkPainter(
            accentColor: isDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20),
            strokeColor: isDark ? const Color(0xFFFFFFFF) : const Color(0xFF0A0F20),
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
