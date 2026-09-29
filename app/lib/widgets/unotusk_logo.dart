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
            color: const Color(0xFFDA7756),
            borderRadius: BorderRadius.circular(size * 0.28),
          ),
          child: Center(
            child: Text(
              'U',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: size * 0.55,
                fontFamily: 'serif',
              ),
            ),
          ),
        );
      },
    );
  }
}
