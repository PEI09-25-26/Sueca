#!/usr/bin/env bash
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

# 9) Get own hand with token-only endpoint.
# Expected: success=true and hand array returned for token owner.
curl -sS "$BASE/api/hand?game_id=$GAME_ID" -H "Authorization: Bearer $ALICE_TOKEN" | jq '.'

# 10) Access another player's hand with mismatched token.
# Expected: success=false, message similar to "Token does not match requested player hand".
curl -sS "$BASE/api/hand/$BOB_ID?game_id=$GAME_ID" -H "Authorization: Bearer $ALICE_TOKEN" | jq '.'

# 11) Protected play with wrong auth scheme.
# Expected: success=false, message similar to "Invalid authorization header format".
curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Token $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","card":"1"}' | jq '.'

# 12) Protected play with valid token.
# Expected: NO auth error; may still fail with game rule message (for example "Not your turn").
curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","card":"1"}' | jq '.'

# 13) Host-only add_bot with host token.
# Expected: success=true (message may be "Bot ... is joining...").
curl -sS -X POST "$BASE/api/add_bot" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","name":"Bot1","position":"SOUTH","difficulty":"random"}' | jq '.'

# 14) Host-only add_bot with non-host token.
# Expected: success=false, message similar to "Only room creator can add bots".
curl -sS -X POST "$BASE/api/add_bot" -H "Content-Type: application/json" -H "Authorization: Bearer $BOB_TOKEN" -d '{"game_id":"'"$GAME_ID"'","name":"Bot2","position":"EAST","difficulty":"random"}' | jq '.'

# 15) Change position using Bob token.
# Expected: auth passes; success depends on slot availability/game phase.
curl -sS -X POST "$BASE/api/change_position" -H "Content-Type: application/json" -H "Authorization: Bearer $BOB_TOKEN" -d '{"game_id":"'"$GAME_ID"'","position":"EAST"}' | jq '.'

# 16) Remove Bob using host token.
# Expected: auth passes and host check passes; success depends on game phase.
curl -sS -X POST "$BASE/api/remove_player" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'","target_id":"'"$BOB_ID"'"}' | jq '.'

# 17) Start game as host.
# Expected: auth passes and host check passes; success depends on room state.
curl -sS -X POST "$BASE/api/start" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}' | jq '.'

# 18) Reset game as host.
# Expected: success=true if host token is valid.
curl -sS -X POST "$BASE/api/reset" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$GAME_ID"'"}' | jq '.'

# 19) Rematch as host.
# Expected: auth passes and host check passes; success depends on room state.
curl -sS -X POST "$BASE/api/room/$GAME_ID/rematch" -H "Authorization: Bearer $ALICE_TOKEN" | jq '.'

# 20) Cross-game token binding check.
# Expected: success=false, message similar to "Player not in this game".
OTHER_GAME=$(curl -sS -X POST "$BASE/api/create_room" | jq -r '.game_id'); echo "OTHER_GAME=$OTHER_GAME"; curl -sS -X POST "$BASE/api/play" -H "Content-Type: application/json" -H "Authorization: Bearer $ALICE_TOKEN" -d '{"game_id":"'"$OTHER_GAME"'","card":"1"}' | jq '.'

# 21) Final token sanity check.
# Expected: "ALICE TOKEN OK".
[ -n "$ALICE_TOKEN" ] && [ "$ALICE_TOKEN" != "null" ] && echo "ALICE TOKEN OK" || echo "ALICE TOKEN INVALID"
