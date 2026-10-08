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
  final String? deploymentDir;
  final String? repoUrl;
  final String? groqApiKey;

  LocalServer({
    required this.id,
    required this.name,
    required this.apiPort,
    this.deploymentDir,
    this.repoUrl,
    this.groqApiKey,
  });

  factory LocalServer.fromJson(Map<String, dynamic> json, {String? repoUrl, String? groqApiKey}) {
    return LocalServer(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      apiPort: json['apiPort'] ?? 28000,
      deploymentDir: json['deploymentDir'],
      repoUrl: repoUrl,
      groqApiKey: groqApiKey,
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
              String? repoUrl;
              String? groqApiKey;
              
              final deploymentDir = json['deploymentDir']?.toString();
              if (deploymentDir != null) {
                final envFile = File('$deploymentDir/.env');
                if (envFile.existsSync()) {
                  try {
                    final lines = envFile.readAsLinesSync();
                    for (final line in lines) {
                      if (line.startsWith('TARGET_REPO_URL=')) {
                        repoUrl = line.substring('TARGET_REPO_URL='.length).trim();
                      } else if (line.startsWith('GROQ_API_KEY=')) {
                        groqApiKey = line.substring('GROQ_API_KEY='.length).trim();
                      }
                    }
                  } catch (_) {}
                }
              }
              
              servers.add(LocalServer.fromJson(json, repoUrl: repoUrl, groqApiKey: groqApiKey));
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
