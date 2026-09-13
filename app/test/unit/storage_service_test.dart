import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app/core/storage/storage_service.dart';

void main() {
  late StorageService storageService;

  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'unotusk_server_url': 'http://localhost:8000',
      'unotusk_auth_token': 'mock-token-123',
      'unotusk_user_data': '{"id":"user-1","email":"dev@company.com","full_name":"Developer","role":"member"}',
    });
    final prefs = await SharedPreferences.getInstance();
    storageService = StorageService(prefs);
  });

  test('reads and updates server URL correctly', () async {
    expect(storageService.getServerUrl(), 'http://localhost:8000');
    await storageService.setServerUrl('https://custom.unotusk.local');
    expect(storageService.getServerUrl(), 'https://custom.unotusk.local');
  });

  test('reads and manages auth tokens', () async {
    expect(storageService.getAuthToken(), 'mock-token-123');
    await storageService.setAuthToken('new-token-456');
    expect(storageService.getAuthToken(), 'new-token-456');
    await storageService.removeAuthToken();
    expect(storageService.getAuthToken(), isNull);
  });

  test('clears session completely on logout', () async {
    await storageService.clearSession();
    expect(storageService.getAuthToken(), isNull);
    expect(storageService.getUserData(), isNull);
    // Server URL remains persisted
    expect(storageService.getServerUrl(), isNotEmpty);
  });
}
