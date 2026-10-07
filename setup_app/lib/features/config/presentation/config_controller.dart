import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/server_config.dart';

class ConfigState {
  final ServerConfig config;
  final String? repoUrlError;
  final String? apiKeyError;
  final String? portError;

  const ConfigState({
    required this.config,
    this.repoUrlError,
    this.apiKeyError,
    this.portError,
  });

  bool get isValid =>
      repoUrlError == null &&
      apiKeyError == null &&
      portError == null &&
      config.repoUrl.isNotEmpty &&
      config.llmApiKey.isNotEmpty;

  ConfigState copyWith({
    ServerConfig? config,
    Object? repoUrlError = _sentinel,
    Object? apiKeyError = _sentinel,
    Object? portError = _sentinel,
  }) {
    return ConfigState(
      config: config ?? this.config,
      repoUrlError: identical(repoUrlError, _sentinel)
          ? this.repoUrlError
          : repoUrlError as String?,
      apiKeyError: identical(apiKeyError, _sentinel)
          ? this.apiKeyError
          : apiKeyError as String?,
      portError: identical(portError, _sentinel)
          ? this.portError
          : portError as String?,
    );
  }

  static const Object _sentinel = Object();
}

class ConfigController extends StateNotifier<ConfigState> {
  ConfigController() : super(ConfigState(config: ServerConfig()));

  void updateServerName(String name) {
    state = state.copyWith(
      config: state.config.copyWith(serverName: name),
    );
  }

  void updateServerPort(String portStr) {
    final port = int.tryParse(portStr);
    if (port == null || port <= 1024 || port > 65535) {
      state = state.copyWith(
        portError: 'Enter a valid port between 1025 and 65535.',
      );
    } else {
      state = state.copyWith(
        config: state.config.copyWith(serverPort: port),
        portError: null,
      );
    }
  }

  
  void updateRepoUrl(String url) {
    final trimmed = url.trim();
    if (trimmed.isEmpty) {
      state = state.copyWith(
        config: state.config.copyWith(repoUrl: trimmed),
        repoUrlError: 'Repository URL is required',
      );
    } else {
      state = state.copyWith(
        config: state.config.copyWith(repoUrl: trimmed),
        repoUrlError: null,
      );
    }
  }
void updateLlmProvider(LlmProviderType provider) {
    state = state.copyWith(
      config: state.config.copyWith(llmProvider: provider),
    );
  }

  void updateLlmApiKey(String key) {
    final trimmed = key.trim();
    if (trimmed.isEmpty) {
      state = state.copyWith(
        config: state.config.copyWith(llmApiKey: trimmed),
        apiKeyError: 'API key is required for intelligence features.',
      );
    } else {
      state = state.copyWith(
        config: state.config.copyWith(llmApiKey: trimmed),
        apiKeyError: null,
      );
    }
  }

  void updateLanIp(String ip) {
    state = state.copyWith(
      config: state.config.copyWith(lanIp: ip),
    );
  }

  bool validateAll() {
    updateRepoUrl(state.config.repoUrl);
    updateLlmApiKey(state.config.llmApiKey);
    return state.isValid;
  }
}

final configControllerProvider =
    StateNotifierProvider<ConfigController, ConfigState>((ref) {
  return ConfigController();
});
