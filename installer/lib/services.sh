#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Service Orchestration and Startup Library
# ==============================================================================

# Start all platform services in the correct dependency order
start_all_services() {
  log_to_file_info "Starting UNOTUSK platform services..."
  log_info "Launching platform container stack..."

  # ── 1. Database Tier ──
  log_to_file_info "Starting Postgres database..."
  if ! execute_compose up -d postgres; then
    log_fatal_err "Failed to start database container." "Check docker logs and resource limits." "https://docs.unotusk.com/ops/db-trouble" "160"
  fi
  if ! wait_for_service_health postgres 90; then
    log_fatal_err "PostgreSQL failed to report healthy." "Check volume permissions or logs: docker compose logs postgres" "https://docs.unotusk.com/ops/db-trouble" "161"
  fi
  log_success "Database engine is online."

  # Run database migrations
  execute_database_migrations

  # ── 2. Cache & Data Store Tier ──
  log_to_file_info "Starting Redis, Qdrant and Arize Phoenix..."
  if ! execute_compose up -d redis qdrant phoenix; then
    log_fatal_err "Failed to start cache/vector store tier." "Check docker logs." "https://docs.unotusk.com/ops/stores-trouble" "162"
  fi
  wait_for_service_health redis 60
  wait_for_service_health qdrant 90
  wait_for_service_health phoenix 90
  log_success "Cache and storage services are online."

  # ── 3. Identity and Authorization Service (US) ──
  log_to_file_info "Starting US (Auth Service)..."
  if ! execute_compose up -d us; then
    log_fatal_err "Failed to start US service." "Check docker logs." "https://docs.unotusk.com/ops/auth-trouble" "163"
  fi
  if ! wait_for_service_health us 120; then
    log_fatal_err "US failed to report healthy." "Check US/.env configuration and logs: docker compose logs us" "https://docs.unotusk.com/ops/auth-trouble" "164"
  fi
  log_success "Auth Service is online."

  # ── 4. Core Company Logic Service (UPS) ──
  log_to_file_info "Starting UPS (Company Server)..."
  if ! execute_compose up -d ups; then
    log_fatal_err "Failed to start UPS service." "Check docker logs." "https://docs.unotusk.com/ops/ups-trouble" "165"
  fi
  if ! wait_for_service_health ups 120; then
    log_fatal_err "UPS failed to report healthy." "Check license configurations and logs: docker compose logs ups" "https://docs.unotusk.com/ops/ups-trouble" "166"
  fi
  log_success "Company Server is online."

  # ── 5. AI Reasoning Engine (AI PIE) ──
  log_to_file_info "Starting AI-PIE (Reasoning Engine)..."
  if ! execute_compose up -d ai-pie; then
    log_fatal_err "Failed to start AI-PIE engine." "Check docker logs." "https://docs.unotusk.com/ops/ai-trouble" "167"
  fi
  if ! wait_for_service_health ai-pie 180; then
    log_fatal_err "AI-PIE failed to report healthy." "Check credentials and logs: docker compose logs ai-pie" "https://docs.unotusk.com/ops/ai-trouble" "168"
  fi
  log_success "AI Engine is online."

  # ── 6. Ingress Reverse Proxy (Caddy) ──
  log_to_file_info "Starting Ingress Reverse Proxy (Caddy)..."
  if ! execute_compose up -d caddy; then
    log_fatal_err "Failed to start Caddy ingress proxy." "Check port 80/443 mapping conflicts." "https://docs.unotusk.com/ops/ingress-trouble" "169"
  fi
  if ! wait_for_service_health caddy 60; then
    log_fatal_err "Caddy proxy failed to report healthy." "Check logs: docker compose logs caddy" "https://docs.unotusk.com/ops/ingress-trouble" "170"
  fi
  log_success "Caddy Reverse Proxy is online."

  log_success "All stack containers successfully started."
}

# Stop all platform services
stop_all_services() {
  log_to_file_info "Stopping all UNOTUSK services..."
  log_info "Stopping platform container stack..."
  if ! execute_compose down; then
    log_to_file_err "Docker Compose down returned errors."
    log_warn "Teardown script encountered errors. Force cleanup may be required."
  else
    log_success "All platform services stopped."
  fi
}

# Restart all services with diagnostic checks
restart_all_services() {
  log_to_file_info "Restarting all UNOTUSK services..."
  log_info "Restarting platform container stack..."
  if ! execute_compose restart; then
    log_to_file_err "Docker Compose restart returned errors."
  fi
  verify_overall_health
}
