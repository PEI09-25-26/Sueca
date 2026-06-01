#!/usr/bin/env bash
set -euo pipefail

# Create an EMQX built-in-database user via the EMQX HTTP management API.
# By default reads `MQTT_USERNAME` and `MQTT_PASSWORD` from the repository `.env`.
# Usage: ./create_user.sh                 # reads credentials from .env
#        ./create_user.sh <user> <pass>  # override from CLI

COMPOSE_FILE="docker-compose.yml"
SERVICE_NAME="emqx"
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file '$ENV_FILE' not found. Run this script from repo root (sueca_1.4_pubsub/) or set ENV_FILE." >&2
  exit 1
fi

# Helper to read a value from .env without executing it (safe for JSON)
get_env() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | head -n1 | sed -E "s/^${key}=(.*)$/\1/" | sed -E 's/^"(.*)"$/\1/' || true
}

USERNAME="$(get_env MQTT_USERNAME)"
PASSWORD="$(get_env MQTT_PASSWORD)"

if [ "$#" -ge 2 ]; then
  USERNAME="$1"
  PASSWORD="$2"
fi

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
  echo "MQTT_USERNAME or MQTT_PASSWORD missing in $ENV_FILE and not supplied as arguments." >&2
  echo "Usage: $0 <username> <password>" >&2
  exit 2
fi

# EMQX admin API credentials: optionally set in .env as EMQX_API_USER / EMQX_API_PASS
API_USER="$(get_env EMQX_API_USER)"
API_PASS="$(get_env EMQX_API_PASS)"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-public}"

API_BASE="http://127.0.0.1:18083/api/v5/authentication/password_based%3Abuilt_in_database"

echo "Creating EMQX user '$USERNAME' via HTTP API (host) using API user '$API_USER'..."

# Check if user already exists (HTTP)
if curl -sS -u "$API_USER:$API_PASS" "$API_BASE/users/$USERNAME" -o /dev/null -w "%{http_code}" | grep -q "^200$"; then
  echo "User '$USERNAME' already exists (HTTP)."
  exit 0
fi

# Try create via host HTTP API
HTTP_CODE=$(curl -sS -u "$API_USER:$API_PASS" -H "Content-Type: application/json" -X POST "$API_BASE/users" -d "{\"user_id\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" -w "%{http_code}" -o /tmp/emqx_create_user_resp.$$) || HTTP_CODE=""

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
  echo "User '$USERNAME' created via HTTP API (host)."
  rm -f /tmp/emqx_create_user_resp.$$
  exit 0
fi

echo "Host HTTP API call failed or EMQX not reachable on 127.0.0.1:18083 (http code=$HTTP_CODE). Trying inside container via docker-compose..."

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Compose file $COMPOSE_FILE not found. Cannot exec into container." >&2
  exit 3
fi

# If curl exists inside the container, invoke it there (use docker-compose exec)
if docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" sh -c "command -v curl >/dev/null 2>&1"; then
  docker-compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" curl -sS -u "$API_USER:$API_PASS" -H "Content-Type: application/json" -X POST "$API_BASE/users" -d "{\"user_id\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" -w "\nHTTP:%{http_code}\n" || true
  echo "If the container call failed, check container logs: docker-compose -f $COMPOSE_FILE logs $SERVICE_NAME" >&2
  exit 0
else
  echo "curl not available inside container. Please either run this script from the host when EMQX management API is reachable on 127.0.0.1:18083, or install curl in the container." >&2
  exit 4
fi
