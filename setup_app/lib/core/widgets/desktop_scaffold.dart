import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:window_manager/window_manager.dart';
import '../theme/theme_provider.dart';
import '../theme/uno_palette.dart';
import '../theme/app_text_styles.dart';
import 'desktop_window_controls.dart';
import 'unotusk_logo.dart';

class DesktopScaffold extends ConsumerWidget {
  final Widget body;
  final String? title;
  final Widget? headerAction;

  const DesktopScaffold({
    super.key,
    required this.body,
    this.title,
    this.headerAction,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final palette = UnoPalette.of(context);
    final themeMode = ref.watch(themeModeProvider);
    final isDark = themeMode == ThemeMode.dark;

    return Scaffold(
      backgroundColor: palette.bgBase,
      body: SafeArea(
        child: Column(
          children: [
            // Top Bar matching Employee App Window Title Bar exactly (Image 5)
            Container(
              height: 36,
              color: palette.bgBase,
              child: Row(
                children: [
                  const SizedBox(width: 14),
                  // Official Unotusk Logo from Employee App
                  UnotuskLogo(size: 16, onDark: palette.isDark),
                  const SizedBox(width: 8),
                  Text(
                    title ?? 'Unotusk Server Manager',
                    style: UnoTypography.brandSerif(
                      palette: palette,
                      fontSize: 13,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                  // Draggable Window Area in the middle
                  const Expanded(
                    child: DragToMoveArea(
                      child: SizedBox(
                        height: double.infinity,
                        width: double.infinity,
                      ),
                    ),
                  ),
                  // Theme Toggle Button (Dark / Light)
                  Tooltip(
                    message: isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode',
                    child: InkWell(
                      onTap: () {
                        ref.read(themeModeProvider.notifier).toggleTheme();
                      },
                      borderRadius: BorderRadius.circular(6),
                      child: Container(
                        padding: const EdgeInsets.all(5),
                        decoration: BoxDecoration(
                          color: palette.bgElevated,
                          border: Border.all(color: palette.div),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Icon(
                          isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                          size: 14,
                          color: palette.textSec,
                        ),
                      ),
                    ),
                  ),
                  if (headerAction != null) ...[
                    const SizedBox(width: 8),
                    headerAction!,
                  ],
                  const SizedBox(width: 6),
                  // Native-style Frameless Window Controls
                  DesktopWindowControls(palette: palette, height: 36),
                ],
              ),
            ),
            // Main Content Area
            Expanded(
              child: Container(
                color: palette.bgBase,
                child: body,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
