import '../../config/domain/server_config.dart';

class ComposeGenerator {
  /// Generates a Docker Compose configuration for local development.
  ///
  /// The caller must supply [projectRoot] (the Unotusk source directory)
  /// for the build context.
  static String generateDockerCompose(ServerConfig config, {String? projectRoot}) {
    return '''
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: unotusk-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${config.postgresUser}
      POSTGRES_PASSWORD: ${config.postgresPassword}
      POSTGRES_DB: ${config.postgresDb}
    volumes:
      - unotusk_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${config.postgresUser} -d ${config.postgresDb}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - unotusk-network

  redis:
    image: redis:7-alpine
    container_name: unotusk-redis
    restart: unless-stopped
    volumes:
      - unotusk_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - unotusk-network

  migration:
${projectRoot != null ? '''    build:
      context: $projectRoot
      dockerfile: infrastructure/docker/Dockerfile.worker''' : '    image: unotusk-worker:0.1.0'}
    container_name: unotusk-migration
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - SYNC_DATABASE_URL=postgresql://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
    command: ["alembic", "upgrade", "head"]
    networks:
      - unotusk-network

  api:
${projectRoot != null ? '''    build:
      context: $projectRoot
      dockerfile: infrastructure/docker/Dockerfile.api''' : '    image: unotusk-api:0.1.0'}
    container_name: unotusk-api
    restart: unless-stopped
    depends_on:
      migration:
        condition: service_completed_successfully
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - APP_ENV=production
      - DEBUG=false
      - DATABASE_URL=postgresql+asyncpg://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - SYNC_DATABASE_URL=postgresql://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=${config.authSecret}
      - LLM_PROVIDER=${config.llmProvider == LlmProviderType.groq ? "groq" : "claude"}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_API_KEY" : "ANTHROPIC_API_KEY"}=${config.llmApiKey}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_MODEL" : "ANTHROPIC_MODEL"}=${config.llmProvider.defaultModel}
    ports:
      - "${config.serverPort}:8000"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - unotusk-network

  worker:
${projectRoot != null ? '''    build:
      context: $projectRoot
      dockerfile: infrastructure/docker/Dockerfile.worker''' : '    image: unotusk-worker:0.1.0'}
    container_name: unotusk-worker
    restart: unless-stopped
    depends_on:
      migration:
        condition: service_completed_successfully
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - APP_ENV=production
      - DEBUG=false
      - DATABASE_URL=postgresql+asyncpg://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - SYNC_DATABASE_URL=postgresql://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=${config.authSecret}
      - LLM_PROVIDER=${config.llmProvider == LlmProviderType.groq ? "groq" : "claude"}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_API_KEY" : "ANTHROPIC_API_KEY"}=${config.llmApiKey}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_MODEL" : "ANTHROPIC_MODEL"}=${config.llmProvider.defaultModel}
      - QUEUE_NAME=unotusk_tasks
    networks:
      - unotusk-network

volumes:
  unotusk_postgres_data:
  unotusk_redis_data:

networks:
  unotusk-network:
    driver: bridge
''';
  }

  /// Generates a Docker Compose configuration for production using a prebuilt [imageTag].
  static String generateProductionCompose(ServerConfig config, {required String imageTag}) {
    return '''
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: unotusk-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${config.postgresUser}
      POSTGRES_PASSWORD: ${config.postgresPassword}
      POSTGRES_DB: ${config.postgresDb}
    volumes:
      - unotusk_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${config.postgresUser} -d ${config.postgresDb}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - unotusk-network

  redis:
    image: redis:7-alpine
    container_name: unotusk-redis
    restart: unless-stopped
    volumes:
      - unotusk_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - unotusk-network

  migration:
    image: $imageTag
    container_name: unotusk-migration
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - SYNC_DATABASE_URL=postgresql://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
    command: ["alembic", "upgrade", "head"]
    networks:
      - unotusk-network

  api:
    image: $imageTag
    container_name: unotusk-api
    restart: unless-stopped
    depends_on:
      migration:
        condition: service_completed_successfully
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - APP_ENV=production
      - DEBUG=false
      - DATABASE_URL=postgresql+asyncpg://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - SYNC_DATABASE_URL=postgresql://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=${config.authSecret}
      - LLM_PROVIDER=${config.llmProvider == LlmProviderType.groq ? "groq" : "claude"}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_API_KEY" : "ANTHROPIC_API_KEY"}=${config.llmApiKey}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_MODEL" : "ANTHROPIC_MODEL"}=${config.llmProvider.defaultModel}
    ports:
      - "${config.serverPort}:8000"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - unotusk-network

  worker:
    image: $imageTag
    container_name: unotusk-worker
    restart: unless-stopped
    depends_on:
      migration:
        condition: service_completed_successfully
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - APP_ENV=production
      - DEBUG=false
      - DATABASE_URL=postgresql+asyncpg://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - SYNC_DATABASE_URL=postgresql://${config.postgresUser}:${config.postgresPassword}@postgres:5432/${config.postgresDb}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=${config.authSecret}
      - LLM_PROVIDER=${config.llmProvider == LlmProviderType.groq ? "groq" : "claude"}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_API_KEY" : "ANTHROPIC_API_KEY"}=${config.llmApiKey}
      - ${config.llmProvider == LlmProviderType.groq ? "GROQ_MODEL" : "ANTHROPIC_MODEL"}=${config.llmProvider.defaultModel}
      - QUEUE_NAME=unotusk_tasks
    networks:
      - unotusk-network

volumes:
  unotusk_postgres_data:
  unotusk_redis_data:

networks:
  unotusk-network:
    driver: bridge
''';
  }
}
