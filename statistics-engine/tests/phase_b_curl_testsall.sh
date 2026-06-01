#!/usr/bin/env bash
set -euo pipefail

# Strict Phase B validation script.
# Stops on first unexpected result and prints PASS/FAIL per step.
# Usage:
#   BASE="http://localhost:5001" ./tests/phase_b_curl_tests.sh

BASE="${BASE:-http://localhost:5001}"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

json_field() {
  local json="$1"
  local query="$2"
  echo "$json" | jq -r "$query"
}

assert_success_false() {#!/usr/bin/env bash
# Phase B curl one-liner checklist
# Run this line-by-line in a terminal while the API is running on localhost:5001.
# Each command is a one-liner and includes the expected result.

# 0) Set API base URL.
# Expected: no output; BASE variable is available.
BASE="http://localhost:5001"

# 1) Quick health probe.
# Expected: JSON game state response (HTTP 200), not empty.
curl -sS "$BASE/api/status" | jq '.'

# 2) Create room and store GAME_ID.
# Expected: GAME_ID is non-empty and not null.
GAME_ID=$(curl -sS -X POST "$BASE/api/create_room" | jq -r '.game_id'); echo "GAME_ID=$GAME_ID"

# 3) Join Alice (host) and store raw response.
# Expected: success=true and token present.
ALICE_JOIN=$(curl -sS -X POST "$BASE/api/join" -H "Content-Type: application/json" -d '{"game_id":"'"$GAME_ID"'","name":"Alice","position":"NORTH"}'); echo "$ALICE_JOIN" | jq '.'

# 4) Extract Alice identity and token.
# Expected: ALICE_ID non-null, ALICE_TOKEN_LEN > 100.
ALICE_TOKEN=$(echo "$ALICE_JOIN" | jq -r '.token'); ALICE_ID=$(echo "$ALICE_JOIN" | jq -r '.player_id'); echo "ALICE_ID=$ALICE_ID ALICE_TOKEN_LEN=${#ALICE_TOKEN}"

# 5) Join Bob and store raw response.
# Expected: success=true and token present.
BOB_JOIN=$(curl -sS -X POST "$BASE/api/join" -H "Content-Type: application/json" -d '{"game_id":"'"$GAME_ID"'","name":"Bob","position":"WEST"}'); echo "$BOB_JOIN" | jq '.'

# 6) Extract Bob identity and token.
# Expected: BOB_ID non-null, BOB_TOKEN_LEN > 100.
BOB_TOKEN=$(echo "$BOB_JOIN" | jq -r '.token'); BOB_ID=$(echo "$BOB_JOIN" | jq -r '.player_id'); echo "BOB_ID=$BOB_ID BOB_TOKEN_LEN=${#BOB_TOKEN}"

# 7) Variable sanity check.
# Expected: BASE, GAME_ID, ALICE_ID, BOB_ID non-empty; token lengths non-zero.
printf 'BASE=%s\nGAME_ID=%s\nALICE_ID=%s\nBOB_ID=%s\nALICE_TOKEN_LEN=%s\nBOB_TOKEN_LEN=%s\n' "$BASE" "$GAME_ID" "$ALICE_ID" "$BOB_ID" "${#ALICE_TOKEN}" "${#BOB_TOKEN}"

# 8) Protected play without token.
# Expected: success=false, message similar to "Missing authorization header".
curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -d '{"game_id":"'"$GAME_ID"'","card":"1"}' | jq '.'

# 9) Protected play with wrong auth scheme.
# Expected: success=false, message similar to "Invalid authorization header format".
curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Token $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","card":"1"}' | jq '.'

# 10) Protected play with valid token.
# Expected: NO auth error; may still fail with game rule message (for example "Not your turn").
curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","card":"1"}' | jq '.'

# 11) Host-only add_bot with host token.
# Expected: success=true (message may be "Bot ... is joining...").
curl -sS -X POST "$BASE/api/add_bot" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","name":"Bot1","position":"SOUTH","difficulty":"random"}' | jq '.'

# 12) Host-only add_bot with non-host token.
# Expected: success=false, message similar to "Only room creator can add bots".
curl -sS -X POST "$BASE/api/add_bot" -H "Content-Type: application/json" -H "Authorization: Bearer $BOB_TOKEN" -d '{"game_id":"'"$GAME_ID"'","name":"Bot2","position":"EAST","difficulty":"random"}' | jq '.'

# 13) Change position using Bob token.
# Expected: auth passes; success depends on slot availability/game phase.
curl -sS -X POST "$BASE/api/change_position" -H "Content-Type: application/json" -H "Authorization: Bearer $BOB_TOKEN" -d '{"game_id":"'"$GAME_ID"'","position":"EAST"}' | jq '.'

# 14) Remove Bob using host token.
# Expected: auth passes and host check passes; success depends on game phase.
curl -sS -X POST "$BASE/api/remove_player" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","target_id":"'"$BOB_ID"'"}' | jq '.'

# 15) Start game as host.
# Expected: auth passes and host check passes; success depends on room state.
curl -sS -X POST "$BASE/api/start" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}' | jq '.'

