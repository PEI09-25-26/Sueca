package com.example.MVP.models

import com.google.gson.annotations.SerializedName
import com.google.gson.JsonObject

// ============ Card Data ============
data class Card(
    val id: String,
    val suit: String,
    val value: String
)

// ============ Game Status Response ============
data class GameStatusResponse(
    @SerializedName("game_id") val gameId: String?,
    val phase: String,
    @SerializedName("current_player") val currentPlayer: String?,
    @SerializedName("current_player_id") val currentPlayerId: String?,
    @SerializedName("player_count") val playerCount: Int,
    val players: List<GamePlayer>,
    val trump: String?,
    @SerializedName("trump_suit") val trumpSuit: String?,
    @SerializedName("round_plays") val roundPlays: List<RoundPlay>,
    val teams: Teams,
    @SerializedName("team_scores") val teamScores: TeamScores?,
    @SerializedName("north_player") val northPlayer: String?,
    @SerializedName("north_player_id") val northPlayerId: String?,
    @SerializedName("west_player") val westPlayer: String?,
    @SerializedName("west_player_id") val westPlayerId: String?,
    @SerializedName("trump_selector_player") val trumpSelectorPlayer: String? = null,
    @SerializedName("trump_selector_player_id") val trumpSelectorPlayerId: String? = null,
    @SerializedName("trump_selector_position") val trumpSelectorPosition: String? = null,
    @SerializedName("current_round") val currentRound: Int,
    @SerializedName("round_suit") val roundSuit: String?,
    @SerializedName("game_started") val gameStarted: Boolean,
    val scores: Map<String, Int>?,
    @SerializedName("available_slots") val availableSlots: List<LobbySlot>? = emptyList(),
    @SerializedName("match_points") val matchPoints: MatchPoints? = null
)

data class GamePlayer(
    val id: String?,
    val name: String,
    val position: String,
    @SerializedName("cards_left") val cardsLeft: Int
)

data class LobbySlot(
    val position: String,
    val team: String,
    @SerializedName("team_label") val teamLabel: String
)

data class RoundPlay(
    @SerializedName("player_name") val playerName: String,
    val card: String,
    val position: String?
)

data class Teams(
    val team1: List<String>,
    val team2: List<String>
)

data class TeamScores(
    val team1: Int,
    val team2: Int
)

data class MatchPoints(
    val team1: Int,
    val team2: Int
)

data class MatchPointsPayload(
    val points: MatchPoints,
    @SerializedName("matches_played") val matchesPlayed: Int
)

data class MatchPointsResponse(
    val success: Boolean,
    val message: String? = null,
    val points: MatchPoints? = null,
    @SerializedName("matches_played") val matchesPlayed: Int? = null
)

// ============ Requests ============
data class PlayRequest(
    @SerializedName("player_id") val playerId: String,
    val card: String,
    @SerializedName("game_id") val gameId: String? = null
)

data class CutDeckRequest(
    @SerializedName("player_id") val playerId: String,
    val index: Int,
    @SerializedName("game_id") val gameId: String? = null
)

data class SelectTrumpRequest(
    @SerializedName("player_id") val playerId: String,
    val choice: String, // "top" or "bottom"
    @SerializedName("game_id") val gameId: String? = null
)

// ============ Responses ============
data class GenericResponse(
    val success: Boolean,
    val message: String?
)

data class JoinResponse(
    val success: Boolean,
    val message: String?
)

data class HandResponse(
    val success: Boolean,
    val hand: List<String>
)

// ============ Room-based models (for RoomActivity) ============
data class Player(
    val id: String,
    val name: String,
    val position: String? = null
)

data class RoomState(
    val roomId: String,
    val players: List<Player>,
    val gameStarted: Boolean,
    val gameState: GameStatusResponse?
)

data class CreateRoomRequest(
    val playerName: String
)

data class CreateRoomResponse(
    val success: Boolean,
    @SerializedName("room_id") val roomId: String? = null,
    @SerializedName("player_id") val playerId: String? = null,
    @SerializedName("game_id") val gameId: String? = null,
    val message: String? = null
)

data class JoinRoomRequest(
    val playerName: String,
    val roomId: String
)

data class JoinRoomResponse(
    val success: Boolean,
    val roomId: String,
    val playerId: String
)

data class StartGameRequest(
    val playerName: String?,
    val roomId: String?
)

data class StartGameResponse(
    val success: Boolean,
    val message: String?,
    val gameId: String?
)

data class JoinGameRequest(
    val name: String,
    @SerializedName("game_id") val gameId: String? = null,
    val position: String? = null
)

data class JoinGameResponse(
    val success: Boolean,
    val message: String?,
    @SerializedName("game_id") val gameId: String?,
    @SerializedName("player_id") val playerId: String?
)

data class AddBotRequest(
    @SerializedName("player_id") val playerId: String,
    @SerializedName("game_id") val gameId: String,
    val position: String,
    val difficulty: String,
    val name: String
)

data class AddBotResponse(
    val success: Boolean,
    val message: String?,
    @SerializedName("game_id") val gameId: String?,
    @SerializedName("player_id") val playerId: String?
)

