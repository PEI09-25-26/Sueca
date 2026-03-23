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

assert_success_false() {
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

assert_message_not_contains() {
  local json="$1"
  local needle="$2"
  local label="$3"
  local msg
  msg=$(json_field "$json" '.message // ""')
  [[ "$msg" != *"$needle"* ]] || fail "$label unexpectedly contained '$needle'"
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

# 12) Non-host start should fail
START_NON_HOST=$(curl -sS -X POST "$BASE/api/start" -H "Content-Type: application/json" -H "Authorization: Bearer $BOB_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}') || fail "start non-host request failed"
assert_success_false "$START_NON_HOST" "Non-host start"
assert_message_contains "$START_NON_HOST" "Only room creator can start the game" "Non-host start"
pass "Non-host start rejected"

# 13) Host start should pass host-auth layer
START_HOST=$(curl -sS -X POST "$BASE/api/start" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}') || fail "start host request failed"
assert_message_not_contains "$START_HOST" "Only room creator can start the game" "Host start"
pass "Host start accepted by host-auth layer"

# 14) Non-host rematch should fail
REMATCH_NON_HOST=$(curl -sS -X POST "$BASE/api/room/$GAME_ID/rematch" -H "Authorization: Bearer $BOB_TOKEN") || fail "rematch non-host request failed"
assert_success_false "$REMATCH_NON_HOST" "Non-host rematch"
assert_message_contains "$REMATCH_NON_HOST" "Only room creator can start rematch" "Non-host rematch"
pass "Non-host rematch rejected"

# 15) Host rematch should pass host-auth layer (game-state success may vary)
REMATCH_HOST=$(curl -sS -X POST "$BASE/api/room/$GAME_ID/rematch" -H "Authorization: Bearer $ALICE_TOKEN") || fail "rematch host request failed"
assert_message_not_contains "$REMATCH_HOST" "Only room creator can start rematch" "Host rematch"
pass "Host rematch accepted by host-auth layer"

# 16) Non-host reset should fail
RESET_NON_HOST=$(curl -sS -X POST "$BASE/api/reset" -H "Content-Type: application/json" -H "Authorization: Bearer $BOB_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}') || fail "reset non-host request failed"
assert_success_false "$RESET_NON_HOST" "Non-host reset"
assert_message_contains "$RESET_NON_HOST" "Only room creator can reset the game" "Non-host reset"
pass "Non-host reset rejected"

# 17) Host reset should pass
RESET_HOST=$(curl -sS -X POST "$BASE/api/reset" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}') || fail "reset host request failed"
assert_success_true "$RESET_HOST" "Host reset"
pass "Host reset allowed"

# 18) Cross-game token binding must fail
CREATE_OTHER=$(curl -sS -X POST "$BASE/api/create_room") || fail "create other room failed"
OTHER_GAME=$(json_field "$CREATE_OTHER" '.game_id')
assert_non_empty_not_null "$OTHER_GAME" "OTHER_GAME"

PLAY_OTHER=$(curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$OTHER_GAME"'","card":"1"}') || fail "cross-game play request failed"
assert_success_false "$PLAY_OTHER" "Cross-game token binding"
assert_message_contains "$PLAY_OTHER" "Player not in this game" "Cross-game token binding"
pass "Token is bound to game_id"

echo ""
echo "All strict Phase B checks passed."