# 16) Reset game as host.
# Expected: success=true if host token is valid.
curl -sS -X POST "$BASE/api/reset" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}' | jq '.'

# 17) Rematch as host.
# Expected: auth passes and host check passes; success depends on room state.
curl -sS -X POST "$BASE/api/room/$GAME_ID/rematch" -H "Authorization: Bearer $ALICE_TOKEN" | jq '.'

# 18) Cross-game token binding check.
# Expected: success=false, message similar to "Player not in this game".
OTHER_GAME=$(curl -sS -X POST "$BASE/api/create_room" | jq -r '.game_id'); echo "OTHER_GAME=$OTHER_GAME"; curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$OTHER_GAME"'","card":"1"}' | jq '.'

# 19) Final token sanity check.
# Expected: "ALICE TOKEN OK".
[ -n "$ALICE_TOKEN" ] && [ "$ALICE_TOKEN" != "null" ] && echo "ALICE TOKEN OK" || echo "ALICE TOKEN INVALID"

  local json="$1"
  local label="$2"
  local success
  success=$(json_field "$json" '.success')
  [[ "$success" == "false" ]] || fail "$label expected success=false, got success=$success"
}

assert_success_true() {
  local json="$1"
  local label="$2"
  local success
  success=$(json_field "$json" '.success')
  [[ "$success" == "true" ]] || fail "$label expected success=true, got success=$success"
}

assert_message_contains() {
  local json="$1"
  local needle="$2"
  local label="$3"
  local msg
  msg=$(json_field "$json" '.message // ""')
  [[ "$msg" == *"$needle"* ]] || fail "$label expected message containing '$needle', got '$msg'"
}

assert_non_empty_not_null() {
  local value="$1"
  local label="$2"
  [[ -n "$value" && "$value" != "null" ]] || fail "$label is empty or null"
}

require_cmd curl
require_cmd jq

echo "== Phase B Strict Tests =="
echo "BASE=$BASE"

# 1) API health
STATUS_RAW=$(curl -sS "$BASE/api/status") || fail "status request failed"
[[ -n "$STATUS_RAW" ]] || fail "status response is empty"
pass "API status reachable"

# 2) Create room
CREATE_RAW=$(curl -sS -X POST "$BASE/api/create_room") || fail "create_room request failed"
GAME_ID=$(json_field "$CREATE_RAW" '.game_id')
assert_non_empty_not_null "$GAME_ID" "GAME_ID"
pass "Room created: $GAME_ID"

# 3) Join Alice
ALICE_JOIN=$(curl -sS -X POST "$BASE/api/join" -H "Content-Type: application/json" -d '{"game_id":"'"$GAME_ID"'","name":"Alice","position":"NORTH"}') || fail "Alice join failed"
assert_success_true "$ALICE_JOIN" "Alice join"
ALICE_TOKEN=$(json_field "$ALICE_JOIN" '.token')
ALICE_ID=$(json_field "$ALICE_JOIN" '.player_id')
assert_non_empty_not_null "$ALICE_TOKEN" "ALICE_TOKEN"
assert_non_empty_not_null "$ALICE_ID" "ALICE_ID"
pass "Alice joined with token"

