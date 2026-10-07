import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/logging/app_logger.dart';
import '../data/connection_repository.dart';
import '../domain/connection_state.dart';

final connectionControllerProvider =
    StateNotifierProvider<ConnectionController, ServerConnectionState>((ref) {
  final repository = ref.watch(connectionRepositoryProvider);
  final logger = ref.watch(appLoggerProvider);
  return ConnectionController(repository, logger: logger);
});

class ConnectionController extends StateNotifier<ServerConnectionState> {
  final ConnectionRepository _repository;
  final AppLogger? _logger;

  ConnectionController(this._repository, {this._logger})
      : super(ServerConnectionState(serverUrl: _repository.getSavedServerUrl())) {
    checkConnection();
  }

  Future<void> checkConnection([String? testUrl]) async {
    final targetUrl = testUrl ?? state.serverUrl;
    _logger?.info(
      AppLogEvent.serverConnectionAttempt,
      metadata: {'url': targetUrl},
    );
    state = state.copyWith(
      serverUrl: targetUrl,
      status: ConnectionStatus.checking,
      errorMessage: null,
    );

    try {
      final data = await _repository.testConnection(targetUrl);
      final version = data['version']?.toString();
      _logger?.info(
        AppLogEvent.serverConnectionSuccess,
        metadata: {'url': targetUrl, 'version': version},
      );
      state = state.copyWith(
        status: ConnectionStatus.connected,
        serverVersion: version,
      );
    } catch (e) {
      _logger?.error(
        AppLogEvent.serverConnectionFailure,
        message: e.toString(),
        metadata: {'url': targetUrl},
      );
      state = state.copyWith(
        status: ConnectionStatus.error,
        errorMessage: e.toString(),
      );
    }
  }

  Future<bool> saveAndConnect(String newUrl) async {
    final cleanUrl = newUrl.trim();
    _logger?.info(
      AppLogEvent.serverUrlConfigured,
      metadata: {'url': cleanUrl},
    );
    _logger?.info(
      AppLogEvent.serverConnectionAttempt,
      metadata: {'url': cleanUrl},
    );
    state = state.copyWith(
      serverUrl: cleanUrl,
      status: ConnectionStatus.checking,
      errorMessage: null,
    );

    try {
      final data = await _repository.testConnection(cleanUrl);
      await _repository.saveServerUrl(cleanUrl);
      final version = data['version']?.toString();
      _logger?.info(
        AppLogEvent.serverConnectionSuccess,
        metadata: {'url': cleanUrl, 'version': version},
      );
      state = state.copyWith(
        serverUrl: cleanUrl,
        status: ConnectionStatus.connected,
        serverVersion: version,
      );
      return true;
    } catch (e) {
      _logger?.error(
        AppLogEvent.serverConnectionFailure,
        message: e.toString(),
        metadata: {'url': cleanUrl},
      );
      state = state.copyWith(
        status: ConnectionStatus.error,
        errorMessage: e.toString(),
      );
      return false;
    }
  }
}
