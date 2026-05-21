package com.example.MVP.network

import com.example.MVP.models.*
import retrofit2.http.*

interface ApiService {

    // ============ /api/auth Endpoints ============

    @POST("/api/auth/register")
    suspend fun registerUser(@Body request: RegisterRequest): RegisterResponse

    @POST("/api/auth/verify-email")
    suspend fun verifyEmail(@Body request: VerifyEmailRequest): AuthResponse

    @POST("/api/auth/login")
    suspend fun loginUser(@Body request: LoginRequest): AuthResponse

    @GET("/api/auth/recover-password")
    suspend fun recoverPassword(@Query("email") email: String): RecoverPasswordResponse

    @POST("/api/auth/reset-password")
    suspend fun resetPassword(@Body request: ResetPasswordRequest): GenericResponse

    @GET("/api/auth/user/{uid}")
    suspend fun getUser(
        @Path("uid") uid: String,
        @Header("Authorization") token: String
    ): UserResponse

    @GET("/api/auth/user/by-friend-code/{friendCode}")
    suspend fun getUserByFriendCode(
        @Path("friendCode") friendCode: String,
        @Header("Authorization") token: String
    ): UserResponse

    @PUT("/api/auth/user/{uid}")
    suspend fun updateUser(
        @Path("uid") uid: String,
        @Body request: UpdateUserRequest,
        @Header("Authorization") token: String
    ): UserResponse

    @DELETE("/api/auth/user/{uid}")
    suspend fun deleteUser(
        @Path("uid") uid: String,
        @Header("Authorization") token: String
    ): GenericResponse

