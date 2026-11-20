import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import '../utils/platform_environment.dart';
import 'secret_generator.dart';

/// Manages cluster authority keys and derives cryptographic per-data-plane secrets.
class ClusterAuthority {
  static String? _cachedMasterSecret;

  /// Retrieves or initializes the persistent cluster authority secret from ~/.unotusk/cluster_authority.key
  static String getMasterSecret() {
    if (_cachedMasterSecret != null && _cachedMasterSecret!.isNotEmpty) {
      return _cachedMasterSecret!;
    }

    try {
      final keyFile = File('${PlatformEnvironment.homeDir}/.unotusk/cluster_authority.key');
      if (keyFile.existsSync()) {
        final content = keyFile.readAsStringSync().trim();
        if (content.isNotEmpty) {
          _cachedMasterSecret = content;
          return content;
        }
      }

      // Generate a cryptographically secure 256-bit random master authority key
      final newSecret = SecretGenerator.generateHexSecret(32);
      final dir = Directory('${PlatformEnvironment.homeDir}/.unotusk');
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      keyFile.writeAsStringSync(newSecret);
      _cachedMasterSecret = newSecret;
      return newSecret;
    } catch (_) {
      return 'unotusk-cluster-authority-ephemeral-key';
    }
  }

  /// Cryptographically derives a project-scoped shared secret from the cluster master authority key.
  static String deriveDataPlaneSecret(String serverName) {
    final master = getMasterSecret();
    final slug = serverName.toLowerCase().trim().replaceAll(RegExp(r'[^a-z0-9_-]'), '-');
    final msg = utf8.encode('unotusk-data-plane:$slug');
    final hmac = Hmac(sha256, utf8.encode(master));
    return hmac.convert(msg).toString();
  }
}
