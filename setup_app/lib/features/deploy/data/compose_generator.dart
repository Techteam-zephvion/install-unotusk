import '../../config/domain/server_config.dart';

class ComposeGenerator {
  /// Generates a Docker Compose configuration for production using prebuilt images.
  static String generateProductionCompose(ServerConfig config, {required String imageVersion}) {
    final apiKeyVar = config.llmProvider == LlmProviderType.groq ? "GROQ_API_KEY" : "ANTHROPIC_API_KEY";
    final modelVar = config.llmProvider == LlmProviderType.groq ? "GROQ_MODEL" : "ANTHROPIC_MODEL";

    final apiImage = "ghcr.io/techteam-zephvion/unotusk-api:$imageVersion";
    final workerImage = "ghcr.io/techteam-zephvion/unotusk-worker:$imageVersion";

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
    image: $apiImage
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
    image: $apiImage
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
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
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
    image: $workerImage
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
