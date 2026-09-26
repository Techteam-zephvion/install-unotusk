import 'dart:convert';
import 'dart:io';
import '../domain/server_instance.dart';
import '../../validation/data/environment_validator.dart';

class ServerRegistry {
  final ProcessExecutor _processExecutor;

  ServerRegistry({ProcessExecutor? processExecutor})
      : _processExecutor = processExecutor ?? Process.run;

  String get _registryBaseDir {
    final home = Platform.environment['HOME'] ?? Directory.systemTemp.path;
    return '$home/.unotusk/servers';
  }

  String get _legacyDir {
    final home = Platform.environment['HOME'] ?? Directory.systemTemp.path;
    return '$home/.unotusk/server';
  }

  Future<void> initializeRegistry() async {
    final dir = Directory(_registryBaseDir);
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    await _migrateLegacy();
  }

  Future<void> _migrateLegacy() async {
    final legacy = Directory(_legacyDir);
    if (!legacy.existsSync()) return;
    
    // Check if it's already migrated
    final metadataFile = File('${legacy.path}/metadata.json');
    if (!metadataFile.existsSync()) {
      // Create metadata for the legacy server to mark it as part of the registry
      // We will keep it in the same directory but treat it as a managed server.
      final instance = ServerInstance(
        id: 'legacy-server',
        name: 'Legacy Server',
        composeProject: 'server',
        deploymentDir: legacy.path,
        apiPort: 8000, // Legacy default
        createdAt: DateTime.now(),
      );
      _saveMetadata(legacy.path, instance);
      
      // We can also create a symlink in the registry to point to it, 
      // or just move it. Moving is safer if we enforce docker-compose -p, 
      // since docker volumes for 'server' project are independent of the folder path.
      // But just to be 100% safe, we will just move the folder.
      final newDir = '$_registryBaseDir/legacy-server';
      if (!Directory(newDir).existsSync()) {
        legacy.renameSync(newDir);
        final migratedInstance = instance.copyWith(deploymentDir: newDir);
        _saveMetadata(newDir, migratedInstance);
      }
    }
  }

  void _saveMetadata(String dirPath, ServerInstance instance) {
    final file = File('$dirPath/metadata.json');
    file.writeAsStringSync(jsonEncode(instance.toJson()));
  }

  Future<List<ServerInstance>> listServers() async {
    await initializeRegistry();
    final List<ServerInstance> servers = [];
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
    return servers;
  }

  Future<void> saveServer(ServerInstance instance) async {
    final dir = Directory(instance.deploymentDir);
    if (!dir.existsSync()) {
      dir.createSync(recursive: true);
    }
    _saveMetadata(instance.deploymentDir, instance);
  }

  Future<void> deleteServer(ServerInstance instance, {required bool deleteVolumes}) async {
    // 1. Stop and remove containers
    final args = ['compose', '-p', instance.composeProject, 'down'];
    if (deleteVolumes) {
      args.add('-v');
    }
    
    await _processExecutor(
      'docker',
      args,
      workingDirectory: instance.deploymentDir,
    );

    // 2. Delete deployment directory
    final dir = Directory(instance.deploymentDir);
    if (dir.existsSync()) {
      dir.deleteSync(recursive: true);
    }
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
