import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/config/domain/server_config.dart';
import 'package:setup_app/features/deploy/data/compose_generator.dart';

void main() {
  group('ComposeGenerator Tests', () {
    test('generateDockerCompose outputs valid compose configuration with custom ports and services', () {
      final config = ServerConfig(
        serverName: 'Demo Unotusk',
        serverPort: 8085,
        llmProvider: LlmProviderType.groq,
        llmApiKey: 'gsk_mock_123',
        postgresPort: 5439,
        redisPort: 6389,
      );

      final compose = ComposeGenerator.generateDockerCompose(config);
      expect(compose, contains('container_name: unotusk-postgres'));
      expect(compose, contains('container_name: unotusk-redis'));
      expect(compose, contains('container_name: unotusk-api'));
      expect(compose, contains('container_name: unotusk-worker'));
      expect(compose, contains('"8085:8000"'));
      expect(compose, contains('"127.0.0.1:5439:5432"'));
      expect(compose, contains('"127.0.0.1:6389:6379"'));
      expect(compose, contains('GROQ_API_KEY=gsk_mock_123'));
    });
  });
}
