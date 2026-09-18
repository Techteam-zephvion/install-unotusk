import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/server_config.dart';

class ConfigState {
  final ServerConfig config;
  final String? emailError;
  final String? passwordError;
  final String? apiKeyError;
  final String? portError;

  const ConfigState({
    required this.config,
    this.emailError,
    this.passwordError,
    this.apiKeyError,
    this.portError,
  });

  bool get isValid =>
      emailError == null &&
      passwordError == null &&
      apiKeyError == null &&
      portError == null &&
      config.adminEmail.isNotEmpty &&
      config.adminPassword.isNotEmpty &&
      config.llmApiKey.isNotEmpty;

  ConfigState copyWith({
    ServerConfig? config,
    Object? emailError = _sentinel,
    Object? passwordError = _sentinel,
    Object? apiKeyError = _sentinel,
    Object? portError = _sentinel,
  }) {
    return ConfigState(
      config: config ?? this.config,
      emailError: identical(emailError, _sentinel)
          ? this.emailError
          : emailError as String?,
      passwordError: identical(passwordError, _sentinel)
          ? this.passwordError
          : passwordError as String?,
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

  void updateAdminEmail(String email) {
    final trimmed = email.trim();
    if (trimmed.isEmpty || !trimmed.contains('@') || !trimmed.contains('.')) {
      state = state.copyWith(
        config: state.config.copyWith(adminEmail: trimmed),
        emailError: 'Please enter a valid admin email address.',
      );
    } else {
      state = state.copyWith(
        config: state.config.copyWith(adminEmail: trimmed),
        emailError: null,
      );
    }
  }

  void updateAdminPassword(String password) {
    if (password.length < 8) {
      state = state.copyWith(
        config: state.config.copyWith(adminPassword: password),
        passwordError: 'Password must be at least 8 characters.',
      );
    } else {
      state = state.copyWith(
        config: state.config.copyWith(adminPassword: password),
        passwordError: null,
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
    updateAdminEmail(state.config.adminEmail);
    updateAdminPassword(state.config.adminPassword);
    updateLlmApiKey(state.config.llmApiKey);
    return state.isValid;
  }
}

final configControllerProvider =
    StateNotifierProvider<ConfigController, ConfigState>((ref) {
  return ConfigController();
});
