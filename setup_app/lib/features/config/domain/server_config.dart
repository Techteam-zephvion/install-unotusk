import '../../../core/constants/app_constants.dart';
import '../../../core/security/cluster_authority.dart';
import '../../../core/security/secret_generator.dart';

enum LlmProviderType {
  groq,
  openrouter,
  claude,
  offline;

  String get label {
    switch (this) {
      case LlmProviderType.groq:
        return 'Groq (openai/gpt-oss-120b)';
      case LlmProviderType.openrouter:
        return 'OpenRouter (meta-llama/llama-3.3-70b-instruct:free)';
      case LlmProviderType.claude:
        return 'Anthropic (Claude 3.5 Sonnet)';
      case LlmProviderType.offline:
        return 'Offline Synthesizer (Zero-Network Deterministic)';
    }
  }

  String get defaultModel {
    switch (this) {
      case LlmProviderType.groq:
        return AppConstants.defaultGroqModel;
      case LlmProviderType.openrouter:
        return AppConstants.defaultOpenRouterModel;
      case LlmProviderType.claude:
        return AppConstants.defaultClaudeModel;
      case LlmProviderType.offline:
        return 'offline-synthesizer';
    }
  }

  String get apiKeyHint {
    switch (this) {
      case LlmProviderType.groq:
        return 'gsk_...';
      case LlmProviderType.openrouter:
        return 'sk-or-v1-...';
      case LlmProviderType.claude:
        return 'sk-ant-...';
      case LlmProviderType.offline:
        return 'No key required (Deterministic offline)';
    }
  }
}

class ServerConfig {
  final String serverName;
  final int serverPort;
  final String repoUrl;
  final LlmProviderType llmProvider;
  final String llmApiKey;
  // Multi-key failover configuration
  final bool enableBackupLlm;
  final LlmProviderType backupLlmProvider;
  final String backupLlmApiKey;
  final String authSecret;
  final String postgresPassword;
  final String postgresUser;
  final String postgresDb;
  final int postgresPort;
  final int redisPort;
  final String? lanIp;

  ServerConfig({
    this.serverName = AppConstants.defaultServerName,
    this.serverPort = AppConstants.defaultPort,
    this.repoUrl = '',
    this.llmProvider = LlmProviderType.groq,
    this.llmApiKey = '',
    this.enableBackupLlm = true,
    this.backupLlmProvider = LlmProviderType.openrouter,
    this.backupLlmApiKey = '',
    String? authSecret,
    String? postgresPassword,
    this.postgresUser = AppConstants.defaultDbUser,
    this.postgresDb = AppConstants.defaultDbName,
    this.postgresPort = AppConstants.defaultPostgresPort,
    this.redisPort = AppConstants.defaultRedisPort,
    this.lanIp,
  })  : authSecret = authSecret ?? SecretGenerator.generateHexSecret(32),
        postgresPassword = postgresPassword ?? SecretGenerator.generateHexSecret(16);

  String get serverUrl => (lanIp != null && lanIp!.isNotEmpty && lanIp != '127.0.0.1')
      ? 'http://$lanIp:$serverPort'
      : 'http://localhost:$serverPort';

  String get lanUrl => (lanIp != null && lanIp!.isNotEmpty)
      ? 'http://$lanIp:$serverPort'
      : 'http://localhost:$serverPort';

  String get localUrl => 'http://localhost:$serverPort';

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
    buffer.writeln('NEXT_PUBLIC_API_URL=$serverUrl');
    buffer.writeln('CONTROL_PLANE_URL=http://127.0.0.1:28000');
    final dataPlaneSecret = ClusterAuthority.deriveDataPlaneSecret(serverName);
    buffer.writeln('CLUSTER_FEDERATION_SECRET=$dataPlaneSecret');
    if (repoUrl.isNotEmpty) buffer.writeln('TARGET_REPO_URL=$repoUrl');

    // Primary Provider Setting
    if (llmProvider == LlmProviderType.groq) {
      buffer.writeln('LLM_PROVIDER=groq');
      buffer.writeln('GROQ_API_KEY=$llmApiKey');
      buffer.writeln('GROQ_MODEL=${llmProvider.defaultModel}');
    } else if (llmProvider == LlmProviderType.openrouter) {
      buffer.writeln('LLM_PROVIDER=openrouter');
      buffer.writeln('OPENROUTER_API_KEY=$llmApiKey');
      buffer.writeln('OPENROUTER_MODEL=${llmProvider.defaultModel}');
    } else if (llmProvider == LlmProviderType.claude) {
      buffer.writeln('LLM_PROVIDER=claude');
      buffer.writeln('ANTHROPIC_API_KEY=$llmApiKey');
      buffer.writeln('ANTHROPIC_MODEL=${llmProvider.defaultModel}');
    } else {
      buffer.writeln('LLM_PROVIDER=offline');
    }

    // Backup Provider Settings (Allows seamless failover when primary hits rate limits)
    if (enableBackupLlm && backupLlmApiKey.isNotEmpty) {
      if (backupLlmProvider == LlmProviderType.openrouter) {
        buffer.writeln('BACKUP_LLM_PROVIDER=openrouter');
        buffer.writeln('OPENROUTER_API_KEY=$backupLlmApiKey');
        buffer.writeln('OPENROUTER_MODEL=${backupLlmProvider.defaultModel}');
      } else if (backupLlmProvider == LlmProviderType.groq) {
        buffer.writeln('BACKUP_LLM_PROVIDER=groq');
        buffer.writeln('GROQ_API_KEY=$backupLlmApiKey');
        buffer.writeln('GROQ_MODEL=${backupLlmProvider.defaultModel}');
      } else if (backupLlmProvider == LlmProviderType.claude) {
        buffer.writeln('BACKUP_LLM_PROVIDER=claude');
        buffer.writeln('ANTHROPIC_API_KEY=$backupLlmApiKey');
        buffer.writeln('ANTHROPIC_MODEL=${backupLlmProvider.defaultModel}');
      }
    }

    return buffer.toString();
  }

  ServerConfig copyWith({
    String? serverName,
    int? serverPort,
    String? repoUrl,
    LlmProviderType? llmProvider,
    String? llmApiKey,
    bool? enableBackupLlm,
    LlmProviderType? backupLlmProvider,
    String? backupLlmApiKey,
    String? authSecret,
    String? postgresPassword,
    String? postgresUser,
    String? postgresDb,
    int? postgresPort,
    int? redisPort,
    String? lanIp,
  }) {
    return ServerConfig(
      serverName: serverName ?? this.serverName,
      serverPort: serverPort ?? this.serverPort,
      repoUrl: repoUrl ?? this.repoUrl,
      llmProvider: llmProvider ?? this.llmProvider,
      llmApiKey: llmApiKey ?? this.llmApiKey,
      enableBackupLlm: enableBackupLlm ?? this.enableBackupLlm,
      backupLlmProvider: backupLlmProvider ?? this.backupLlmProvider,
      backupLlmApiKey: backupLlmApiKey ?? this.backupLlmApiKey,
      authSecret: authSecret ?? this.authSecret,
      postgresPassword: postgresPassword ?? this.postgresPassword,
      postgresUser: postgresUser ?? this.postgresUser,
      postgresDb: postgresDb ?? this.postgresDb,
      postgresPort: postgresPort ?? this.postgresPort,
      redisPort: redisPort ?? this.redisPort,
      lanIp: lanIp ?? this.lanIp,
    );
  }
}
