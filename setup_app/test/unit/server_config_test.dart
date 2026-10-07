import 'package:flutter_test/flutter_test.dart';
import 'package:setup_app/features/config/domain/server_config.dart';
import 'package:setup_app/features/config/presentation/config_controller.dart';

void main() {
  group('ServerConfig and ConfigController Tests', () {
    test('ServerConfig generates auto-secrets and valid .env format', () {
      final config = ServerConfig(
        serverName: 'Production Unotusk',
        serverPort: 8080,
        repoUrl: 'https://github.com/org/repo',
        llmProvider: LlmProviderType.groq,
        llmApiKey: 'gsk_mock_api_key_123',
      );

      expect(config.authSecret.length, greaterThanOrEqualTo(32));
      expect(config.postgresPassword.length, greaterThanOrEqualTo(16));
      expect(config.serverUrl, 'http://localhost:8080');

      final env = config.generateEnvFileContent();
      expect(env, contains('APP_NAME="Production Unotusk"'));
      expect(env, contains('PORT=8080'));
      expect(env, contains('TARGET_REPO_URL=https://github.com/org/repo'));
      expect(env, contains('GROQ_API_KEY=gsk_mock_api_key_123'));
      expect(env, contains('AUTH_SECRET=${config.authSecret}'));
      expect(env, contains('DATABASE_URL=postgresql+asyncpg://'));
    });

    test('ConfigController validates repo url and API key', () {
      final controller = ConfigController();
      expect(controller.validateAll(), false);

      controller.updateRepoUrl('');
      expect(controller.state.repoUrlError, isNotNull);

      controller.updateRepoUrl('https://github.com/org/repo');
      expect(controller.state.repoUrlError, isNull);

      controller.updateLlmApiKey('gsk_valid_key');
      expect(controller.state.apiKeyError, isNull);

      expect(controller.validateAll(), true);
    });
  });
}
