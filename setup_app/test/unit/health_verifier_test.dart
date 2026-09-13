import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/verify/data/health_verifier.dart';

void main() {
  group('HealthVerifier Unit Tests', () {
    test('checkHealth returns isReady true when /health and /health/ready return 200 ready', () async {
      final dio = Dio();
      dio.httpClientAdapter = _MockHttpClientAdapter((options) {
        if (options.path.endsWith('/health')) {
          return ResponseBody.fromString('{"status":"ok","version":"0.1.0"}', 200, headers: {
            Headers.contentTypeHeader: [Headers.jsonContentType],
          });
        }
        if (options.path.endsWith('/health/ready')) {
          return ResponseBody.fromString(
              '{"status":"ready","database":"connected","redis":"connected"}', 200,
              headers: {
                Headers.contentTypeHeader: [Headers.jsonContentType],
              });
        }
        return ResponseBody.fromString('Not found', 404);
      });

      final verifier = HealthVerifier(dio: dio);
      final status = await verifier.checkHealth('http://localhost:8000');

      expect(status.isHealthy, true);
      expect(status.isReady, true);
      expect(status.databaseStatus, 'connected');
      expect(status.redisStatus, 'connected');
      expect(status.version, '0.1.0');
    });

    test('checkHealth reports degraded when database is disconnected', () async {
      final dio = Dio();
      dio.httpClientAdapter = _MockHttpClientAdapter((options) {
        if (options.path.endsWith('/health')) {
          return ResponseBody.fromString('{"status":"ok","version":"0.1.0"}', 200, headers: {
            Headers.contentTypeHeader: [Headers.jsonContentType],
          });
        }
        if (options.path.endsWith('/health/ready')) {
          return ResponseBody.fromString(
              '{"status":"degraded","database":"disconnected","redis":"connected"}', 200,
              headers: {
                Headers.contentTypeHeader: [Headers.jsonContentType],
              });
        }
        return ResponseBody.fromString('Not found', 404);
      });

      final verifier = HealthVerifier(dio: dio);
      final status = await verifier.checkHealth('http://localhost:8000');

      expect(status.isHealthy, true);
      expect(status.isReady, false);
      expect(status.databaseStatus, 'disconnected');
    });
  });
}

class _MockHttpClientAdapter implements HttpClientAdapter {
  final ResponseBody Function(RequestOptions options) handler;

  _MockHttpClientAdapter(this.handler);

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<dynamic>? requestStream, Future<void>? cancelFuture) async {
    return handler(options);
  }

  @override
  void close({bool force = false}) {}
}
