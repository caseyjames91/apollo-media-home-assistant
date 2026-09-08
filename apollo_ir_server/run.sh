#!/usr/bin/with-contenv bashio
set -e

LOG_LEVEL="$(bashio::config 'log_level')"
API_KEY="$(bashio::config 'api_key')"

export APOLLO_IR_LOG_LEVEL="${LOG_LEVEL}"
export APOLLO_IR_API_KEY="${API_KEY}"
export HOME_ASSISTANT_URL="http://supervisor/core"
export HOME_ASSISTANT_TOKEN="${SUPERVISOR_TOKEN}"

bashio::log.info "Starting Apollo IR Server ${APOLLO_IR_VERSION:-dev}"
bashio::log.info "Home Assistant backend: Supervisor Core API"
if [ -z "${API_KEY}" ]; then
    bashio::log.warning "Apollo IR API key is empty; LAN API authentication is disabled"
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8100 \
  --log-level "${LOG_LEVEL}"
