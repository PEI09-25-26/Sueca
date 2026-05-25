package com.example.MVP.network

import com.example.MVP.models.AddBotRequest
import com.example.MVP.models.AddBotResponse
import com.example.MVP.models.CreateRoomResponse
import com.example.MVP.models.DeclineInviteRequest
import com.example.MVP.models.CutDeckRequest
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.GatewayCommandRequest
import com.example.MVP.models.GatewayEnvelope
import com.example.MVP.models.GenericResponse
import com.example.MVP.models.HandResponse
import com.example.MVP.models.HybridConfirmCaptureRequest
import com.example.MVP.models.HybridConfirmCaptureResponse
import com.example.MVP.models.HybridForceRenunciaRequest
import com.example.MVP.models.HybridConfirmTrumpCaptureRequest
import com.example.MVP.models.HybridConfirmTrumpCaptureResponse
import com.example.MVP.models.HybridDealRecognizeRequest
import com.example.MVP.models.HybridDealRecognizeResponse
import com.example.MVP.models.HybridDealResetRequest
import com.example.MVP.models.HybridPendingResponse
import com.example.MVP.models.HybridRegisterPlayerRequest
import com.example.MVP.models.HybridSelectCardRequest
import com.example.MVP.models.HybridStateResponse
import com.example.MVP.models.JoinGameRequest
import com.example.MVP.models.JoinGameResponse
import com.example.MVP.models.MatchPointsResponse
import com.example.MVP.models.LeaveRoomRequest
import com.example.MVP.models.RemoveParticipantRequest
import com.example.MVP.models.RoomModeRequest
import com.example.MVP.models.SelectTrumpRequest
import com.example.MVP.models.UndoMoveRequest
import com.example.MVP.models.UndoMoveResponse
import com.example.MVP.models.PlayRequest
import com.example.MVP.AuthManager
import com.example.MVP.GameSessionManager
import com.google.gson.Gson
import com.google.gson.JsonObject

object GatewayClient {
    private val gson = Gson()

    suspend fun setRoomMode(gameId: String, mode: String) {
        runCatching {
            RetrofitClient.api.setRoomMode(
                gameId,
                RoomModeRequest(mode),
                GameSessionManager.getAuthHeader(gameId)
            )
        }
    }

    suspend fun getRoomMode(gameId: String): String? {
        return runCatching {
            RetrofitClient.api.getRoomMode(
                gameId,
                GameSessionManager.getAuthHeader(gameId)
            ).mode
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

    suspend fun createRoom(playerName: String, mode: String? = null): CreateRoomResponse {
        // Create an empty room through the gateway so we can handle the wrapped response format.
        val envelope = command(
            command = "create_room",
            gameId = null,
            mode = mode,
            payload = mapOf("name" to playerName, "mode" to mode)
        )

        val response = envelope.response
        val success = response.bool("success") ?: envelope.success
        val gameId = response.string("game_id") ?: response.string("room_id")
        val playerId = response.string("player_id")
        val token = response.string("token")

        if (success && !gameId.isNullOrBlank()) {
            GameSessionManager.saveToken(gameId, token)
        }

        return CreateRoomResponse(
            success = success,
            roomId = gameId,
            playerId = playerId,
            gameId = gameId,
            token = token,
            message = response.string("message") ?: fallbackMessage(envelope)
        )
    }

    suspend fun joinGame(request: JoinGameRequest, authHeader: String? = null, mode: String? = null): JoinGameResponse {
        val payload = mutableMapOf<String, Any?>(
            "name" to request.name,
            "position" to request.position,
            "mode" to mode
        )
        request.gameId?.let { payload["game_id"] = it }

        val envelope = command("join", gameId = request.gameId, mode = mode, payload = payload, authHeader = authHeader)
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

    suspend fun declineInvite(gameId: String, position: String): GenericResponse {
        val token = GameSessionManager.getAuthHeader(gameId) ?: AuthManager.getAuthHeader()
        if (token.isNullOrBlank()) {
            return GenericResponse(success = false, message = "No auth token")
        }

        return RetrofitClient.api.declineInvite(
            gameId = gameId,
            request = DeclineInviteRequest(position = position),
            token = token
        )
    }

    suspend fun addBot(request: AddBotRequest): AddBotResponse {
        val payload = mapOf(
            "player_id" to request.playerId,
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
            "player_id" to playerId,
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
            "actor_id" to request.actorId,
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
            "player_id" to request.playerId,
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
            "player_id" to request.playerId,
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
            "player_id" to request.playerId,
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

    suspend fun hybridRegisterPlayer(request: HybridRegisterPlayerRequest): HybridStateResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "player_id" to request.playerId,
            "role" to request.role,
            "is_host" to request.isHost
        )

        val envelope = command("hybrid/register_player", gameId = request.gameId, mode = "hybrid", payload = payload)
        return requireParsed(envelope, HybridStateResponse::class.java)
    }

    suspend fun hybridState(gameId: String): HybridStateResponse {
        val envelope = RetrofitClient.api.routeQuery(
            queryPath = "hybrid/state",
            gameId = gameId,
            mode = "hybrid",
            token = GameSessionManager.getAuthHeader(gameId)
        )
        return requireParsed(envelope, HybridStateResponse::class.java)
    }

    suspend fun hybridDealReset(request: HybridDealResetRequest): HybridStateResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "player_id" to request.playerId,
            "cards_per_virtual" to request.cardsPerVirtual
        )

        val envelope = command("hybrid/deal/reset", gameId = request.gameId, mode = "hybrid", payload = payload)
        return requireParsed(envelope, HybridStateResponse::class.java)
    }

    suspend fun hybridDealFinalize(request: com.example.MVP.models.HybridDealFinalizeRequest): HybridStateResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "player_id" to request.playerId
        )

