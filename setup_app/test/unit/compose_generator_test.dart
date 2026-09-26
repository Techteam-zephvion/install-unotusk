import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/config/domain/server_config.dart';
import 'package:setup_app/features/deploy/data/compose_generator.dart';

void main() {
  group('ComposeGenerator Tests', () {
    test('generateDockerCompose isolates postgres and redis internally and references secrets via env', () {
      final config = ServerConfig(
        serverName: 'Demo Unotusk',
        serverPort: 8085,
        llmProvider: LlmProviderType.groq,
        llmApiKey: 'gsk_mock_123',
      );

      final compose = ComposeGenerator.generateDockerCompose(config);
      // Secrets must NOT be inlined in plaintext in the compose file
      expect(compose, isNot(contains('gsk_mock_123')));
      expect(compose, contains(r'GROQ_API_KEY=${GROQ_API_KEY}'));
      expect(compose, contains(r'AUTH_SECRET=${AUTH_SECRET}'));
      expect(compose, contains(r'POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}'));
      expect(compose, contains(r'DATABASE_URL=${DATABASE_URL}'));

      // Multi-server isolation: no fixed global container names
      expect(compose, isNot(contains('container_name: unotusk-postgres')));
      expect(compose, isNot(contains('container_name: unotusk-api')));

      // Port exposure: only api port is exposed, postgres and redis are internal
      expect(compose, contains('"8085:8000"'));
      expect(compose, isNot(contains(':5432"')));
      expect(compose, isNot(contains(':6379"')));
      expect(compose, contains('networks:\n      - unotusk-network'));
    });

    test('generateProductionCompose isolates postgres and redis internally with prebuilt image tag', () {
      final config = ServerConfig(
        serverName: 'Demo Unotusk',
        serverPort: 8085,
        llmProvider: LlmProviderType.groq,
        llmApiKey: 'gsk_mock_123',
      );

      final compose = ComposeGenerator.generateProductionCompose(config, imageTag: 'unotusk-api:0.1.0');
      expect(compose, contains('image: unotusk-api:0.1.0'));
      expect(compose, contains('"8085:8000"'));
      expect(compose, isNot(contains('gsk_mock_123')));
      expect(compose, contains(r'AUTH_SECRET=${AUTH_SECRET}'));
      expect(compose, isNot(contains(':5432"')));
      expect(compose, isNot(contains(':6379"')));
    });
  });
}
