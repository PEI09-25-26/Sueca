package com.example.MVP.models

import com.google.gson.JsonObject
import com.google.gson.annotations.SerializedName

// ============ Auth Models ============
data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String
)

data class RegisterResponse(
    val success: Boolean,
    val message: String,
    @SerializedName("verificationRequired") val verificationRequired: Boolean? = null,
    @SerializedName("verificationId") val verificationId: String? = null
)

data class VerifyEmailRequest(
    @SerializedName("verification_id") val verificationId: String,
    val code: String
)

data class LoginRequest(
    val username: String,
    val password: String
)

data class UpdateUserRequest(
    val description: String? = null,
    val photoURL: String? = null,
    val bannerURL: String? = null,
    val privacy: String? = null,
    val status: String? = null,
    val password: String? = null
)

data class LogoutRequest(
    val uid: String
)

data class DeleteAccountRequest(
    val uid: String
)

data class ConfirmDeleteAccountRequest(
    val uid: String,
    val code: String
)

data class AuthResponse(
    val success: Boolean,
    val message: String,
    val user: UserData? = null,
    val token: String? = null
)

data class UserResponse(
    val success: Boolean,
    val message: String? = null,
    val user: UserData? = null
)

data class UserData(
    val uid: String,
    val username: String,
    val email: String,
    @SerializedName("emailVerified") val emailVerified: Boolean,
    val description: String,
    val photoURL: String,
    val bannerURL: String,
    @SerializedName("createdAt") val createdAt: String,
    @SerializedName("updatedAt") val updatedAt: String,
    @SerializedName("lastLoginAt") val lastLoginAt: String?,
    val privacy: String,
    @SerializedName("friendsCount") val friendsCount: Int,
    val status: String,
    @SerializedName("friendCode") val friendCode: String? = null
)

// ============ Friend Models ============
data class SendFriendRequestRequest(
    @SerializedName("from_uid") val fromUid: String,
    @SerializedName("to_uid") val toUid: String
)

data class SendFriendRequestByUsernameRequest(
    @SerializedName("from_uid") val fromUid: String,
    @SerializedName("to_username") val toUsername: String
)

data class AcceptFriendRequestRequest(
    @SerializedName("request_id") val requestId: String
)

data class DeclineFriendRequestRequest(
    @SerializedName("request_id") val requestId: String
)

data class FriendRequestResponse(
    val success: Boolean,
    val message: String,
    val request: FriendRequest? = null
)

data class FriendRequest(
    val id: String,
    @SerializedName("from_uid") val fromUid: String,
    @SerializedName("to_uid") val toUid: String,
    val status: String,
    @SerializedName("createdAt") val createdAt: String,
    @SerializedName("updatedAt") val updatedAt: String
)

data class FriendCodeResponse(
    val code: String,
    @SerializedName("expires_at") val expiresAt: String? = null
)

data class FriendsListResponse(
    val success: Boolean,
    val message: String? = null,
    val friends: List<UserData>? = null,
    val count: Int? = null
)

data class IncomingFriendRequestData(
    val id: String,
    @SerializedName("from_uid") val fromUid: String,
    @SerializedName("to_uid") val toUid: String,
    @SerializedName("from_username") val fromUsername: String,
    val status: String,
    @SerializedName("createdAt") val createdAt: String,
    @SerializedName("updatedAt") val updatedAt: String
)

data class FriendRequestsListResponse(
    val success: Boolean,
    val message: String? = null,
    val requests: List<IncomingFriendRequestData>? = null,
    val count: Int? = null
)

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
    @SerializedName("creator_id") val creatorId: String? = null,
    @SerializedName("is_public") val isPublic: Boolean? = null,
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

data class RoomVisibilityRequest(
    @SerializedName("player_id") val playerId: String,
    @SerializedName("game_id") val gameId: String,
    @SerializedName("is_public") val isPublic: Boolean
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

data class RoomSummary(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_count") val playerCount: Int,
    @SerializedName("max_players") val maxPlayers: Int,
    val players: List<String> = emptyList(),
    val phase: String? = null,
    @SerializedName("is_public") val isPublic: Boolean? = null,
    @SerializedName("game_started") val gameStarted: Boolean = false
)

data class RoomsResponse(
    val success: Boolean,
    val rooms: List<RoomSummary>? = null,
    @SerializedName("total_rooms") val totalRooms: Int = 0,
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
