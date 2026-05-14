package com.example.MVP.network

import com.example.MVP.models.AddBotRequest
import com.example.MVP.models.AddBotResponse
import com.example.MVP.models.CreateRoomRequest
import com.example.MVP.models.CreateRoomResponse
import com.example.MVP.models.CutDeckRequest
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.GatewayCommandRequest
import com.example.MVP.models.GatewayEnvelope
import com.example.MVP.models.GenericResponse
import com.example.MVP.models.HandResponse
import com.example.MVP.models.JoinGameRequest
import com.example.MVP.models.JoinGameResponse
import com.example.MVP.models.MatchPointsResponse
import com.example.MVP.models.LeaveRoomRequest
import com.example.MVP.models.RemoveParticipantRequest
import com.example.MVP.models.RoomModeRequest
import com.example.MVP.models.SelectTrumpRequest
import com.example.MVP.models.PlayRequest
import com.example.MVP.GameSessionManager
import com.google.gson.Gson
import com.google.gson.JsonObject

object GatewayClient {
    private val gson = Gson()

    suspend fun setRoomMode(gameId: String, mode: String) {
        runCatching {
            RetrofitClient.api.setRoomMode(gameId, RoomModeRequest(mode))
        }
    }

    suspend fun getRoomMode(gameId: String): String? {
        return runCatching {
            RetrofitClient.api.getRoomMode(gameId).mode
        }.getOrNull()
    }

    suspend fun getStatus(gameId: String?, mode: String? = null): GameStatusResponse? {
        val envelope = RetrofitClient.api.routeQuery(
            queryPath = "status",
            gameId = gameId,
            mode = mode
        )

        if (!envelope.success) return null
        return parseJson(envelope.response, GameStatusResponse::class.java)
    }

    suspend fun createRoom(playerName: String): CreateRoomResponse {
        val response = RetrofitClient.api.createRoomV2(CreateRoomRequest(name = playerName))
        if (response.success) {
            val gameId = response.gameId ?: response.roomId
            if (!gameId.isNullOrBlank()) {
                GameSessionManager.saveToken(gameId, response.token)
            }
        }
        return response
    }

