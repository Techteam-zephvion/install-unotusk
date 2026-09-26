import '../../config/domain/server_config.dart';

class ComposeGenerator {
  /// Generates a Docker Compose configuration for local/multi-server deployment.
  ///
  /// Secrets and database credentials are read via Docker Compose environment
  /// substitution from the accompanying `.env` file (${POSTGRES_PASSWORD},
  /// ${AUTH_SECRET}, ${GROQ_API_KEY} / ${ANTHROPIC_API_KEY}) to avoid baking
  /// plaintext credentials into the compose YAML.
  ///
  /// Global container names are omitted so Docker isolates each deployment
  /// by project name (`docker compose -p <project>`).
  static String generateDockerCompose(ServerConfig config, {String? projectRoot}) {
    final apiKeyVar = config.llmProvider == LlmProviderType.groq ? "GROQ_API_KEY" : "ANTHROPIC_API_KEY";
    final modelVar = config.llmProvider == LlmProviderType.groq ? "GROQ_MODEL" : "ANTHROPIC_MODEL";

    return '''
services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_USER: \${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD}
      POSTGRES_DB: \${POSTGRES_DB:-unotusk}
    volumes:
      - unotusk_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${POSTGRES_USER:-postgres} -d \${POSTGRES_DB:-unotusk}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - unotusk-network

  redis:
    image: redis:7-alpine
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
      dockerfile: infrastructure/docker/Dockerfile.api''' : '    image: unotusk-api:0.1.0'}
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - SYNC_DATABASE_URL=\${SYNC_DATABASE_URL}
    command: ["alembic", "upgrade", "head"]
    networks:
      - unotusk-network

  api:
${projectRoot != null ? '''    build:
      context: $projectRoot
      dockerfile: infrastructure/docker/Dockerfile.api''' : '    image: unotusk-api:0.1.0'}
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
      - DATABASE_URL=\${DATABASE_URL}
      - SYNC_DATABASE_URL=\${SYNC_DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=\${AUTH_SECRET}
      - LLM_PROVIDER=\${LLM_PROVIDER:-groq}
      - $apiKeyVar=\${$apiKeyVar}
      - $modelVar=\${$modelVar}
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
      - DATABASE_URL=\${DATABASE_URL}
      - SYNC_DATABASE_URL=\${SYNC_DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=\${AUTH_SECRET}
      - LLM_PROVIDER=\${LLM_PROVIDER:-groq}
      - $apiKeyVar=\${$apiKeyVar}
      - $modelVar=\${$modelVar}
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

  /// Generates a Docker Compose configuration for production using prebuilt images.
  static String generateProductionCompose(ServerConfig config, {required String imageTag}) {
    final apiKeyVar = config.llmProvider == LlmProviderType.groq ? "GROQ_API_KEY" : "ANTHROPIC_API_KEY";
    final modelVar = config.llmProvider == LlmProviderType.groq ? "GROQ_MODEL" : "ANTHROPIC_MODEL";

    return '''
services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_USER: \${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD}
      POSTGRES_DB: \${POSTGRES_DB:-unotusk}
    volumes:
      - unotusk_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \${POSTGRES_USER:-postgres} -d \${POSTGRES_DB:-unotusk}"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - unotusk-network

  redis:
    image: redis:7-alpine
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
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URL=\${DATABASE_URL}
      - SYNC_DATABASE_URL=\${SYNC_DATABASE_URL}
    command: ["alembic", "upgrade", "head"]
    networks:
      - unotusk-network

  api:
    image: $imageTag
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
      - DATABASE_URL=\${DATABASE_URL}
      - SYNC_DATABASE_URL=\${SYNC_DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=\${AUTH_SECRET}
      - LLM_PROVIDER=\${LLM_PROVIDER:-groq}
      - $apiKeyVar=\${$apiKeyVar}
      - $modelVar=\${$modelVar}
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
      - DATABASE_URL=\${DATABASE_URL}
      - SYNC_DATABASE_URL=\${SYNC_DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - AUTH_SECRET=\${AUTH_SECRET}
      - LLM_PROVIDER=\${LLM_PROVIDER:-groq}
      - $apiKeyVar=\${$apiKeyVar}
      - $modelVar=\${$modelVar}
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
