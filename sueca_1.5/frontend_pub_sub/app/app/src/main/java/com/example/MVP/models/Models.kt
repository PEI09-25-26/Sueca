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
    @SerializedName("verification_id") val verificationId: String,
    val code: String
)

data class AuthResponse(
    val success: Boolean,
    val message: String,
    val user: UserData? = null,
    val token: String? = null
)

data class RecoverPasswordResponse(
    val success: Boolean,
    val message: String? = null,
    @SerializedName("verificationId") val verificationId: String? = null
)

data class ResetPasswordRequest(
    @SerializedName("verification_id") val verificationId: String,
    val code: String,
    @SerializedName("new_password") val newPassword: String
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
    @SerializedName("friendCode") val friendCode: String? = null,
    val stats: PlayerStatsData? = null
)

data class PlayerStatsData(
    @SerializedName("player_id") val playerId: String = "",
    @SerializedName("games_played") val gamesPlayed: Int = 0,
    val wins: Int = 0,
    val losses: Int = 0,
    val draws: Int = 0
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
    val message: String? = null,
    val requested: Boolean? = null,
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
    @SerializedName("match_points") val matchPoints: MatchPoints? = null,
    @SerializedName("dealer") val dealer: Int? = null,
    @SerializedName("trick_awaiting_confirmation") val trickAwaitingConfirmation: Boolean? = false,
    @SerializedName("round_resolving") val roundResolving: Boolean? = false
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
    val choice: Choice, // "top" or "bottom"
    @SerializedName("game_id") val gameId: String? = null
)

data class RoomVisibilityRequest(
    @SerializedName("player_id") val playerId: String,
    @SerializedName("game_id") val gameId: String,
    @SerializedName("is_public") val isPublic: Boolean
)

data class LeaveRoomRequest(
    @SerializedName("player_id") val playerId: String,
    @SerializedName("game_id") val gameId: String
)

// ============ Responses ============
data class GenericResponse(
    val success: Boolean,
    val message: String?,
    @SerializedName("verificationId") val verificationId: String? = null
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
    val name: String? = null,
    val position: String? = null
)

data class CreateRoomResponse(
    val success: Boolean,
    @SerializedName("room_id") val roomId: String? = null,
    @SerializedName("player_id") val playerId: String? = null,
    @SerializedName("game_id") val gameId: String? = null,
    val token: String? = null,
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
    @SerializedName("playerName") val playerName: String?,
    @SerializedName("room_id") val roomId: String?,
    val dealerId: Int? = null
)

data class StartGameResponse(
    val success: Boolean,
    val message: String?,
    @SerializedName("game_id") val gameId: String?,
    val token: String? = null,
    val gameState: GameStatusResponse? = null
)

data class CorrectCardRequest(
    val rank: String,
    val suit: String,
    @SerializedName("wrong_label") val wrongLabel: String? = null
)

data class CorrectCardResponse(
    val success: Boolean,
    val message: String?,
    @SerializedName("game_state") val gameState: GameStatusResponse? = null,
    @SerializedName("who_played") val whoPlayed: String? = null
)

data class JoinGameRequest(
    val name: String,
    @SerializedName("game_id") val gameId: String? = null,
    val position: Position? = null
)

data class JoinGameResponse(
    val success: Boolean,
    val message: String?,
    @SerializedName("game_id") val gameId: String?,
    @SerializedName("player_id") val playerId: String?,
    val token: String? = null
)

