import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/core/security/secret_sanitizer.dart';
import 'package:setup_app/features/config/domain/server_config.dart';

void main() {
  group('Security Audit & Secret Sanitization Tests', () {
    test('redacts multiple mixed secrets in combined terminal output', () {
      const rawLog = '''
2026-09-13 14:00:00 [ERROR] Connection failed: postgresql+asyncpg://unotusk:MyUltraSecretPassw0rd!@10.0.0.5:5432/unotusk_db
2026-09-13 14:00:01 [DEBUG] Groq client initialized with key=gsk_9876543210abcdef9876543210
2026-09-13 14:00:02 [DEBUG] Anthropic fallback configured with sk-ant-api03-abcdef9876543210_test-123
2026-09-13 14:00:03 [INFO] Token validation failed: auth_secret="64charhexstring1234567890abcdef1234567890abcdef1234567890abcdef12"
2026-09-13 14:00:04 [INFO] API key header missing: api-key: my_raw_api_key_secret_value
''';

      final sanitized = SecretSanitizer.sanitize(rawLog);

      // Verify no secrets exist in the sanitized text
      expect(sanitized.contains('MyUltraSecretPassw0rd!'), isFalse);
      expect(sanitized.contains('gsk_9876543210abcdef9876543210'), isFalse);
      expect(sanitized.contains('sk-ant-api03-abcdef9876543210_test-123'), isFalse);
      expect(sanitized.contains('64charhexstring1234567890abcdef1234567890abcdef1234567890abcdef12'), isFalse);
      expect(sanitized.contains('my_raw_api_key_secret_value'), isFalse);

      // Verify structure and redaction placeholders
      expect(sanitized, contains('postgresql+asyncpg://unotusk:[REDACTED]@10.0.0.5:5432/unotusk_db'));
      expect(sanitized, contains('key=[REDACTED]'));
      expect(sanitized, contains('auth_secret=[REDACTED]'));
      expect(sanitized, contains('api-key: [REDACTED]'));
    });

    test('generateEnvFileContent generates strong random secrets and masks values safely', () {
      final config = ServerConfig(
        adminEmail: 'admin@company.com',
        adminPassword: 'SuperSecurePassword123!',
        llmApiKey: 'gsk_supersecretapikeyforgroq123456',
      );

      final envContent = config.generateEnvFileContent();

      expect(envContent, contains('GROQ_API_KEY=gsk_supersecretapikeyforgroq123456'));
      expect(envContent, contains('DATABASE_URL='));
      expect(envContent, contains('AUTH_SECRET='));

      // Ensure that sanitizing the env file content properly protects all secrets
      final sanitizedEnv = SecretSanitizer.sanitize(envContent);
      expect(sanitizedEnv.contains('gsk_supersecretapikeyforgroq123456'), isFalse);
      expect(sanitizedEnv.contains(config.authSecret), isFalse);
      expect(sanitizedEnv.contains(config.postgresPassword), isFalse);
    });

    test('generated .env file on disk is written with restrictive 0600 permissions', () async {
      if (Platform.isWindows) return;

      final tempDir = Directory.systemTemp.createTempSync('unotusk_sec_test_');
      final envFile = File('${tempDir.path}/.env');
      envFile.writeAsStringSync('SECRET=123456');

      final chmodRes = await Process.run('chmod', ['600', envFile.path]);
      expect(chmodRes.exitCode, 0);

      final statRes = await Process.run('stat', ['-c', '%a', envFile.path]);
      expect(statRes.stdout.toString().trim(), '600');

      tempDir.deleteSync(recursive: true);
    });
  });
}
