import 'package:flutter/material.dart';
import '../theme/uno_palette.dart';

class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? backgroundColor;
  final Gradient? gradient;
  final Border? border;
  final BorderRadius? borderRadius;
  final List<BoxShadow>? boxShadow;
  final VoidCallback? onTap;

  const AppCard({
    super.key,
    required this.child,
    this.padding,
    this.backgroundColor,
    this.gradient,
    this.border,
    this.borderRadius,
    this.boxShadow,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final palette = UnoPalette.of(context);
    final radius = borderRadius ?? BorderRadius.circular(16);

    final defaultShadow = [
      BoxShadow(
        color: Colors.black.withValues(alpha: palette.isDark ? 0.35 : 0.05),
        blurRadius: palette.isDark ? 28 : 14,
        offset: const Offset(0, 8),
      ),
    ];

    Widget content = Container(
      padding: padding ?? const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: gradient == null ? (backgroundColor ?? palette.bgSurface) : null,
        gradient: gradient,
        borderRadius: radius,
        border: border ?? Border.all(color: palette.div),
        boxShadow: boxShadow ?? defaultShadow,
      ),
      child: child,
    );

    if (onTap != null) {
      return Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: radius,
          hoverColor: palette.accent.withValues(alpha: 0.05),
          child: content,
        ),
      );
    }

    return content;
  }
}
