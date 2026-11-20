import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/security/cluster_authority.dart';
import '../../../../core/utils/platform_environment.dart';
import '../domain/server_instance.dart';
import 'server_registry.dart';
import '../../validation/data/environment_validator.dart';

final serverRegistryProvider = Provider<ServerRegistry>((ref) {
  return ServerRegistry();
});

class ServerManagerState {
  final bool isLoading;
  final List<ServerInstance> servers;
  final String? error;

  ServerManagerState({
    this.isLoading = true,
    this.servers = const [],
    this.error,
  });

  ServerManagerState copyWith({
    bool? isLoading,
    List<ServerInstance>? servers,
    String? error,
  }) {
    return ServerManagerState(
      isLoading: isLoading ?? this.isLoading,
      servers: servers ?? this.servers,
      error: error,
    );
  }
}

class ServerManagerController extends StateNotifier<ServerManagerState> {
  final ServerRegistry registry;
  final ProcessExecutor _processExecutor;

  ServerManagerController(this.registry, {ProcessExecutor? processExecutor}) 
      : _processExecutor = processExecutor ?? Process.run,
        super(ServerManagerState()) {
    loadServers();
  }

  Future<void> loadServers() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final List<ServerInstance> servers = [];

      // 1. Load local servers from file registry
      try {
        final localServers = await registry.listServers();
        servers.addAll(localServers);
      } catch (_) {}

      // 2. Fetch live data plane projects from Control Plane API
      try {
        final cpServers = await _fetchFromControlPlane();
        final existingSlugs = servers.map((s) => s.composeProject.toLowerCase()).toSet();
        for (final cp in cpServers) {
          if (!existingSlugs.contains(cp.composeProject.toLowerCase())) {
            servers.add(cp);
          }
        }
      } catch (_) {}

      // 3. Inspect container status (if running on desktop host with docker)
      final List<ServerInstance> updatedServers = [];
      for (final s in servers) {
        if (!kIsWeb) {
          final updated = await _updateServerStatus(s);
          updatedServers.add(updated);
          if (updated.lastKnownState != ServerState.unknown) {
            try {
              await registry.saveServer(updated);
            } catch (_) {}
          }
        } else {
          updatedServers.add(s);
        }
      }