        val envelope = command("hybrid/deal/finalize", gameId = request.gameId, mode = "hybrid", payload = payload)
        return requireParsed(envelope, HybridStateResponse::class.java)
    }

    suspend fun hybridDealRecognize(request: HybridDealRecognizeRequest): HybridDealRecognizeResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "player_id" to request.playerId,
            "frame_base64" to request.frameBase64,
            "target_player_id" to request.targetPlayerId
        )

        val envelope = command("hybrid/deal/recognize", gameId = request.gameId, mode = "hybrid", payload = payload)
        return requireParsed(envelope, HybridDealRecognizeResponse::class.java)
    }

    suspend fun hybridSelectCard(request: HybridSelectCardRequest): HybridStateResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "player_id" to request.playerId,
            "card" to request.card
        )

        val envelope = command("hybrid/virtual/select_card", gameId = request.gameId, mode = "hybrid", payload = payload)
        return requireParsed(envelope, HybridStateResponse::class.java)
    }

    suspend fun hybridPendingPlay(gameId: String): HybridPendingResponse {
        val envelope = RetrofitClient.api.routeQuery(
            queryPath = "hybrid/pending_play",
            gameId = gameId,
            mode = "hybrid",
            token = GameSessionManager.getAuthHeader(gameId)
        )

        return requireParsed(envelope, HybridPendingResponse::class.java)
    }

    suspend fun hybridConfirmCapture(request: HybridConfirmCaptureRequest): HybridConfirmCaptureResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "player_id" to request.playerId,
            "host_player_id" to request.hostPlayerId,
            "frame_base64" to request.frameBase64
        )

        val envelope = command("hybrid/play/confirm_capture", gameId = request.gameId, mode = "hybrid", payload = payload)
        
        // Don't use requireParsed if it's a renúncia warning (success will be false, but response has data)
        val responseJson = envelope.response
        if (responseJson?.bool("is_renuncia_warning") == true) {
            return parseJson(responseJson, HybridConfirmCaptureResponse::class.java) 
                ?: throw IllegalStateException("Failed to parse renúncia warning response")
        }
        
        return requireParsed(envelope, HybridConfirmCaptureResponse::class.java)
    }

    suspend fun hybridForceRenuncia(request: HybridForceRenunciaRequest): HybridStateResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "player_id" to request.playerId,
            "card_id" to request.cardId
        )

        val envelope = command("hybrid/play/force_renuncia", gameId = request.gameId, mode = "hybrid", payload = payload)
        return requireParsed(envelope, HybridStateResponse::class.java)
    }

    suspend fun hybridConfirmTrumpCapture(request: HybridConfirmTrumpCaptureRequest): HybridConfirmTrumpCaptureResponse {
        val payload = mapOf(
            "game_id" to request.gameId,
            "host_player_id" to request.hostPlayerId,
            "frame_base64" to request.frameBase64
        )

        val envelope = command("hybrid/trump/confirm_capture", gameId = request.gameId, mode = "hybrid", payload = payload)
        return requireParsed(envelope, HybridConfirmTrumpCaptureResponse::class.java)
    }

    suspend fun undoMove(request: UndoMoveRequest, mode: String = "virtual"): UndoMoveResponse {
        val payload = mapOf("game_id" to request.gameId)
        val cmdStr = if (mode == "physical") "play/undo" else "hybrid/play/undo"
        val envelope = command(cmdStr, gameId = request.gameId, mode = mode, payload = payload)
        val response = envelope.response

        return UndoMoveResponse(
            success = response?.bool("success") ?: false,
            message = response?.string("message") ?: fallbackMessage(envelope),
            state = parseJson(response?.objectOrNull("state"), com.example.MVP.models.HybridRuntimeState::class.java),
            gameState = parseJson(response?.objectOrNull("game_state"), com.example.MVP.models.GameStatusResponse::class.java)
        )
    }

    private suspend fun command(
        command: String,
        gameId: String?,
        mode: String?,
        payload: Map<String, Any?>,
        authHeader: String? = null,
    ): GatewayEnvelope {
        return RetrofitClient.api.routeCommand(
            command = command,
            request = GatewayCommandRequest(
                gameId = gameId,
                mode = mode,
                payload = payload
            ),
            token = authHeader ?: GameSessionManager.getAuthHeader(gameId)
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

    private fun <T> requireParsed(envelope: GatewayEnvelope, clazz: Class<T>): T {
        val parsed = parseJson(envelope.response, clazz)
        if (parsed != null) {
            return parsed
        }
        throw IllegalStateException(fallbackMessage(envelope))
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
