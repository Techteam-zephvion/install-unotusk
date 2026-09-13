import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/connection_repository.dart';
import '../domain/connection_state.dart';

final connectionControllerProvider =
    StateNotifierProvider<ConnectionController, ServerConnectionState>((ref) {
  final repository = ref.watch(connectionRepositoryProvider);
  return ConnectionController(repository);
});

class ConnectionController extends StateNotifier<ServerConnectionState> {
  final ConnectionRepository _repository;

  ConnectionController(this._repository)
      : super(ServerConnectionState(serverUrl: _repository.getSavedServerUrl())) {
    checkConnection();
  }

  Future<void> checkConnection([String? testUrl]) async {
    final targetUrl = testUrl ?? state.serverUrl;
    state = state.copyWith(
      serverUrl: targetUrl,
      status: ConnectionStatus.checking,
      errorMessage: null,
    );

    try {
      final data = await _repository.testConnection(targetUrl);
      final version = data['version']?.toString();
      state = state.copyWith(
        status: ConnectionStatus.connected,
        serverVersion: version,
      );
    } catch (e) {
      state = state.copyWith(
        status: ConnectionStatus.error,
        errorMessage: e.toString(),
      );
    }
  }

  Future<bool> saveAndConnect(String newUrl) async {
    final cleanUrl = newUrl.trim();
    state = state.copyWith(
      serverUrl: cleanUrl,
      status: ConnectionStatus.checking,
      errorMessage: null,
    );

    try {
      final data = await _repository.testConnection(cleanUrl);
      await _repository.saveServerUrl(cleanUrl);
      final version = data['version']?.toString();
      state = state.copyWith(
        serverUrl: cleanUrl,
        status: ConnectionStatus.connected,
        serverVersion: version,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        status: ConnectionStatus.error,
        errorMessage: 'Connection failed: ${e.toString()}',
      );
      return false;
    }
  }
}