data class RemoveParticipantRequest(
    @SerializedName("actor_id") val actorId: String,
    @SerializedName("target_id") val targetId: String,
    @SerializedName("game_id") val gameId: String
)

// ============ Hybrid Mode Models ============
data class HybridSessionResetRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("target_count") val targetCount: Int = 10
)

data class HybridRecognizeRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("frame_base64") val frameBase64: String,
    @SerializedName("target_count") val targetCount: Int = 10
)

data class HybridCardPayload(
    val id: Int,
    val rank: String,
    val suit: String,
    @SerializedName("suit_symbol") val suitSymbol: String,
    @SerializedName("drawable_key") val drawableKey: String,
    val display: String
)

data class HybridSessionStatusResponse(
    val success: Boolean,
    @SerializedName("game_id") val gameId: String,
    @SerializedName("confirmed_count") val confirmedCount: Int,
    @SerializedName("target_count") val targetCount: Int,
    val done: Boolean,
    val cards: List<HybridCardPayload>
)

data class HybridRecognizeResponse(
    val success: Boolean,
    val recognized: Boolean = false,
    val confirmed: Boolean = false,
    val message: String? = null,
    val card: HybridCardPayload? = null,
    val streak: Int? = null,
    @SerializedName("required_streak") val requiredStreak: Int? = null,
    @SerializedName("game_id") val gameId: String,
    @SerializedName("confirmed_count") val confirmedCount: Int,
    @SerializedName("target_count") val targetCount: Int,
    val done: Boolean,
    val cards: List<HybridCardPayload>
)

data class HybridRegisterPlayerRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String,
    val role: String,
    @SerializedName("is_host") val isHost: Boolean
)

data class HybridPlayerRuntime(
    @SerializedName("player_id") val playerId: String,
    @SerializedName("player_name") val playerName: String,
    val position: String,
    val cards: List<Int>,
    @SerializedName("cards_count") val cardsCount: Int
)

data class HybridPendingPlay(
    @SerializedName("player_id") val playerId: String,
    @SerializedName("player_name") val playerName: String,
    val position: String,
    @SerializedName("card_id") val cardId: Int
)

data class HybridRuntimeState(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("host_player_id") val hostPlayerId: String?,
    @SerializedName("cards_per_virtual") val cardsPerVirtual: Int,
    @SerializedName("virtual_order") val virtualOrder: List<String>,
    @SerializedName("player_roles") val playerRoles: Map<String, String>,
    @SerializedName("virtual_players") val virtualPlayers: List<HybridPlayerRuntime>,
    @SerializedName("pending_virtual_play") val pendingVirtualPlay: HybridPendingPlay?,
    @SerializedName("deal_done") val dealDone: Boolean
)

data class HybridStateResponse(
    val success: Boolean,
    val state: HybridRuntimeState,
    val message: String? = null
)

data class HybridDealResetRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String,
    @SerializedName("cards_per_virtual") val cardsPerVirtual: Int = 10
)

data class HybridDealRecognizeRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String,
    @SerializedName("frame_base64") val frameBase64: String,
    @SerializedName("target_player_id") val targetPlayerId: String? = null
)

data class HybridDealRecognizeResponse(
    val success: Boolean,
    val recognized: Boolean,
    val confirmed: Boolean,
    val message: String,
    @SerializedName("target_player_id") val targetPlayerId: String? = null,
    val card: HybridCardPayload? = null,
    val state: HybridRuntimeState
)

data class HybridSelectCardRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String,
    val card: Int
)

data class HybridPendingResponse(
    val success: Boolean,
    val pending: HybridPendingPlay?,
    val state: HybridRuntimeState
)

data class HybridConfirmCaptureRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String,
    @SerializedName("host_player_id") val hostPlayerId: String? = null,
    @SerializedName("frame_base64") val frameBase64: String
)

data class HybridConfirmCaptureResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("captured_card_id") val capturedCardId: Int? = null,
    @SerializedName("captured_display") val capturedDisplay: String? = null,
    val state: HybridRuntimeState? = null,
    @SerializedName("game_state") val gameState: GameStatusResponse? = null
)

data class HybridConfirmTrumpCaptureRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("host_player_id") val hostPlayerId: String,
    @SerializedName("frame_base64") val frameBase64: String
)

data class HybridConfirmTrumpCaptureResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("captured_card_id") val capturedCardId: Int? = null,
    @SerializedName("captured_display") val capturedDisplay: String? = null,
    val state: HybridRuntimeState? = null,
    @SerializedName("game_state") val gameState: GameStatusResponse? = null
)

data class RoomModeRequest(
    val mode: String
)

data class GatewayCommandRequest(
    @SerializedName("game_id") val gameId: String? = null,
    val mode: String? = null,
    val payload: Map<String, Any?> = emptyMap()
)

data class GatewayEnvelope(
    val success: Boolean,
    @SerializedName("http_success") val httpSuccess: Boolean? = null,
    @SerializedName("http_status") val httpStatus: Int? = null,
    val mode: String? = null,
    val target: String? = null,
    val message: String? = null,
    val response: JsonObject? = null
)
