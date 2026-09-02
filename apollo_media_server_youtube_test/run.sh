#!/usr/bin/with-contenv bashio
set -e

LOG_LEVEL="$(bashio::config 'log_level')"
YOUTUBE_IMPORT_KEY="$(bashio::config 'youtube_import_key')"
export APOLLO_DATABASE_URL="sqlite:////config/apollo.db"
export APOLLO_LOG_LEVEL="${LOG_LEVEL}"
export APOLLO_YOUTUBE_IMPORT_KEY="${YOUTUBE_IMPORT_KEY}"

install_custom_ca() {
    local source_ca="/ssl/Apollo+CA.crt"
    local target_ca="/usr/local/share/ca-certificates/apollo-home-ca.crt"

    if [ ! -f "${source_ca}" ]; then
        bashio::log.info "Custom Apollo CA not found at ${source_ca}; using system trust store"
        return
    fi

    bashio::log.info "Installing custom Apollo CA from ${source_ca}"
    cp "${source_ca}" "${target_ca}"

    if ! update-ca-certificates >/tmp/apollo-update-ca.log 2>&1; then
        cat /tmp/apollo-update-ca.log >&2 || true
        bashio::log.fatal "Failed to update container CA trust store"
        exit 1
    fi

    bashio::log.info "Custom Apollo CA installed"
}

install_custom_ca

export SSL_CERT_FILE="/etc/ssl/certs/ca-certificates.crt"
export REQUESTS_CA_BUNDLE="${SSL_CERT_FILE}"

bashio::log.info "TLS trust bundle: ${SSL_CERT_FILE}"
bashio::log.info "Starting Apollo Media Server ${APOLLO_VERSION:-dev}"
bashio::log.info "Database: persistent add-on config storage"

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8099 \
  --log-level "${LOG_LEVEL}"
