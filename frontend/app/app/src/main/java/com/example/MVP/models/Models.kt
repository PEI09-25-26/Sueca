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
    val phase: String,
    @SerializedName("current_player") val currentPlayer: String?,
    @SerializedName("player_count") val playerCount: Int,
    val players: List<GamePlayer>,
    val trump: String?,
    @SerializedName("trump_suit") val trumpSuit: String?,
    @SerializedName("round_plays") val roundPlays: List<RoundPlay>,
    val teams: Teams,
    @SerializedName("team_scores") val teamScores: TeamScores?,
    @SerializedName("north_player") val northPlayer: String?,
    @SerializedName("west_player") val westPlayer: String?,
    @SerializedName("current_round") val currentRound: Int,
    @SerializedName("round_suit") val roundSuit: String?,
    @SerializedName("game_started") val gameStarted: Boolean,
    val scores: Map<String, Int>?
)

data class GamePlayer(
    val name: String,
    val position: String,
    @SerializedName("cards_left") val cardsLeft: Int
)

data class RoundPlay(
    val player: String,
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
    val player: String,
    val card: String
)

data class CutDeckRequest(
    val player: String,
    val index: Int
)

data class SelectTrumpRequest(
    val player: String,
    val choice: String // "top" or "bottom"
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
    val name: String
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
    val roomId: String,
    val playerId: String
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
