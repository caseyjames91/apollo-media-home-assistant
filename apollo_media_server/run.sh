#!/usr/bin/with-contenv bashio
set -e

LOG_LEVEL="$(bashio::config 'log_level')"
export APOLLO_DATABASE_URL="sqlite:////config/apollo.db"
export APOLLO_LOG_LEVEL="${LOG_LEVEL}"

bashio::log.info "Starting Apollo Media Server 0.1.2"
bashio::log.info "Database: persistent add-on config storage"

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8099 \
  --log-level "${LOG_LEVEL}"
