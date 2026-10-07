import 'package:flutter_test/flutter_test.dart';
import 'package:app/core/logging/app_logger.dart';

void main() {
  group('AppLogger Unit Tests', () {
    late AppLogger logger;
    late List<String> writtenLines;

    setUp(() {
      writtenLines = [];
      logger = AppLogger(
        osName: 'linux',
        maxBuffer: 10,
        logWriter: (line) => writtenLines.add(line),
      );
    });

    test('logs event with correct structured fields and metadata', () {
      logger.info(
        AppLogEvent.serverConnectionSuccess,
        message: 'Connected to server',
        metadata: {'url': 'http://10.0.0.59:8000', 'version': '0.1.0'},
      );

      expect(logger.logs.length, 1);
      final record = logger.logs.first;

      expect(record.event, AppLogEvent.serverConnectionSuccess);
      expect(record.severity, AppLogLevel.info);
      expect(record.appVersion, '0.1.0');
      expect(record.os, 'linux');
      expect(record.message, 'Connected to server');
      expect(record.metadata?['url'], 'http://10.0.0.59:8000');
      expect(record.metadata?['version'], '0.1.0');

      expect(writtenLines.length, 1);
      final json = record.toJson();
      expect(json['event'], 'SERVER_CONNECTION_SUCCESS');
      expect(json['severity'], 'INFO');
      expect(json['version'], '0.1.0');
    });

    test('sanitizes Bearer tokens and raw JWTs from log messages', () {
      const rawJwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwicm9sZSI6ImFkbWluIn0.signature';
      logger.warning(
        AppLogEvent.loginFailure,
        message: 'Failed request with Authorization: Bearer $rawJwt',
      );

      expect(logger.logs.length, 1);
      final record = logger.logs.first;
      expect(record.message, isNot(contains(rawJwt)));
      expect(record.message, contains('[REDACTED'));
    });

    test('sanitizes passwords, secrets, and API keys in message and metadata', () {
      logger.error(
        AppLogEvent.unexpectedError,
        message: 'Error with password="super_secret_password" and token=xyz12345',
        metadata: {
          'password': 'mySecretPassword123',
          'apiKey': 'gsk_abcdef1234567890',
          'nested': {
            'anthropicKey': 'sk-ant-api03-abcdef123456789',
          },
          'safeField': 'hello_world',
        },
      );

      final record = logger.logs.first;
      expect(record.message, isNot(contains('super_secret_password')));
      expect(record.message, isNot(contains('xyz12345')));

      final meta = record.metadata!;
      expect(meta['password'], '[REDACTED]');
      expect(meta['apiKey'], '[REDACTED]');
      final nested = meta['nested'] as Map<String, dynamic>;
      expect(nested['anthropicKey'], '[REDACTED]');
      expect(meta['safeField'], 'hello_world');
    });

    test('sanitizes database connection URLs with credentials', () {
      const dbUrl = 'postgresql+asyncpg://postgres:superSecretPass@postgres:5432/unotusk';
      logger.error(
        AppLogEvent.serverConnectionFailure,
        message: 'DB connection error: $dbUrl',
      );

      final record = logger.logs.first;
      expect(record.message, isNot(contains('superSecretPass')));
      expect(record.message, contains('postgresql+asyncpg://[REDACTED]@postgres:5432/unotusk'));
    });

    test('enforces circular buffer max capacity', () {
      for (int i = 0; i < 15; i++) {
        logger.info(AppLogEvent.applicationStart, message: 'Start $i');
      }

      expect(logger.logs.length, 10);
      expect(logger.logs.first.message, 'Start 5');
      expect(logger.logs.last.message, 'Start 14');
    });
  });
}
