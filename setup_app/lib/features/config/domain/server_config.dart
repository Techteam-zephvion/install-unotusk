import '../../../core/constants/app_constants.dart';
import '../../../core/security/secret_generator.dart';

enum LlmProviderType {
  groq,
  claude;

  String get label {
    switch (this) {
      case LlmProviderType.groq:
        return 'Groq (Llama 3.3 70B)';
      case LlmProviderType.claude:
        return 'Anthropic (Claude 3.5 Sonnet)';
    }
  }

  String get defaultModel {
    switch (this) {
      case LlmProviderType.groq:
        return AppConstants.defaultGroqModel;
      case LlmProviderType.claude:
        return AppConstants.defaultClaudeModel;
    }
  }

  String get apiKeyHint {
    switch (this) {
      case LlmProviderType.groq:
        return 'gsk_...';
      case LlmProviderType.claude:
        return 'sk-ant-...';
    }
  }
}

class ServerConfig {
  final String serverName;
  final int serverPort;
  final String adminEmail;
  final String adminPassword;
  final LlmProviderType llmProvider;
  final String llmApiKey;
  final String authSecret;
  final String postgresPassword;
  final String postgresUser;
  final String postgresDb;
  final int postgresPort;
  final int redisPort;

  ServerConfig({
    this.serverName = AppConstants.defaultServerName,
    this.serverPort = AppConstants.defaultPort,
    this.adminEmail = '',
    this.adminPassword = '',
    this.llmProvider = LlmProviderType.groq,
    this.llmApiKey = '',
    String? authSecret,
    String? postgresPassword,
    this.postgresUser = AppConstants.defaultDbUser,
    this.postgresDb = AppConstants.defaultDbName,
    this.postgresPort = AppConstants.defaultPostgresPort,
    this.redisPort = AppConstants.defaultRedisPort,
  })  : authSecret = authSecret ?? SecretGenerator.generateHexSecret(32),
        postgresPassword = postgresPassword ?? SecretGenerator.generateHexSecret(16);

  String get serverUrl => 'http://localhost:$serverPort';

  String generateEnvFileContent() {
    final buffer = StringBuffer();
    buffer.writeln('# Unotusk Server Auto-Generated Environment');
    buffer.writeln('APP_NAME="$serverName"');
    buffer.writeln('APP_ENV=production');
    buffer.writeln('DEBUG=false');
    buffer.writeln('PORT=$serverPort');
    buffer.writeln('API_PORT=$serverPort');
    buffer.writeln('POSTGRES_USER=$postgresUser');
    buffer.writeln('POSTGRES_PASSWORD=$postgresPassword');
    buffer.writeln('POSTGRES_DB=$postgresDb');
    buffer.writeln('POSTGRES_PORT=$postgresPort');
    buffer.writeln('REDIS_PORT=$redisPort');
    buffer.writeln('DATABASE_URL=postgresql+asyncpg://$postgresUser:$postgresPassword@postgres:5432/$postgresDb');
    buffer.writeln('SYNC_DATABASE_URL=postgresql://$postgresUser:$postgresPassword@postgres:5432/$postgresDb');
    buffer.writeln('REDIS_URL=redis://redis:6379/0');
    buffer.writeln('AUTH_SECRET=$authSecret');
    buffer.writeln('LLM_PROVIDER=${llmProvider == LlmProviderType.groq ? "groq" : "claude"}');

    if (llmProvider == LlmProviderType.groq) {
      buffer.writeln('GROQ_API_KEY=$llmApiKey');
      buffer.writeln('GROQ_MODEL=${llmProvider.defaultModel}');
    } else {
      buffer.writeln('ANTHROPIC_API_KEY=$llmApiKey');
      buffer.writeln('ANTHROPIC_MODEL=${llmProvider.defaultModel}');
    }

    return buffer.toString();
  }

  ServerConfig copyWith({
    String? serverName,
    int? serverPort,
    String? adminEmail,
    String? adminPassword,
    LlmProviderType? llmProvider,
    String? llmApiKey,
    String? authSecret,
    String? postgresPassword,
    String? postgresUser,
    String? postgresDb,
    int? postgresPort,
    int? redisPort,
  }) {
    return ServerConfig(
      serverName: serverName ?? this.serverName,
      serverPort: serverPort ?? this.serverPort,
      adminEmail: adminEmail ?? this.adminEmail,
      adminPassword: adminPassword ?? this.adminPassword,
      llmProvider: llmProvider ?? this.llmProvider,
      llmApiKey: llmApiKey ?? this.llmApiKey,
      authSecret: authSecret ?? this.authSecret,
      postgresPassword: postgresPassword ?? this.postgresPassword,
      postgresUser: postgresUser ?? this.postgresUser,
      postgresDb: postgresDb ?? this.postgresDb,
      postgresPort: postgresPort ?? this.postgresPort,
      redisPort: redisPort ?? this.redisPort,
    );
  }
}
