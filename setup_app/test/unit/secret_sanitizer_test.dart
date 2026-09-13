import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/core/security/secret_sanitizer.dart';

void main() {
  group('SecretSanitizer Unit Tests', () {
    test('sanitize redacts Groq API keys', () {
      const raw = 'Error executing request with api_key=gsk_1234567890abcdef123456 in worker';
      final sanitized = SecretSanitizer.sanitize(raw);
      expect(sanitized.contains('gsk_1234567890abcdef123456'), false);
      expect(sanitized.contains('[REDACTED]'), true);
    });

    test('sanitize redacts Anthropic API keys', () {
      const raw = 'Client failed with key sk-ant-api03-abcdef1234567890-XYZ';
      final sanitized = SecretSanitizer.sanitize(raw);
      expect(sanitized.contains('sk-ant-api03-abcdef1234567890-XYZ'), false);
      expect(sanitized.contains('[REDACTED]'), true);
    });

    test('sanitize redacts PostgreSQL connection passwords', () {
      const raw = 'Failed to connect: postgresql+asyncpg://postgres:SuperSecretP@ssword123@localhost:5432/unotusk';
      final sanitized = SecretSanitizer.sanitize(raw);
      expect(sanitized.contains('SuperSecretP@ssword123'), false);
      expect(sanitized, contains('postgresql+asyncpg://postgres:[REDACTED]@localhost:5432/unotusk'));
    });

    test('sanitize redacts AUTH_SECRET and tokens in key-value format', () {
      const raw = 'AUTH_SECRET="a1b2c3d4e5f678901234567890abcdef"';
      final sanitized = SecretSanitizer.sanitize(raw);
      expect(sanitized.contains('a1b2c3d4e5f678901234567890abcdef'), false);
      expect(sanitized, contains('AUTH_SECRET=[REDACTED]'));
    });
  });
}