      state = state.copyWith(isLoading: false, servers: updatedServers);
      if (!kIsWeb) {
        _syncToControlPlane(updatedServers);
      }
    } catch (e) {
      // Never crash the view: fallback to empty server list
      state = state.copyWith(isLoading: false, servers: state.servers);
    }
  }

  Future<List<ServerInstance>> _fetchFromControlPlane() async {
    try {
      final dio = Dio();
      final federationSecret = ClusterAuthority.getMasterSecret();
      final rawJson = jsonEncode({'servers': []});
      final ts = (DateTime.now().millisecondsSinceEpoch ~/ 1000).toString();
      final msgBytes = utf8.encode('$ts.$rawJson');
      final hmacSha256 = Hmac(sha256, utf8.encode(federationSecret));
      final sig = hmacSha256.convert(msgBytes).toString();

      final resp = await dio.post(
        'http://127.0.0.1:28000/api/v1/projects/sync-servers',
        data: rawJson,
        options: Options(
          headers: {
            'Content-Type': 'application/json',
            'X-Unotusk-Timestamp': ts,
            'X-Unotusk-Cluster-Signature': sig,
          },
          sendTimeout: const Duration(seconds: 3),
          receiveTimeout: const Duration(seconds: 3),
        ),
      );

      if (resp.statusCode == 200 && resp.data is List) {
        final List<ServerInstance> result = [];
        for (final item in resp.data) {
          if (item is Map) {
            final name = item['name']?.toString() ?? 'Project Server';
            final slug = item['slug']?.toString() ?? name.toLowerCase().replaceAll(RegExp(r'\s+'), '-');
            final port = item['port'] is int
                ? item['port'] as int
                : int.tryParse(item['port']?.toString() ?? '') ?? 28150;
            final statusStr = item['status']?.toString().toUpperCase() ?? 'STOPPED';
            final isRunning = statusStr == 'READY' || statusStr == 'RUNNING';

            result.add(ServerInstance(
              id: slug,
              name: name,
              composeProject: slug,
              deploymentDir: '${PlatformEnvironment.homeDir}/.unotusk/servers/$slug',
              apiPort: port,
              lastKnownState: isRunning ? ServerState.running : ServerState.stopped,
              createdAt: DateTime.now(),
            ));
          }
        }
        return result;
      }
    } catch (_) {}
    return [];
  }

  Future<ServerInstance> _updateServerStatus(ServerInstance server) async {
    if (kIsWeb) return server;
    try {
      final dirExists = Directory(server.deploymentDir).existsSync();
      final res = await _processExecutor(
        'docker',
        ['compose', '-p', server.composeProject, 'ps', '--all', '--format', 'json'],
        workingDirectory: dirExists ? server.deploymentDir : null,
      );
      
      if (res.exitCode == 0) {
        final out = res.stdout.toString().trim();
        if (out.isNotEmpty) {
          bool hasRunning = false;
          bool hasExited = false;
          
          final lines = out.split('\n');
          for (var line in lines) {
            final trimmed = line.trim();
            if (trimmed.isEmpty) continue;
            if (!trimmed.startsWith('{')) continue;
            
            try {
              final json = jsonDecode(trimmed);
              if (json is Map) {
                final state = json['State']?.toString().toLowerCase();
                final exitCode = json['ExitCode'];
                final serviceName = json['Service']?.toString() ?? '';
                
                if (state == 'running' || state == 'starting' || state == 'created') {
                  hasRunning = true;
                } else if (serviceName == 'migration' && exitCode == 0) {
                  continue;
                } else if (state == 'exited' || state == 'dead' || state == 'failed') {
                  hasExited = true;
                }
              }
            } catch (_) {
              if (trimmed.contains('"State":"running"') || trimmed.contains('"State": "running"')) {
                hasRunning = true;
              }
            }
          }

          if (hasRunning && !hasExited) {
            return server.copyWith(lastKnownState: ServerState.running);
          } else if (hasRunning && hasExited) {
            return server.copyWith(lastKnownState: ServerState.degraded);
          } else {
            return server.copyWith(lastKnownState: ServerState.stopped);
          }
        }
      }
    } catch (_) {}

    // Health probe fallback: Check if server is actively responding on its loopback port
    if (server.apiPort > 0) {
      try {
        final dio = Dio();
        final resp = await dio.get(
          'http://127.0.0.1:${server.apiPort}/health',
          options: Options(
            sendTimeout: const Duration(milliseconds: 1000),
            receiveTimeout: const Duration(milliseconds: 1000),
          ),
        );
        if (resp.statusCode == 200) {
          return server.copyWith(lastKnownState: ServerState.running);
        }
      } catch (_) {}
    }

    return server;
  }

  Future<void> startServer(ServerInstance server) async {
    await _updateLocalState(server.copyWith(lastKnownState: ServerState.starting));
    try {
      final dirExists = Directory(server.deploymentDir).existsSync();
      final res = await _processExecutor(
        'docker',
        ['compose', '-p', server.composeProject, 'up', '-d'],
        workingDirectory: dirExists ? server.deploymentDir : null,
      );
      if (res.exitCode == 0) {
        await _updateLocalState(server.copyWith(lastKnownState: ServerState.running));
      } else {
        await _updateLocalState(server.copyWith(lastKnownState: ServerState.failed));
      }
      final updated = await _updateServerStatus(server);
      await _updateLocalState(updated);
    } catch (_) {
      await _updateLocalState(server.copyWith(lastKnownState: ServerState.running));
    }
  }

  Future<void> stopServer(ServerInstance server) async {
    try {
      final dirExists = Directory(server.deploymentDir).existsSync();
      final res = await _processExecutor(
        'docker',
        ['compose', '-p', server.composeProject, 'stop'],
        workingDirectory: dirExists ? server.deploymentDir : null,
      );
      if (res.exitCode == 0) {
        await _updateLocalState(server.copyWith(lastKnownState: ServerState.stopped));
      } else {
        final updated = await _updateServerStatus(server);
        await _updateLocalState(updated);
      }
    } catch (_) {
      await _updateLocalState(server.copyWith(lastKnownState: ServerState.stopped));
    }
  }

  Future<void> restartServer(ServerInstance server) async {
    await stopServer(server);
    await startServer(server);
  }

  Future<void> deleteServer(ServerInstance server, {required bool deleteVolumes}) async {
    await registry.deleteServer(server, deleteVolumes: deleteVolumes);
    final updatedList = state.servers.where((s) => s.id != server.id).toList();
    state = state.copyWith(servers: updatedList);
    _syncToControlPlane(updatedList);
  }
  
  Future<void> _updateLocalState(ServerInstance updated) async {
    await registry.saveServer(updated);
    final updatedList = state.servers.map((s) => s.id == updated.id ? updated : s).toList();
    state = state.copyWith(servers: updatedList);
    _syncToControlPlane(updatedList);
  }

  Future<void> _syncToControlPlane(List<ServerInstance> servers) async {
    if (kIsWeb) return;
    try {
      final dio = Dio();
      final federationSecret = ClusterAuthority.getMasterSecret();
      final payloadMap = {
        'servers': servers.map((s) {
          String? repoUrl;
          try {
            final envFile = File('${s.deploymentDir}/.env');
            if (envFile.existsSync()) {
              for (final line in envFile.readAsLinesSync()) {
                if (line.startsWith('TARGET_REPO_URL=')) {
                  repoUrl = line.substring('TARGET_REPO_URL='.length).trim();
                  break;
                }
              }
            }
          } catch (_) {}
          return {
            'name': s.name,
            'slug': s.composeProject,
            'port': s.apiPort,
            'state': s.lastKnownState.name,
            'repo_url': repoUrl,
          };
        }).toList(),
      };
      final rawJson = jsonEncode(payloadMap);
      final ts = (DateTime.now().millisecondsSinceEpoch ~/ 1000).toString();
      final msgBytes = utf8.encode('$ts.$rawJson');
      final hmacSha256 = Hmac(sha256, utf8.encode(federationSecret));
      final sig = hmacSha256.convert(msgBytes).toString();

      await dio.post(
        'http://127.0.0.1:28000/api/v1/projects/sync-servers',
        data: rawJson,
        options: Options(
          headers: {
            'Content-Type': 'application/json',
            'X-Unotusk-Timestamp': ts,
            'X-Unotusk-Cluster-Signature': sig,
          },
          sendTimeout: const Duration(seconds: 3),
          receiveTimeout: const Duration(seconds: 3),
        ),
      );
    } catch (_) {}
  }
}

final serverManagerProvider = StateNotifierProvider<ServerManagerController, ServerManagerState>((ref) {
  return ServerManagerController(ref.watch(serverRegistryProvider));
});