# 4) Join Bob
BOB_JOIN=$(curl -sS -X POST "$BASE/api/join" -H "Content-Type: application/json" -d '{"game_id":"'"$GAME_ID"'","name":"Bob","position":"WEST"}') || fail "Bob join failed"
assert_success_true "$BOB_JOIN" "Bob join"
BOB_TOKEN=$(json_field "$BOB_JOIN" '.token')
BOB_ID=$(json_field "$BOB_JOIN" '.player_id')
assert_non_empty_not_null "$BOB_TOKEN" "BOB_TOKEN"
assert_non_empty_not_null "$BOB_ID" "BOB_ID"
pass "Bob joined with token"

# 5) Play without token must fail
PLAY_NO_AUTH=$(curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -d '{"game_id":"'"$GAME_ID"'","card":"1"}') || fail "play without auth request failed"
assert_success_false "$PLAY_NO_AUTH" "Play without token"
assert_message_contains "$PLAY_NO_AUTH" "Missing authorization header" "Play without token"
pass "Play without token rejected"

# 6) Play with invalid auth scheme must fail
PLAY_BAD_SCHEME=$(curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Token $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","card":"1"}') || fail "play with invalid auth scheme request failed"
assert_success_false "$PLAY_BAD_SCHEME" "Play with invalid auth scheme"
assert_message_contains "$PLAY_BAD_SCHEME" "Invalid authorization header format" "Play with invalid auth scheme"
pass "Invalid auth scheme rejected"

# 7) Play with valid token must pass auth layer
PLAY_GOOD_AUTH=$(curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","card":"1"}') || fail "play with valid token request failed"
GOOD_MSG=$(json_field "$PLAY_GOOD_AUTH" '.message // ""')
if [[ "$GOOD_MSG" == *"Missing authorization header"* || "$GOOD_MSG" == *"Invalid authorization header format"* || "$GOOD_MSG" == *"Invalid or expired token"* ]]; then
  fail "Play with valid token still failed auth: $GOOD_MSG"
fi
pass "Valid token accepted by auth layer"

# 8) Token-only hand endpoint for owner should pass
HAND_SELF=$(curl -sS "$BASE/api/hand?game_id=$GAME_ID" -H "Authorization: Bearer $ALICE_TOKEN") || fail "hand self request failed"
assert_success_true "$HAND_SELF" "Get own hand"
pass "Own hand accessible with token"

# 9) Hand access with mismatched token must fail
HAND_OTHER=$(curl -sS "$BASE/api/hand/$BOB_ID?game_id=$GAME_ID" -H "Authorization: Bearer $ALICE_TOKEN") || fail "hand mismatch request failed"
assert_success_false "$HAND_OTHER" "Mismatched hand access"
assert_message_contains "$HAND_OTHER" "Token does not match requested player hand" "Mismatched hand access"
pass "Cross-player hand access rejected"

# 10) Host add_bot should pass
ADD_BOT_HOST=$(curl -sS -X POST "$BASE/api/add_bot" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","name":"Bot1","position":"SOUTH","difficulty":"random"}') || fail "add_bot host request failed"
assert_success_true "$ADD_BOT_HOST" "Host add_bot"
pass "Host add_bot allowed"

# 11) Non-host add_bot should fail
ADD_BOT_NON_HOST=$(curl -sS -X POST "$BASE/api/add_bot" -H "Content-Type: application/json" -H "Authorization: Bearer $BOB_TOKEN" -d '{"game_id":"'"$GAME_ID"'","name":"Bot2","position":"EAST","difficulty":"random"}') || fail "add_bot non-host request failed"
assert_success_false "$ADD_BOT_NON_HOST" "Non-host add_bot"
assert_message_contains "$ADD_BOT_NON_HOST" "Only room creator can add bots" "Non-host add_bot"
pass "Non-host add_bot rejected"

# 12) Cross-game token binding must fail
CREATE_OTHER=$(curl -sS -X POST "$BASE/api/create_room") || fail "create other room failed"
OTHER_GAME=$(json_field "$CREATE_OTHER" '.game_id')
assert_non_empty_not_null "$OTHER_GAME" "OTHER_GAME"

PLAY_OTHER=$(curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$OTHER_GAME"'","card":"1"}') || fail "cross-game play request failed"
assert_success_false "$PLAY_OTHER" "Cross-game token binding"
assert_message_contains "$PLAY_OTHER" "Player not in this game" "Cross-game token binding"
pass "Token is bound to game_id"

echo ""
echo "All strict Phase B checks passed."
