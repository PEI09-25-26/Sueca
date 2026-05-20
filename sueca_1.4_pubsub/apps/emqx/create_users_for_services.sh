#!/usr/bin/env bash
set -euo pipefail

# Bulk-create MQTT users by calling create_user.sh for each username:password pair.
# Usage: ./create_users_for_services.sh gateway:pass virtual_engine:pass physical_engine:pass cloudflare:pass
# It forwards each pair to create_user.sh which will use the EMQX HTTP API.

SCRIPT_DIR=$(dirname "$0")
CREATE_USER="$SCRIPT_DIR/create_user.sh"

if [ ! -x "$CREATE_USER" ]; then
  echo "create_user.sh not found or not executable at $CREATE_USER" >&2
  echo "Make it executable: chmod +x $CREATE_USER" >&2
  exit 1
fi

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 user1:pass1 [user2:pass2 ...]" >&2
  exit 2
fi

for pair in "$@"; do
  if [[ "$pair" != *":"* ]]; then
    echo "Skipping invalid pair '$pair' (expected user:pass)" >&2
    continue
  fi
  user=${pair%%:*}
  pass=${pair#*:}
  echo "Creating user '$user'..."
  "$CREATE_USER" "$user" "$pass" || { echo "Failed to create user $user" >&2; exit 3; }
done

echo "Done. Remember to store passwords securely and update your services' env vars."