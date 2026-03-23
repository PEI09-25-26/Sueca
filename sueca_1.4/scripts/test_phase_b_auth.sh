#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://localhost:5001}"

echo "== Phase B Auth Smoke Test =="
echo "BASE=$BASE"

if ! command -v jq >/dev/null 2>&1; then
  echo "[FAIL] jq is required but not installed."
  exit 1
fi

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

json_field() {
  local json="$1"
  local field="$2"
  echo "$json" | jq -r "$field"
}

# 1) Create room
CREATE_RESP=$(curl -sS -X POST "$BASE/api/create_room") || fail "create_room request failed"
GAME_ID=$(json_field "$CREATE_RESP" '.game_id')
[[ -n "$GAME_ID" && "$GAME_ID" != "null" ]] || fail "create_room did not return game_id"
pass "create_room returned game_id=$GAME_ID"

# 2) Join as host and capture token
JOIN_A=$(curl -sS -X POST "$BASE/api/join" \
  -H "Content-Type: application/json" \
  -d '{"game_id":"'"$GAME_ID"'","name":"Alice","position":"NORTH"}') || fail "join (Alice) failed"

ALICE_TOKEN=$(json_field "$JOIN_A" '.token')
ALICE_ID=$(json_field "$JOIN_A" '.player_id')
[[ -n "$ALICE_TOKEN" && "$ALICE_TOKEN" != "null" ]] || fail "Alice join did not return token"
pass "Alice token issued"

# 3) Protected endpoint without token must fail
NO_AUTH_PLAY=$(curl -sS -X POST "$BASE/api/play" \
  -H "Content-Type: application/json" \
  -d '{"game_id":"'"$GAME_ID"'","card":"1"}') || fail "play without auth request failed"

NO_AUTH_SUCCESS=$(json_field "$NO_AUTH_PLAY" '.success')
[[ "$NO_AUTH_SUCCESS" == "false" ]] || fail "play without token should fail"
pass "play without token is rejected"

# 4) Protected endpoint with malformed token must fail
BAD_AUTH_PLAY=$(curl -sS -X POST "$BASE/api/play" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token $ALICE_TOKEN" \
  -d '{"game_id":"'"$GAME_ID"'","card":"1"}') || fail "play with malformed auth request failed"

BAD_AUTH_SUCCESS=$(json_field "$BAD_AUTH_PLAY" '.success')
[[ "$BAD_AUTH_SUCCESS" == "false" ]] || fail "play with malformed auth should fail"
pass "malformed auth header is rejected"

# 5) Protected endpoint with valid token should pass auth layer
GOOD_AUTH_PLAY=$(curl -sS -X POST "$BASE/api/play" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -d '{"game_id":"'"$GAME_ID"'","card":"1"}') || fail "play with token request failed"

GOOD_AUTH_MSG=$(json_field "$GOOD_AUTH_PLAY" '.message')
if [[ "$GOOD_AUTH_MSG" == "Missing authorization header" || "$GOOD_AUTH_MSG" == "Invalid authorization header format" || "$GOOD_AUTH_MSG" == "Invalid or expired token" ]]; then
  fail "play with valid token still failed auth"
fi
pass "valid token passes auth layer (message: $GOOD_AUTH_MSG)"

# 6) Host-only: Alice can add bot
ADD_BOT_HOST=$(curl -sS -X POST "$BASE/api/add_bot" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -d '{"game_id":"'"$GAME_ID"'","name":"Bot1","position":"SOUTH","difficulty":"random"}') || fail "add_bot as host failed"

ADD_BOT_HOST_SUCCESS=$(json_field "$ADD_BOT_HOST" '.success')
[[ "$ADD_BOT_HOST_SUCCESS" == "true" ]] || fail "host should be able to add bot"
pass "host add_bot accepted"

# 7) Join Bob and verify non-host is blocked from add_bot
JOIN_B=$(curl -sS -X POST "$BASE/api/join" \
  -H "Content-Type: application/json" \
  -d '{"game_id":"'"$GAME_ID"'","name":"Bob","position":"WEST"}') || fail "join (Bob) failed"

BOB_TOKEN=$(json_field "$JOIN_B" '.token')
[[ -n "$BOB_TOKEN" && "$BOB_TOKEN" != "null" ]] || fail "Bob join did not return token"

ADD_BOT_NON_HOST=$(curl -sS -X POST "$BASE/api/add_bot" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -d '{"game_id":"'"$GAME_ID"'","name":"Bot2","position":"EAST","difficulty":"random"}') || fail "add_bot as non-host request failed"

ADD_BOT_NON_HOST_SUCCESS=$(json_field "$ADD_BOT_NON_HOST" '.success')
[[ "$ADD_BOT_NON_HOST_SUCCESS" == "false" ]] || fail "non-host should not be able to add bot"
pass "non-host add_bot rejected"

# 8) Cross-game token binding must fail
CREATE_RESP_2=$(curl -sS -X POST "$BASE/api/create_room") || fail "create_room (other game) failed"
OTHER_GAME=$(json_field "$CREATE_RESP_2" '.game_id')

CROSS_GAME=$(curl -sS -X POST "$BASE/api/play" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ALICE_TOKEN" \
  -d '{"game_id":"'"$OTHER_GAME"'","card":"1"}') || fail "cross-game play request failed"

CROSS_GAME_SUCCESS=$(json_field "$CROSS_GAME" '.success')
[[ "$CROSS_GAME_SUCCESS" == "false" ]] || fail "cross-game token should be rejected"
pass "cross-game token binding enforced"

echo ""
echo "All Phase B auth checks passed."
