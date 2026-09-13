import 'package:dio/dio.dart';

class HealthStatus {
  final bool isHealthy;
  final bool isReady;
  final String? databaseStatus;
  final String? redisStatus;
  final String? version;
  final String? errorMessage;

  const HealthStatus({
    required this.isHealthy,
    required this.isReady,
    this.databaseStatus,
    this.redisStatus,
    this.version,
    this.errorMessage,
  });
}

class HealthVerifier {
  final Dio _dio;

  HealthVerifier({Dio? dio})
      : _dio = dio ??
            Dio(
              BaseOptions(
                connectTimeout: const Duration(seconds: 3),
                receiveTimeout: const Duration(seconds: 3),
              ),
            );

  Future<HealthStatus> checkHealth(String serverUrl) async {
    try {
      // 1. Basic Health Endpoint
      final healthRes = await _dio.get('$serverUrl/health');
      if (healthRes.statusCode != 200) {
        return HealthStatus(
          isHealthy: false,
          isReady: false,
          errorMessage: 'Server returned HTTP ${healthRes.statusCode}',
        );
      }

      final version = healthRes.data['version'] as String? ?? '0.1.0';

      // 2. Ready Endpoint (DB + Redis check)
      final readyRes = await _dio.get('$serverUrl/health/ready');
      if (readyRes.statusCode == 200) {
        final data = readyRes.data as Map<String, dynamic>;
        final isReady = data['status'] == 'ready';
        return HealthStatus(
          isHealthy: true,
          isReady: isReady,
          databaseStatus: data['database'] as String?,
          redisStatus: data['redis'] as String?,
          version: version,
        );
      }

      return HealthStatus(
        isHealthy: true,
        isReady: false,
        version: version,
        errorMessage: 'Services starting up...',
      );
    } on DioException catch (e) {
      return HealthStatus(
        isHealthy: false,
        isReady: false,
        errorMessage: e.message ?? 'Cannot connect to server at $serverUrl',
      );
    } catch (e) {
      return HealthStatus(
        isHealthy: false,
        isReady: false,
        errorMessage: e.toString(),
      );
    }
  }

  Future<HealthStatus> pollUntilReady(
    String serverUrl, {
    int maxAttempts = 20,
    Duration interval = const Duration(seconds: 2),
    void Function(int attempt, HealthStatus status)? onPoll,
  }) async {
    for (int i = 1; i <= maxAttempts; i++) {
      final status = await checkHealth(serverUrl);
      if (onPoll != null) onPoll(i, status);
      if (status.isReady) {
        return status;
      }
      if (i < maxAttempts) {
        await Future.delayed(interval);
      }
    }

    return const HealthStatus(
      isHealthy: false,
      isReady: false,
      errorMessage: 'Server startup timed out after waiting for services to become ready.',
    );
  }
}
