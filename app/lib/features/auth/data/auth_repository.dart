import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/storage/storage_service.dart';
import '../domain/user.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final storage = ref.watch(storageServiceProvider);
  return AuthRepository(apiClient, storage);
});

class AuthRepository {
  final ApiClient _apiClient;
  final StorageService _storage;

  AuthRepository(this._apiClient, this._storage);

  String? getSavedToken() => _storage.getAuthToken();

  User? getSavedUser() {
    final raw = _storage.getUserData();
    if (raw == null) return null;
    try {
      return User.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return null;
    }
  }

  Future<({String token, User user})> login({
    required String email,
    required String password,
  }) async {
    final response = await _apiClient.post(
      ApiEndpoints.login,
      data: {
        'email': email.trim(),
        'password': password,
      },
    );

    final data = response.data as Map<String, dynamic>;
    final token = data['access_token']?.toString() ?? data['token']?.toString() ?? '';
    if (token.isEmpty) {
      throw Exception('Server did not provide an access token');
    }

    User user;
    if (data['user'] is Map) {
      user = User.fromJson(Map<String, dynamic>.from(data['user']));
    } else {
      // Fallback: fetch current user via /auth/me with the token
      await _storage.setAuthToken(token);
      user = await fetchCurrentUser();
    }

    await _storage.setAuthToken(token);
    await _storage.setUserData(jsonEncode(user.toJson()));

    return (token: token, user: user);
  }

  Future<User> fetchCurrentUser() async {
    final response = await _apiClient.get(ApiEndpoints.me);
    final user = User.fromJson(response.data as Map<String, dynamic>);
    await _storage.setUserData(jsonEncode(user.toJson()));
    return user;
  }

  Future<void> logout() async {
    await _storage.clearSession();
  }
}
