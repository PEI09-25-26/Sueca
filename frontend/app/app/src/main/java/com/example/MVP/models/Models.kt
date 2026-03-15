package com.example.MVP.models

import com.google.gson.annotations.SerializedName

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
    @SerializedName("current_round") val currentRound: Int,
    @SerializedName("round_suit") val roundSuit: String?,
    @SerializedName("game_started") val gameStarted: Boolean,
    val scores: Map<String, Int>?,
    @SerializedName("available_slots") val availableSlots: List<LobbySlot>? = emptyList()
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