    @POST("/api/auth/logout")
    suspend fun logoutUser(
        @Body request: LogoutRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    @POST("/api/auth/request-delete")
    suspend fun requestDeleteAccount(
        @Body request: DeleteAccountRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    @POST("/api/auth/confirm-delete")
    suspend fun confirmDeleteAccount(
        @Body request: ConfirmDeleteAccountRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    // ============ /api/friends Endpoints ============

    @POST("/api/friends/request")
    suspend fun sendFriendRequest(
        @Body request: SendFriendRequestRequest,
        @Header("Authorization") token: String
    ): FriendRequestResponse

    @POST("/api/friends/request-by-username")
    suspend fun sendFriendRequestByUsername(
        @Body request: SendFriendRequestByUsernameRequest,
        @Header("Authorization") token: String
    ): FriendRequestResponse

    @POST("/api/friends/accept")
    suspend fun acceptFriendRequest(
        @Body request: AcceptFriendRequestRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    @POST("/api/friends/decline")
    suspend fun declineFriendRequest(
        @Body request: DeclineFriendRequestRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    @HTTP(method = "DELETE", path = "/api/friends", hasBody = true)
    suspend fun removeFriend(
        @Body request: FriendRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    @GET("/api/friends/list")
    suspend fun listFriends(
        @Query("uid") uid: String,
        @Header("Authorization") token: String,
        @Query("online_only") onlineOnly: Boolean = false
    ): FriendsListResponse

    @GET("/api/friends/requests")
    suspend fun listFriendRequests(
        @Query("uid") uid: String,
        @Header("Authorization") token: String
    ): FriendRequestsListResponse

    @GET("/api/friends/get_code")
    suspend fun getFriendCode(
        @Query("uid") uid: String,
        @Header("Authorization") token: String
    ): FriendCodeResponse

    // ============ /api Endpoints ============

    @GET("/api/status")
    suspend fun getStatus(@Query("game_id") gameId: String? = null): GameStatusResponse

    @POST("/api/join")
    suspend fun joinGame(@Body payload: Map<String, String>): JoinResponse

    @POST("/api/join")
    suspend fun joinGameWithPosition(@Body request: JoinGameRequest): JoinGameResponse

    @POST("/api/create_room")
    suspend fun createRoomV2(@Body request: CreateRoomRequest): CreateRoomResponse

    @GET("/api/rooms")
    suspend fun getRooms(): RoomsResponse

    @GET("/api/hand/{playerId}")
    suspend fun getHand(
        @Path("playerId") playerId: String,
        @Query("game_id") gameId: String? = null
    ): HandResponse

    @POST("/api/play")
    suspend fun playCard(
        @Body payload: PlayRequest,
        @Header("Authorization") token: String? = null
    ): GenericResponse

    @POST("/api/cut_deck")
    suspend fun cutDeck(
        @Body payload: CutDeckRequest,
        @Header("Authorization") token: String? = null
    ): GenericResponse

    @POST("/api/select_trump")
    suspend fun selectTrump(
        @Body payload: SelectTrumpRequest,
        @Header("Authorization") token: String? = null
    ): GenericResponse

    @POST("/api/reset")
    suspend fun resetGame(@Header("Authorization") token: String? = null): GenericResponse

    @POST("/api/room_visibility")
    suspend fun setRoomVisibility(
        @Body request: RoomVisibilityRequest,
        @Header("Authorization") token: String? = null
    ): retrofit2.Response<GenericResponse>

    @POST("/api/leave")
    suspend fun leaveRoom(
        @Body request: LeaveRoomRequest,
        @Header("Authorization") token: String? = null
    ): GenericResponse

    @POST("/api/room/{gameId}/invite")
    suspend fun inviteFriend(
        @Path("gameId") gameId: String,
        @Body request: InviteRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    @POST("/api/room/{gameId}/invite/decline")
    suspend fun declineInvite(
        @Path("gameId") gameId: String,
        @Body request: DeclineInviteRequest,
        @Header("Authorization") token: String
    ): GenericResponse

    @GET("/api/invites")
    suspend fun getInvites(
        @Header("Authorization") token: String
    ): InvitesResponse

    // =========== /api/room Endpoints ============

    @GET("/api/room/{gameId}/match_points")
    suspend fun getMatchPoints(@Path("gameId") gameId: String): MatchPointsResponse

    @POST("/api/room/{gameId}/rematch")
    suspend fun requestRematch(@Path("gameId") gameId: String): GenericResponse

    @POST("/api/start")
    suspend fun startGame(
        @Body request: StartGameRequest,
        @Header("Authorization") token: String? = null
    ): StartGameResponse

    @POST("/game/start")
    suspend fun startPhysicalGame(
        @Body request: StartGameRequest,
        @Header("Authorization") token: String? = null
    ): StartGameResponse

    @POST("/api/add_bot")
    suspend fun addBot(
        @Body request: AddBotRequest,
        @Header("Authorization") token: String? = null
    ): AddBotResponse

    // Issue short-lived token for camera websocket streaming
    @POST("/auth/game_token")
    suspend fun getGameToken(
        @Body request: GameTokenRequest,
        @Header("Authorization") token: String? = null
    ): GameTokenResponse

    @POST("/api/the_council_has_decided_your_fate")
    suspend fun removeParticipant(
        @Body request: RemoveParticipantRequest,
        @Header("Authorization") token: String? = null
    ): GenericResponse

    // =========== /room Endpoints ============

    @POST("/room/create")
    suspend fun createRoom(@Body request: CreateRoomRequest): CreateRoomResponse

    @POST("/room/join")
    suspend fun joinRoom(@Body request: JoinRoomRequest): JoinRoomResponse

    @GET("/room/{roomId}/state")
    suspend fun getRoomState(@Path("roomId") roomId: String): RoomState

    // =========== /game Endpoints ============

    @POST("game/ready/{gameId}")
    suspend fun startGameReady(
        @Path("gameId") gameId: String,
        @Query("dealer_id") dealerId: Int? = null,
        @Query("starter_id") starterId: Int? = null,
        @Header("Authorization") token: String? = null
    ): StartGameResponse

    @POST("game/new_round/{gameId}")
    suspend fun startNewRound(
        @Path("gameId") gameId: String,
        @Header("Authorization") token: String? = null
    ): StartGameResponse

    @POST("game/correct/{gameId}")
    suspend fun correctGameCard(
        @Path("gameId") gameId: String,
        @Body request: CorrectCardRequest,
        @Header("Authorization") token: String? = null
    ): GenericResponse

    // =========== Hybrid Endpoints ============

    @POST("/api/hybrid/session/reset")
    suspend fun resetHybridSession(@Body request: HybridSessionResetRequest): HybridSessionStatusResponse

    @GET("/api/hybrid/session/status")
    suspend fun getHybridSessionStatus(
        @Query("game_id") gameId: String,
        @Query("target_count") targetCount: Int = 10
    ): HybridSessionStatusResponse

    @POST("/api/hybrid/recognize_card")
    suspend fun recognizeHybridCard(@Body request: HybridRecognizeRequest): HybridRecognizeResponse

    @POST("/api/hybrid/register_player")
    suspend fun hybridRegisterPlayer(@Body request: HybridRegisterPlayerRequest): HybridStateResponse

    @GET("/api/hybrid/state")
    suspend fun hybridState(@Query("game_id") gameId: String): HybridStateResponse

    @POST("/api/hybrid/deal/reset")
    suspend fun hybridDealReset(@Body request: HybridDealResetRequest): HybridStateResponse

    @POST("/api/hybrid/deal/recognize")
    suspend fun hybridDealRecognize(@Body request: HybridDealRecognizeRequest): HybridDealRecognizeResponse

    @POST("/api/hybrid/virtual/select_card")
    suspend fun hybridSelectCard(@Body request: HybridSelectCardRequest): HybridStateResponse

    @GET("/api/hybrid/pending_play")
    suspend fun hybridPendingPlay(@Query("game_id") gameId: String): HybridPendingResponse

    @POST("/api/hybrid/play/confirm_capture")
    suspend fun hybridConfirmCapture(@Body request: HybridConfirmCaptureRequest): HybridConfirmCaptureResponse

    @POST("/api/hybrid/trump/confirm_capture")
    suspend fun hybridConfirmTrumpCapture(
        @Body request: HybridConfirmTrumpCaptureRequest
    ): HybridConfirmTrumpCaptureResponse

    // =========== Gateway endpoints (Sueca 1.4) ============

    @POST("/game/room_mode/{gameId}")
    suspend fun setRoomMode(
        @Path("gameId") gameId: String,
        @Body request: RoomModeRequest,
        @Header("Authorization") token: String? = null
    ): GenericResponse

    @GET("/game/room_mode/{gameId}")
    suspend fun getRoomMode(
        @Path("gameId") gameId: String,
        @Header("Authorization") token: String? = null
    ): RoomModeResponse

    @POST("/game/command/{command}")
    suspend fun routeCommand(
        @Path(value = "command", encoded = true) command: String,
        @Body request: GatewayCommandRequest,
        @Header("Authorization") token: String? = null
    ): GatewayEnvelope

    @GET("/game/query/{queryPath}")
    suspend fun routeQuery(
        @Path(value = "queryPath", encoded = true) queryPath: String,
        @Query("game_id") gameId: String? = null,
        @Query("mode") mode: String? = null,
        @Header("Authorization") token: String? = null
    ): GatewayEnvelope

}
