import 'package:flutter/material.dart';
import '../theme/app_fonts.dart';

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
    return Image.asset(
      onDark ? 'assets/logo_light.png' : 'assets/logo_dark.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      errorBuilder: (context, error, stackTrace) {
        // High fidelity geometric fallback matching Unotusk emblem
        return Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: onDark ? const Color(0xFFCBC1B4) : const Color(0xFF0A0F20),
            borderRadius: BorderRadius.circular(size * 0.28),
          ),
          child: Center(
            child: Text(
              'U',
              style: AppFonts.youngSerif(
                color: onDark ? const Color(0xFF0A0F20) : Colors.white,
                fontSize: size * 0.55,
              ),
            ),
          ),
        );
      },
    );
  }
}
