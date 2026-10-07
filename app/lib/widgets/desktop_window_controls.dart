import 'dart:io';
import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';
import '../theme/app_theme.dart';

/// Desktop window control buttons (minimize, maximize/restore, close).
/// Designed to sit directly in top navigation bars flush against the top-right corner.
class DesktopWindowControls extends StatefulWidget {
  final UnoPalette palette;
  final double height;

  const DesktopWindowControls({
    super.key,
    required this.palette,
    this.height = 40.0,
  });

  @override
  State<DesktopWindowControls> createState() => _DesktopWindowControlsState();
}

class _DesktopWindowControlsState extends State<DesktopWindowControls>
    with WindowListener {
  bool _isMaximized = false;

  @override
  void initState() {
    super.initState();
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      windowManager.addListener(this);
      _checkMaximized();
    }
  }

  void _checkMaximized() async {
    try {
      final max = await windowManager.isMaximized();
      if (mounted) setState(() => _isMaximized = max);
    } catch (_) {}
  }

  @override
  void dispose() {
    if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
      windowManager.removeListener(this);
    }
    super.dispose();
  }

  @override
  void onWindowMaximize() {
    if (mounted) setState(() => _isMaximized = true);
  }

  @override
  void onWindowUnmaximize() {
    if (mounted) setState(() => _isMaximized = false);
  }

  @override
  void onWindowRestore() {
    if (mounted) setState(() => _isMaximized = false);
  }

  @override
  Widget build(BuildContext context) {
    if (!Platform.isWindows && !Platform.isLinux && !Platform.isMacOS) {
      return const SizedBox.shrink();
    }

    final p = widget.palette;

    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // Minimize
        _WindowBtn(
          icon: Icons.remove,
          iconSize: 14,
          height: widget.height,
          tooltip: 'Minimize',
          onTap: () => windowManager.minimize(),
          hoverColor: p.textSec.withValues(alpha: 0.12),
          iconColor: p.textSec,
        ),
        // Maximize / Restore
        _WindowBtn(
          icon: _isMaximized ? Icons.filter_none : Icons.crop_square,
          iconSize: _isMaximized ? 11 : 13,
          height: widget.height,
          tooltip: _isMaximized ? 'Restore Down' : 'Maximize',
          onTap: () async {
            if (_isMaximized) {
              await windowManager.unmaximize();
            } else {
              await windowManager.maximize();
            }
          },
          hoverColor: p.textSec.withValues(alpha: 0.12),
          iconColor: p.textSec,
        ),
        // Close
        _WindowBtn(
          icon: Icons.close,
          iconSize: 15,
          height: widget.height,
          tooltip: 'Close',
          onTap: () => windowManager.close(),
          hoverColor: const Color(0xFFE81123),
          iconColor: p.textSec,
          hoverIconColor: Colors.white,
        ),
      ],
    );
  }
}

class _WindowBtn extends StatefulWidget {
  final IconData icon;
  final double iconSize;
  final double height;
  final String tooltip;
  final VoidCallback onTap;
  final Color hoverColor;
  final Color iconColor;
  final Color? hoverIconColor;

  const _WindowBtn({
    required this.icon,
    required this.iconSize,
    required this.height,
    required this.tooltip,
    required this.onTap,
    required this.hoverColor,
    required this.iconColor,
    this.hoverIconColor,
  });

  @override
  State<_WindowBtn> createState() => _WindowBtnState();
}

class _WindowBtnState extends State<_WindowBtn> {
  bool _hovering = false;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: widget.tooltip,
      waitDuration: const Duration(milliseconds: 600),
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovering = true),
        onExit: (_) => setState(() => _hovering = false),
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: widget.onTap,
          child: Container(
            width: 46,
            height: widget.height,
            color: _hovering ? widget.hoverColor : Colors.transparent,
            alignment: Alignment.center,
            child: Icon(
              widget.icon,
              size: widget.iconSize,
              color: _hovering && widget.hoverIconColor != null
                  ? widget.hoverIconColor
                  : widget.iconColor,
            ),
          ),
        ),
      ),
    );
  }
}
