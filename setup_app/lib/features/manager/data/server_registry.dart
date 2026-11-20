import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../../../../core/utils/platform_environment.dart';
import '../domain/server_instance.dart';
import '../../validation/data/environment_validator.dart';

class ServerRegistry {
  final ProcessExecutor _processExecutor;
  final List<ServerInstance> _inMemoryFallback = [];

  ServerRegistry({ProcessExecutor? processExecutor})
      : _processExecutor = processExecutor ?? Process.run;

  String get _registryBaseDir {
    return '${PlatformEnvironment.homeDir}/.unotusk/servers';
  }

  String get _legacyDir {
    return '${PlatformEnvironment.homeDir}/.unotusk/server';
  }

  Future<void> initializeRegistry() async {
    if (kIsWeb) return;
    try {
      final dir = Directory(_registryBaseDir);
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      await _migrateLegacy();
    } catch (_) {}
  }

  Future<void> _migrateLegacy() async {
    if (kIsWeb) return;
    try {
      final legacy = Directory(_legacyDir);
      if (!legacy.existsSync()) return;

      final metadataFile = File('${legacy.path}/metadata.json');
      if (!metadataFile.existsSync()) {
        final instance = ServerInstance(
          id: 'legacy-server',
          name: 'Legacy Server',
          composeProject: 'server',
          deploymentDir: legacy.path,
          apiPort: 28000,
          createdAt: DateTime.now(),
        );
        _saveMetadata(legacy.path, instance);

        final newDir = '$_registryBaseDir/legacy-server';
        if (!Directory(newDir).existsSync()) {
          legacy.renameSync(newDir);
          final migratedInstance = instance.copyWith(deploymentDir: newDir);
          _saveMetadata(newDir, migratedInstance);
        }
      }
    } catch (_) {}
  }

  void _saveMetadata(String dirPath, ServerInstance instance) {
    if (kIsWeb) return;
    try {
      final file = File('$dirPath/metadata.json');
      file.writeAsStringSync(jsonEncode(instance.toJson()));
    } catch (_) {}
  }

  Future<List<ServerInstance>> listServers() async {
    if (kIsWeb) return List.unmodifiable(_inMemoryFallback);

    await initializeRegistry();
    final List<ServerInstance> servers = [];
    try {
      final dir = Directory(_registryBaseDir);
      if (dir.existsSync()) {
        for (final entity in dir.listSync()) {
          if (entity is Directory) {
            final file = File('${entity.path}/metadata.json');
            if (file.existsSync()) {
              try {
                final content = file.readAsStringSync();
                final json = jsonDecode(content) as Map<String, dynamic>;
                servers.add(ServerInstance.fromJson(json));
              } catch (_) {}
            }
          }
        }
      }
    } catch (_) {}

    for (final mem in _inMemoryFallback) {
      if (!servers.any((s) => s.id == mem.id)) {
        servers.add(mem);
      }
    }
    return servers;
  }

  Future<void> saveServer(ServerInstance instance) async {
    _inMemoryFallback.removeWhere((s) => s.id == instance.id);
    _inMemoryFallback.add(instance);

    if (kIsWeb) return;
    try {
      final dir = Directory(instance.deploymentDir);
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      _saveMetadata(instance.deploymentDir, instance);
    } catch (_) {}
  }

  Future<void> deleteServer(ServerInstance instance, {required bool deleteVolumes}) async {
    _inMemoryFallback.removeWhere((s) => s.id == instance.id);
    if (kIsWeb) return;

    try {
      final args = ['compose', '-p', instance.composeProject, 'down'];
      if (deleteVolumes) {
        args.add('-v');
      }

      await _processExecutor(
        'docker',
        args,
        workingDirectory: instance.deploymentDir,
      );

      final dir = Directory(instance.deploymentDir);
      if (dir.existsSync()) {
        dir.deleteSync(recursive: true);
      }
    } catch (_) {}
  }

  Future<String> generateNextServerId() async {
    final servers = await listServers();
    int maxSuffix = 0;
    for (final s in servers) {
      if (s.id.startsWith('server-')) {
        final suffix = int.tryParse(s.id.replaceFirst('server-', ''));
        if (suffix != null && suffix > maxSuffix) {
          maxSuffix = suffix;
        }
      }
    }
    final nextId = maxSuffix + 1;
    return 'server-${nextId.toString().padLeft(2, '0')}';
  }
}
