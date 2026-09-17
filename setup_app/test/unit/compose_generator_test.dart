import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/config/domain/server_config.dart';
import 'package:setup_app/features/deploy/data/compose_generator.dart';

void main() {
  group('ComposeGenerator Tests', () {
    test('generateDockerCompose isolates postgres and redis internally and exposes only api port', () {
      final config = ServerConfig(
        serverName: 'Demo Unotusk',
        serverPort: 8085,
        llmProvider: LlmProviderType.groq,
        llmApiKey: 'gsk_mock_123',
      );

      final compose = ComposeGenerator.generateDockerCompose(config);
      expect(compose, contains('container_name: unotusk-postgres'));
      expect(compose, contains('container_name: unotusk-redis'));
      expect(compose, contains('container_name: unotusk-api'));
      expect(compose, contains('container_name: unotusk-worker'));
      expect(compose, contains('"8085:8000"'));
      expect(compose, contains('GROQ_API_KEY=gsk_mock_123'));
      // Verify postgres and redis do NOT expose host ports
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
      expect(compose, isNot(contains(':5432"')));
      expect(compose, isNot(contains(':6379"')));
    });
  });
}
