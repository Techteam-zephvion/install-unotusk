import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:io';
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
      final servers = await registry.listServers();
      final updatedServers = await Future.wait(servers.map(_updateServerStatus));
      state = state.copyWith(isLoading: false, servers: updatedServers);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<ServerInstance> _updateServerStatus(ServerInstance server) async {
    try {
      final res = await _processExecutor(
        'docker',
        ['compose', '-p', server.composeProject, 'ps', '--all', '--format', 'json'],
        workingDirectory: server.deploymentDir,
      );
      
      if (res.exitCode == 0) {
        final out = res.stdout.toString().trim();
        if (out.isEmpty) {
          return server.copyWith(lastKnownState: ServerState.stopped);
        }
        
        // docker compose ps --format json sometimes returns multiple JSON objects (one per line)
        // or a single array depending on docker version.
        bool hasRunning = false;
        bool hasExited = false;
        
        final lines = out.split('\n');
        for (var line in lines) {
          if (line.isNotEmpty) {
            if (line.contains('"State":"running"') || line.contains('"State": "running"')) {
              hasRunning = true;
            } else {
              hasExited = true;
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
    } catch (_) {}
    return server.copyWith(lastKnownState: ServerState.unknown);
  }

  Future<void> startServer(ServerInstance server) async {
    await _updateLocalState(server.copyWith(lastKnownState: ServerState.starting));
    final res = await _processExecutor(
      'docker',
      ['compose', '-p', server.composeProject, 'up', '-d'],
      workingDirectory: server.deploymentDir,
    );
    if (res.exitCode == 0) {
      await _updateLocalState(server.copyWith(lastKnownState: ServerState.running));
    } else {
      await _updateLocalState(server.copyWith(lastKnownState: ServerState.failed));
    }
    // Perform background status refresh
    final updated = await _updateServerStatus(server);
    await _updateLocalState(updated);
  }

  Future<void> stopServer(ServerInstance server) async {
    final res = await _processExecutor(
      'docker',
      ['compose', '-p', server.composeProject, 'stop'],
      workingDirectory: server.deploymentDir,
    );
    if (res.exitCode == 0) {
      await _updateLocalState(server.copyWith(lastKnownState: ServerState.stopped));
    } else {
      final updated = await _updateServerStatus(server);
      await _updateLocalState(updated);
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
  }
  
  Future<void> _updateLocalState(ServerInstance updated) async {
    await registry.saveServer(updated);
    final updatedList = state.servers.map((s) => s.id == updated.id ? updated : s).toList();
    state = state.copyWith(servers: updatedList);
  }
}

final serverManagerProvider = StateNotifierProvider<ServerManagerController, ServerManagerState>((ref) {
  return ServerManagerController(ref.watch(serverRegistryProvider));
});
