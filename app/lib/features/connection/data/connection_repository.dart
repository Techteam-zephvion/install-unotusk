import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_endpoints.dart';
import '../../../core/storage/storage_service.dart';

final connectionRepositoryProvider = Provider<ConnectionRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final storage = ref.watch(storageServiceProvider);
  return ConnectionRepository(apiClient, storage);
});

class ConnectionRepository {
  final ApiClient _apiClient;
  final StorageService _storage;

  ConnectionRepository(this._apiClient, this._storage);

  String getSavedServerUrl() {
    return _storage.getServerUrl();
  }

  Future<void> saveServerUrl(String url) async {
    await _storage.setServerUrl(url);
    _apiClient.updateBaseUrl(url);
  }

  Future<Map<String, dynamic>> testConnection([String? customUrl]) async {
    final urlToTest = customUrl ?? _storage.getServerUrl();
    final dio = Dio(
      BaseOptions(
        baseUrl: urlToTest,
        connectTimeout: const Duration(seconds: 5),
        receiveTimeout: const Duration(seconds: 5),
      ),
    );

    try {
      final response = await dio.get(ApiEndpoints.health);
      if (response.statusCode == 200 && response.data is Map) {
        return Map<String, dynamic>.from(response.data);
      }
      throw Exception('Invalid server response (${response.statusCode})');
    } catch (e) {
      throw Exception('Cannot reach Unotusk Server at $urlToTest: $e');
    }
  }
}
