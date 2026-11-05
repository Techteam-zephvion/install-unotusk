import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'uno_palette.dart';

final themeModeProvider = StateNotifierProvider<ThemeModeNotifier, ThemeMode>((ref) {
  return ThemeModeNotifier();
});

class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  // Default to Dark Mode to match Image 3 Figma Employee App standard
  ThemeModeNotifier() : super(ThemeMode.dark);

  void toggleTheme() {
    state = state == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
  }

  void setTheme(ThemeMode mode) {
    state = mode;
  }
}

final unoPaletteProvider = Provider<UnoPalette>((ref) {
  final mode = ref.watch(themeModeProvider);
  return mode == ThemeMode.light ? UnoPalette.light : UnoPalette.dark;
});

