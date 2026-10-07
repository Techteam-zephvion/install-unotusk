import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/core/network/api_client.dart';
import 'package:app/core/storage/storage_service.dart';
import 'package:app/features/auth/data/auth_repository.dart';
import 'package:app/features/auth/domain/auth_state.dart';
import 'package:app/features/auth/domain/user.dart';
import 'package:app/features/auth/presentation/auth_controller.dart';

class MockAuthRepository extends AuthRepository {
  MockAuthRepository(super.apiClient, super.storage);

  bool shouldFail = false;

  @override
  Future<({String token, User user})> login({
    required String email,
    required String password,
  }) async {
    if (shouldFail) {
      throw Exception('Invalid credentials');
    }
    const user = User(
      id: 'usr-123',
      email: 'test@example.com',
      fullName: 'Test User',
      role: 'member',
    );
    return (token: 'token-abc', user: user);
  }

  @override
  Future<void> logout() async {}
}

void main() {
  late StorageService storage;
  late ApiClient apiClient;
  late MockAuthRepository mockRepo;
  late AuthController controller;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    storage = StorageService(prefs);
    apiClient = ApiClient(storage);
    mockRepo = MockAuthRepository(apiClient, storage);
    controller = AuthController(mockRepo, apiClient);
  });

  test('initial state is unauthenticated when no token saved', () {
    expect(controller.state.status, AuthStatus.unauthenticated);
    expect(controller.state.isAuthenticated, isFalse);
  });

  test('successful login updates state to authenticated', () async {
    final success = await controller.login(
      email: 'test@example.com',
      password: 'password123',
    );

    expect(success, isTrue);
    expect(controller.state.status, AuthStatus.authenticated);
    expect(controller.state.isAuthenticated, isTrue);
    expect(controller.state.user?.email, 'test@example.com');
  });

  test('failed login updates state to error', () async {
    mockRepo.shouldFail = true;
    final success = await controller.login(
      email: 'wrong@example.com',
      password: 'wrongpassword',
    );

    expect(success, isFalse);
    expect(controller.state.status, AuthStatus.error);
    expect(controller.state.errorMessage, contains('Invalid credentials'));
  });

  test('logout clears session and resets state', () async {
    await controller.login(
      email: 'test@example.com',
      password: 'password123',
    );
    expect(controller.state.isAuthenticated, isTrue);

    await controller.logout();
    expect(controller.state.status, AuthStatus.unauthenticated);
    expect(controller.state.token, isNull);
  });

  test('handleUnauthorized clears session and sets session expired message', () async {
    await controller.login(
      email: 'test@example.com',
      password: 'password123',
    );
    expect(controller.state.isAuthenticated, isTrue);

    controller.handleUnauthorized();
    expect(controller.state.status, AuthStatus.unauthenticated);
    expect(controller.state.isAuthenticated, isFalse);
    expect(controller.state.errorMessage, 'Session expired. Please sign in again.');
  });
}
