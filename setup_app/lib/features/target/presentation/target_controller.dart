import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/target_config.dart';

class TargetState {
  final TargetConfig config;
  final String? validationError;

  const TargetState({
    this.config = const TargetConfig(),
    this.validationError,
  });

  TargetState copyWith({
    TargetConfig? config,
    String? validationError,
    bool clearError = false,
  }) {
    return TargetState(
      config: config ?? this.config,
      validationError: clearError ? null : (validationError ?? this.validationError),
    );
  }
}

class TargetController extends StateNotifier<TargetState> {
  TargetController() : super(const TargetState());

  void setTargetType(TargetType type) {
    state = state.copyWith(
      config: state.config.copyWith(type: type),
      clearError: true,
    );
  }

  void updateRemoteConfig({
    String? host,
    int? port,
    String? username,
    String? privateKeyPath,
    String? password,
  }) {
    state = state.copyWith(
      config: state.config.copyWith(
        host: host,
        port: port,
        username: username,
        privateKeyPath: privateKeyPath,
        password: password,
      ),
      clearError: true,
    );
  }

  bool validate() {
    if (state.config.type == TargetType.local) {
      state = state.copyWith(clearError: true);
      return true;
    }

    // Remote validation
    if (state.config.host.trim().isEmpty || state.config.host == 'localhost') {
      state = state.copyWith(validationError: 'Please enter a valid remote hostname or IP address.');
      return false;
    }

    if (state.config.username.trim().isEmpty) {
      state = state.copyWith(validationError: 'SSH username is required.');
      return false;
    }

    if ((state.config.password == null || state.config.password!.isEmpty) &&
        (state.config.privateKeyPath == null || state.config.privateKeyPath!.isEmpty)) {
      state = state.copyWith(validationError: 'Please provide either an SSH private key path or password.');
      return false;
    }

    state = state.copyWith(clearError: true);
    return true;
  }
}

final targetControllerProvider =
    StateNotifierProvider<TargetController, TargetState>((ref) {
  return TargetController();
});
