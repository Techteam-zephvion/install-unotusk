import '../../config/domain/server_config.dart';

class ComposeGenerator {
  /// Generates a Docker Compose configuration for production using prebuilt images.
  static String generateProductionCompose(ServerConfig config, {required String imageVersion}) {
    final String apiImage;
    final String workerImage;
    if (imageVersion == '0.5.0' || imageVersion == '0.1.0' || imageVersion == 'local') {
      apiImage = "unotusk-api:$imageVersion";
      workerImage = "unotusk-worker:$imageVersion";
    } else {
      apiImage = "ghcr.io/techteam-zephvion/unotusk-api:$imageVersion";
      workerImage = "ghcr.io/techteam-zephvion/unotusk-worker:$imageVersion";
    }

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
    extra_hosts:
      - "host.docker.internal:host-gateway"
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
      - CLUSTER_FEDERATION_SECRET=\${CLUSTER_FEDERATION_SECRET}
      - CONTROL_PLANE_URL=\${CONTROL_PLANE_URL:-http://host.docker.internal:28000}
      - DATA_PLANE_HOST=\${DATA_PLANE_HOST:-host.docker.internal}
      - DATA_PLANE_PROJECT_SLUG=${config.serverName.toLowerCase().trim().replaceAll(RegExp(r'[^a-z0-9_-]'), '-')}
      - LLM_PROVIDER=\${LLM_PROVIDER:-groq}
      - GROQ_API_KEY=\${GROQ_API_KEY}
      - GROQ_MODEL=\${GROQ_MODEL:-openai/gpt-oss-120b}
      - OPENROUTER_API_KEY=\${OPENROUTER_API_KEY:-}
      - OPENROUTER_MODEL=\${OPENROUTER_MODEL:-meta-llama/llama-3.3-70b-instruct:free}
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY:-}
      - ANTHROPIC_MODEL=\${ANTHROPIC_MODEL:-claude-3-5-sonnet-20241022}
      - BACKUP_LLM_PROVIDER=\${BACKUP_LLM_PROVIDER:-openrouter}
      - SERVER_PORT=${config.serverPort}
      - TARGET_REPO_URL=\${TARGET_REPO_URL:-}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "${config.serverPort}:${config.serverPort}"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:${config.serverPort}/health || exit 1"]
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
      - GROQ_API_KEY=\${GROQ_API_KEY}
      - GROQ_MODEL=\${GROQ_MODEL:-openai/gpt-oss-120b}
      - OPENROUTER_API_KEY=\${OPENROUTER_API_KEY:-}
      - OPENROUTER_MODEL=\${OPENROUTER_MODEL:-meta-llama/llama-3.3-70b-instruct:free}
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY:-}
      - ANTHROPIC_MODEL=\${ANTHROPIC_MODEL:-claude-3-5-sonnet-20241022}
      - BACKUP_LLM_PROVIDER=\${BACKUP_LLM_PROVIDER:-openrouter}
      - TARGET_REPO_URL=\${TARGET_REPO_URL:-}
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
