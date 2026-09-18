import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/logging/app_logger.dart';
import '../../../core/network/api_client.dart';
import '../data/auth_repository.dart';
import '../domain/auth_state.dart';

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  final repository = ref.watch(authRepositoryProvider);
  final apiClient = ref.watch(apiClientProvider);
  final logger = ref.watch(appLoggerProvider);
  return AuthController(repository, apiClient, logger: logger);
});

class AuthController extends StateNotifier<AuthState> {
  final AuthRepository _repository;
  final ApiClient _apiClient;
  final AppLogger? _logger;

  AuthController(this._repository, this._apiClient, {this._logger})
      : super(const AuthState()) {
    _apiClient.onUnauthorized = handleUnauthorized;
    _restoreSession();
  }

  void _restoreSession() {
    final token = _repository.getSavedToken();
    final user = _repository.getSavedUser();

    if (token != null && token.isNotEmpty && user != null) {
      _logger?.info(
        AppLogEvent.sessionRestored,
        metadata: {'email': user.email, 'role': user.role},
      );
      state = state.copyWith(
        status: AuthStatus.authenticated,
        token: token,
        user: user,
      );
    } else {
      state = state.copyWith(status: AuthStatus.unauthenticated);
    }
  }

  Future<bool> login({
    required String email,
    required String password,
  }) async {
    _logger?.info(
      AppLogEvent.loginAttempt,
      metadata: {'email': email},
    );
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);

    try {
      final result = await _repository.login(email: email, password: password);
      _logger?.info(
        AppLogEvent.loginSuccess,
        metadata: {'email': email, 'role': result.user.role},
      );
      state = state.copyWith(
        status: AuthStatus.authenticated,
        token: result.token,
        user: result.user,
      );
      return true;
    } catch (e) {
      _logger?.error(
        AppLogEvent.loginFailure,
        message: e.toString(),
        metadata: {'email': email},
      );
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  Future<bool> signup({
    required String name,
    required String email,
    required String password,
  }) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);

    try {
      final result = await _repository.signup(
        name: name,
        email: email,
        password: password,
      );
      state = state.copyWith(
        status: AuthStatus.authenticated,
        token: result.token,
        user: result.user,
      );
      return true;
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  void handleUnauthorized() {
    _logger?.warning(AppLogEvent.sessionExpired);
    _repository.logout();
    state = const AuthState(
      status: AuthStatus.unauthenticated,
      errorMessage: 'Session expired. Please sign in again.',
    );
  }
}