    suspend fun joinGame(request: JoinGameRequest): JoinGameResponse {
        val payload = mutableMapOf<String, Any?>(
            "name" to request.name,
            "position" to request.position
        )
        request.gameId?.let { payload["game_id"] = it }

        val envelope = command("join", gameId = request.gameId, mode = null, payload = payload)
        val response = envelope.response

        val joinResponse = JoinGameResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope),
            gameId = response.string("game_id") ?: request.gameId,
            playerId = response.string("player_id"),
            token = response.string("token")
        )
        if (joinResponse.success) {
            joinResponse.gameId?.let { gid ->
                GameSessionManager.saveToken(gid, joinResponse.token)
            }
        }
        return joinResponse
    }

    suspend fun addBot(request: AddBotRequest): AddBotResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "position" to request.position,
            "difficulty" to request.difficulty,
            "name" to request.name
        )

        val envelope = command("add_bot", gameId = request.gameId, mode = null, payload = payload)
        val response = envelope.response

        return AddBotResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope),
            gameId = response.string("game_id") ?: request.gameId,
            playerId = response.string("player_id")
        )
    }

    suspend fun changePosition(playerId: String, gameId: String, position: String): GenericResponse {
        val payload = mapOf(
            "game_id" to gameId,
            "position" to position
        )

        val envelope = command("change_position", gameId = gameId, mode = null, payload = payload)
        val response = envelope.response

        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun removeParticipant(request: RemoveParticipantRequest): GenericResponse {
        val payload = mapOf(
            "target_id" to request.targetId,
            "game_id" to request.gameId
        )

        val envelope = command("the_council_has_decided_your_fate", gameId = request.gameId, mode = null, payload = payload)
        val response = envelope.response

        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun leaveRoom(gameId: String, playerId: String): GenericResponse {
        val response = RetrofitClient.api.leaveRoom(
            LeaveRoomRequest(
                gameId = gameId,
                playerId = playerId
            ),
            GameSessionManager.getAuthHeader(gameId)
        )
        if (response.success) {
            GameSessionManager.clearToken(gameId)
        }

        return GenericResponse(
            success = response.success,
            message = response.message ?: "Saida da sala processada."
        )
    }

    suspend fun updateRoomVisibility(playerId: String, gameId: String, isPublic: Boolean): GenericResponse {
        val payload = mapOf(
            "player_id" to playerId,
            "game_id" to gameId,
            "is_public" to isPublic
        )

        val envelope = command("room_visibility", gameId = gameId, mode = null, payload = payload)
        val response = envelope.response

        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun cutDeck(request: CutDeckRequest): GenericResponse {
        val payload = mapOf(
            "index" to request.index,
            "game_id" to request.gameId
        )

        val envelope = command("cut_deck", gameId = request.gameId, mode = null, payload = payload)
        val response = envelope.response

        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun selectTrump(request: SelectTrumpRequest): GenericResponse {
        val payload = mapOf(
            "choice" to request.choice,
            "game_id" to request.gameId
        )

        val envelope = command("select_trump", gameId = request.gameId, mode = null, payload = payload)
        val response = envelope.response

        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun playCard(request: PlayRequest): GenericResponse {
        val payload = mapOf(
            "card" to request.card,
            "game_id" to request.gameId
        )

        val envelope = command("play", gameId = request.gameId, mode = null, payload = payload)
        val response = envelope.response

        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun startGame(gameId: String): GenericResponse {
        val payload = mapOf("game_id" to gameId)
        val envelope = command("start", gameId = gameId, mode = null, payload = payload)
        val response = envelope.response
        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun getHand(playerId: String, gameId: String?): HandResponse {
        val envelope = RetrofitClient.api.routeQuery(
            queryPath = "hand/$playerId",
            gameId = gameId,
            mode = null,
            token = GameSessionManager.getAuthHeader(gameId)
        )

        if (!envelope.success) {
            return HandResponse(false, emptyList())
        }

        val response = envelope.response
        val success = response.bool("success") ?: false
        val hand = response.arrayStrings("hand")

        return HandResponse(success, hand)
    }

    suspend fun requestRematch(gameId: String): GenericResponse {
        val envelope = command("room/$gameId/rematch", gameId = gameId, mode = null, payload = emptyMap())
        val response = envelope.response

        return GenericResponse(
            success = response.bool("success") ?: false,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun getMatchPoints(gameId: String): MatchPointsResponse {
        val envelope = RetrofitClient.api.routeQuery(
            queryPath = "room/$gameId/match_points",
            gameId = gameId,
            mode = null
        )

        if (!envelope.success) {
            return MatchPointsResponse(success = false, message = fallbackMessage(envelope))
        }

        val payload = envelope.response ?: return MatchPointsResponse(success = false, message = "Missing payload")
        return parseJson(payload, MatchPointsResponse::class.java)
            ?: MatchPointsResponse(success = false, message = "Invalid payload")
    }

    private suspend fun command(command: String, gameId: String?, mode: String?, payload: Map<String, Any?>): GatewayEnvelope {
        return RetrofitClient.api.routeCommand(
            command = command,
            request = GatewayCommandRequest(
                gameId = gameId,
                mode = mode,
                payload = payload
            ),
            token = GameSessionManager.getAuthHeader(gameId)
        )
    }

    private fun fallbackMessage(envelope: GatewayEnvelope): String {
        envelope.message?.takeIf { it.isNotBlank() }?.let { return it }

        val response = envelope.response
        if (response != null) {
            response.string("message")?.let { return it }
            response.string("detail")?.let { return it }

            val nested = response.objectOrNull("response")
            if (nested != null) {
                nested.string("message")?.let { return it }
                nested.string("detail")?.let { return it }
            }
        }

        return "Unknown error"
    }

    private fun <T> parseJson(json: JsonObject?, clazz: Class<T>): T? {
        if (json == null) return null
        return runCatching { gson.fromJson(json, clazz) }.getOrNull()
    }

    private fun JsonObject?.bool(key: String): Boolean? {
        if (this == null || !has(key)) return null
        val el = get(key)
        return if (el.isJsonPrimitive) el.asBoolean else null
    }

    private fun JsonObject?.string(key: String): String? {
        if (this == null || !has(key)) return null
        val el = get(key)
        return if (el.isJsonPrimitive) el.asString else null
    }

    private fun JsonObject?.arrayStrings(key: String): List<String> {
        if (this == null || !has(key)) return emptyList()
        val el = get(key)
        if (!el.isJsonArray) return emptyList()
        return el.asJsonArray.mapNotNull { item ->
            if (item.isJsonPrimitive) item.asString else null
        }
    }

    private fun JsonObject.objectOrNull(key: String): JsonObject? {
        if (!has(key)) return null
        val el = get(key)
        return if (el.isJsonObject) el.asJsonObject else null
    }
}