data class AddBotRequest(
    @SerializedName("player_id") val playerId: String,
    @SerializedName("game_id") val gameId: String,
    val position: Position,
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

// ============ Invitation Models ============

data class InviteRequest(
    @SerializedName("friend_uid") val friendUid: String,
    val position: String
)

data class DeclineInviteRequest(
    val position: String
)

data class GameInvite(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("inviter_name") val inviterName: String,
    val position: String,
    val timestamp: String
)

data class InvitesResponse(
    val success: Boolean,
    val invites: List<GameInvite>
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


enum class Position {
    @SerializedName("NORTH") NORTH,
    @SerializedName("SOUTH") SOUTH,
    @SerializedName("EAST") EAST,
    @SerializedName("WEST") WEST
}

enum class Choice {
    @SerializedName("top") TOP,
    @SerializedName("bottom") BOTTOM
}

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
    @SerializedName("pending_trump_side") val pendingTrumpSide: String? = null,
    @SerializedName("trump_selector_player_id") val trumpSelectorPlayerId: String? = null,
    @SerializedName("deal_done") val dealDone: Boolean
)

data class HybridStateResponse(
    val success: Boolean,
    val state: HybridRuntimeState,
    val message: String? = null,
    @SerializedName("game_state") val gameState: GameStatusResponse? = null
)

data class HybridDealResetRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String,
    @SerializedName("cards_per_virtual") val cardsPerVirtual: Int = 10
)

data class HybridDealFinalizeRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String
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
    val message: String? = null,
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
    val message: String? = null,
    @SerializedName("is_renuncia_warning") val isRenunciaWarning: Boolean? = null,
    @SerializedName("captured_card_id") val capturedCardId: Int? = null,
    @SerializedName("captured_display") val capturedDisplay: String? = null,
    val state: HybridRuntimeState? = null,
    @SerializedName("game_state") val gameState: GameStatusResponse? = null
)

data class HybridForceRenunciaRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("player_id") val playerId: String,
    @SerializedName("card_id") val cardId: Int
)

data class HybridConfirmTrumpCaptureRequest(
    @SerializedName("game_id") val gameId: String,
    @SerializedName("host_player_id") val hostPlayerId: String,
    @SerializedName("frame_base64") val frameBase64: String
)

data class HybridConfirmTrumpCaptureResponse(
    val success: Boolean,
    val message: String? = null,
    @SerializedName("captured_card_id") val capturedCardId: Int? = null,
    @SerializedName("captured_display") val capturedDisplay: String? = null,
    val state: HybridRuntimeState? = null,
    @SerializedName("game_state") val gameState: GameStatusResponse? = null
)

data class RoomModeRequest(
    val mode: String
)

data class RoomModeResponse(
    val success: Boolean,
    @SerializedName("game_id") val gameId: String? = null,
    val mode: String? = null
)

data class GameTokenRequest(
    @SerializedName("game_id") val gameId: String
)

data class GameTokenResponse(
    val token: String,
    @SerializedName("expires_at") val expiresAt: String
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

// ============ Undo (Play) Models ==========
data class UndoMoveRequest(
    @SerializedName("game_id") val gameId: String
)

data class UndoMoveResponse(
    val success: Boolean,
    val message: String? = null,
    val state: HybridRuntimeState? = null,
    @SerializedName("game_state") val gameState: GameStatusResponse? = null
)

// ============ Match History Models ============
data class GameStatsData(
    @SerializedName("team1_points") val team1Points: Int = 0,
    @SerializedName("team2_points") val team2Points: Int = 0,
    val winner: String? = null
)

data class RoundData(
    @SerializedName("card_played") val cardPlayed: String? = null,
    @SerializedName("cards_in_trick") val cardsInTrick: List<String>? = null,
    @SerializedName("hand_before_play") val handBeforePlay: List<String>? = null,
    @SerializedName("lead_suit") val leadSuit: String? = null,
    @SerializedName("position_in_trick") val positionInTrick: Int? = null
)

data class MatchHistoryEntry(
    @SerializedName("doc_id") val docId: String? = null,
    @SerializedName("game_id") val gameId: String? = null,
    @SerializedName("game_stats") val gameStats: GameStatsData? = null,
    @SerializedName("player_id") val playerId: String? = null,
    val position: String? = null,
    @SerializedName("starting_hand") val startingHand: List<String>? = null,
    @SerializedName("trump_suit") val trumpSuit: String? = null,
    @SerializedName("finished_at") val finishedAt: String? = null,
    val rounds: Map<String, RoundData>? = null
)

data class MatchHistoryResponse(
    val success: Boolean,
    val history: List<MatchHistoryEntry>? = null,
    val count: Int? = null,
    val message: String? = null
)
