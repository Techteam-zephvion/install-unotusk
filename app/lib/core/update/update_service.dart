import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../app/config/app_config.dart';

/// Information about an available software release.
class AppReleaseInfo {
  final String latestVersion;
  final String currentVersion;
  final String codename;
  final String tag;
  final String releaseDate;
  final String? downloadUrl;
  final String? filename;
  final bool hasUpdate;

  const AppReleaseInfo({
    required this.latestVersion,
    required this.currentVersion,
    required this.codename,
    required this.tag,
    required this.releaseDate,
    this.downloadUrl,
    this.filename,
    required this.hasUpdate,
  });

  factory AppReleaseInfo.fromJson({
    required Map<String, dynamic> json,
    required String currentVersion,
  }) {
    final latestVer = json['version']?.toString() ?? '1.0.0';
    final codename = json['codename']?.toString() ?? 'Stable';
    final tag = json['tag']?.toString() ?? 'v$latestVer';
    final releaseDate = json['releaseDate']?.toString() ?? '';

    String? downloadUrl;
    String? filename;

    final downloads = json['downloads'];
    if (downloads is Map<String, dynamic>) {
      Map<String, dynamic>? platformDownload;
      if (!kIsWeb) {
        if (Platform.isWindows) {
          platformDownload = downloads['employeeWindows'] as Map<String, dynamic>?;
        } else if (Platform.isMacOS) {
          platformDownload = downloads['employeeMacos'] as Map<String, dynamic>?;
        } else if (Platform.isLinux) {
          platformDownload = downloads['employeeLinux'] as Map<String, dynamic>?;
        }
      }

      if (platformDownload != null) {
        downloadUrl = platformDownload['url']?.toString();
        filename = platformDownload['filename']?.toString();
      }
    }

    final hasUpdate = UpdateService.isVersionNewer(latestVer, currentVersion);

    return AppReleaseInfo(
      latestVersion: latestVer,
      currentVersion: currentVersion,
      codename: codename,
      tag: tag,
      releaseDate: releaseDate,
      downloadUrl: downloadUrl ?? 'https://install.unotusk.com',
      filename: filename,
      hasUpdate: hasUpdate,
    );
  }
}

/// Service that checks for desktop application updates against install.unotusk.com.
class UpdateService {
  final http.Client _client;

  static const String primaryManifestUrl = 'https://install.unotusk.com/version.json';
  static const String fallbackManifestUrl =
      'https://raw.githubusercontent.com/Techteam-zephvion/install-unotusk/main/apps/install-site/version.json';

  UpdateService({http.Client? client}) : _client = client ?? http.Client();

  /// Compares two semver strings (e.g. "1.0.2" vs "1.0.1").
  /// Returns true if [remote] is strictly higher than [current].
  static bool isVersionNewer(String remote, String current) {
    try {
      final remoteParts = _parseSemver(remote);
      final currentParts = _parseSemver(current);

      for (int i = 0; i < 3; i++) {
        if (remoteParts[i] > currentParts[i]) return true;
        if (remoteParts[i] < currentParts[i]) return false;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  static List<int> _parseSemver(String ver) {
    // Strip leading 'v' and any trailing hyphen metadata (e.g. "v1.0.2-rudra" -> "1.0.2")
    var clean = ver.trim().toLowerCase();
    if (clean.startsWith('v')) clean = clean.substring(1);
    final dashIdx = clean.indexOf('-');
    if (dashIdx != -1) clean = clean.substring(0, dashIdx);
    final plusIdx = clean.indexOf('+');
    if (plusIdx != -1) clean = clean.substring(0, plusIdx);

    final parts = clean.split('.');
    final major = parts.isNotEmpty ? int.tryParse(parts[0]) ?? 0 : 0;
    final minor = parts.length > 1 ? int.tryParse(parts[1]) ?? 0 : 0;
    final patch = parts.length > 2 ? int.tryParse(parts[2]) ?? 0 : 0;
    return [major, minor, patch];
  }

  /// Checks for available updates.
  Future<AppReleaseInfo?> checkForUpdates({String? currentVersionOverride}) async {
    final currentVer = currentVersionOverride ?? AppConfig.appVersion;

    // Try primary install-site URL, then fallback
    Map<String, dynamic>? manifest;
    for (final url in [primaryManifestUrl, fallbackManifestUrl]) {
      try {
        final response = await _client.get(Uri.parse(url)).timeout(const Duration(seconds: 5));
        if (response.statusCode == 200) {
          manifest = jsonDecode(response.body) as Map<String, dynamic>;
          break;
        }
      } catch (_) {
        // Continue to fallback
      }
    }

    if (manifest == null) return null;

    return AppReleaseInfo.fromJson(
      json: manifest,
      currentVersion: currentVer,
    );
  }

  /// Opens the release download URL in the system browser.
  static Future<bool> launchDownload(String url) async {
    if (kIsWeb) return false;
    try {
      if (Platform.isMacOS) {
        await Process.run('open', [url]);
        return true;
      } else if (Platform.isWindows) {
        await Process.run('cmd', ['/c', 'start', '', url]);
        return true;
      } else if (Platform.isLinux) {
        await Process.run('xdg-open', [url]);
        return true;
      }
    } catch (_) {}
    return false;
  }
}

/// Riverpod provider for UpdateService
final updateServiceProvider = Provider<UpdateService>((ref) {
  return UpdateService();
});

/// Notifier managing current update check state
class UpdateStateNotifier extends StateNotifier<AsyncValue<AppReleaseInfo?>> {
  final UpdateService _service;

  UpdateStateNotifier(this._service) : super(const AsyncValue.data(null)) {
    // Automatically perform a silent background check on startup
    check();
  }

  Future<void> check({bool force = false}) async {
    state = const AsyncValue.loading();
    try {
      final info = await _service.checkForUpdates();
      state = AsyncValue.data(info);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  void dismissUpdate() {
    if (state.value != null) {
      // Create a copy with hasUpdate = false to hide the banner for this session
      final current = state.value!;
      state = AsyncValue.data(AppReleaseInfo(
        latestVersion: current.latestVersion,
        currentVersion: current.currentVersion,
        codename: current.codename,
        tag: current.tag,
        releaseDate: current.releaseDate,
        downloadUrl: current.downloadUrl,
        filename: current.filename,
        hasUpdate: false,
      ));
    }
  }
}

final updateStateProvider = StateNotifierProvider<UpdateStateNotifier, AsyncValue<AppReleaseInfo?>>((ref) {
  final service = ref.watch(updateServiceProvider);
  return UpdateStateNotifier(service);
});

