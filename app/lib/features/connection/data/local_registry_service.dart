import 'dart:convert';
import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final localRegistryServiceProvider = Provider<LocalRegistryService>((ref) {
  return LocalRegistryService();
});

final localServersProvider = FutureProvider<List<LocalServer>>((ref) {
  final service = ref.watch(localRegistryServiceProvider);
  return service.getRunningServers();
});

class LocalServer {
  final String id;
  final String name;
  final int apiPort;

  LocalServer({
    required this.id,
    required this.name,
    required this.apiPort,
  });

  factory LocalServer.fromJson(Map<String, dynamic> json) {
    return LocalServer(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      apiPort: json['apiPort'] ?? 28000,
    );
  }
}

class LocalRegistryService {
  String get _registryBaseDir {
    final home = Platform.environment['HOME'] ?? Platform.environment['USERPROFILE'] ?? Directory.systemTemp.path;
    return '$home/.unotusk/servers';
  }

  Future<List<LocalServer>> getRunningServers() async {
    final List<LocalServer> servers = [];
    final dir = Directory(_registryBaseDir);
    if (!dir.existsSync()) {
      return servers;
    }

    for (final entity in dir.listSync()) {
      if (entity is Directory) {
        final file = File('${entity.path}/metadata.json');
        if (file.existsSync()) {
          try {
            final content = file.readAsStringSync();
            final json = jsonDecode(content) as Map<String, dynamic>;
            final state = json['lastKnownState']?.toString().toLowerCase();
            
            if (state == 'running') {
              servers.add(LocalServer.fromJson(json));
            }
          } catch (_) {}
        }
      }
    }
    
    // Sort by name
    servers.sort((a, b) => a.name.compareTo(b.name));
    return servers;
  }
}
