import 'dart:io';
import 'package:flutter/foundation.dart';

/// Safe cross-platform environment accessor that never throws on Web or constrained platforms.
class PlatformEnvironment {
  static String? get(String key) {
    if (kIsWeb) return null;
    try {
      return Platform.environment[key];
    } catch (_) {
      return null;
    }
  }

  static String get homeDir {
    if (kIsWeb) return '/tmp';
    try {
      final env = Platform.environment;
      return env['HOME'] ?? env['USERPROFILE'] ?? Directory.systemTemp.path;
    } catch (_) {
      return '/tmp';
    }
  }

  static bool get isWindows {
    if (kIsWeb) return false;
    try {
      return Platform.isWindows;
    } catch (_) {
      return false;
    }
  }

  static bool get isLinux {
    if (kIsWeb) return false;
    try {
      return Platform.isLinux;
    } catch (_) {
      return false;
    }
  }

  static bool get isMacOS {
    if (kIsWeb) return false;
    try {
      return Platform.isMacOS;
    } catch (_) {
      return false;
    }
  }
}
