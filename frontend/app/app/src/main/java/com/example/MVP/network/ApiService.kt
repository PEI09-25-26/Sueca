package com.example.MVP.network

import com.example.MVP.models.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ============ /api/auth Endpoints ============

    @POST("/api/auth/register")
    suspend fun registerUser(@Body request: RegisterRequest): RegisterResponse

    @POST("/api/auth/verify-email")
    suspend fun verifyEmail(@Body request: VerifyEmailRequest): AuthResponse

    @POST("/api/auth/login")
    suspend fun loginUser(@Body request: LoginRequest): AuthResponse

    @GET("/api/auth/user/{uid}")
    suspend fun getUser(
        @Path("uid") uid: String,
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

    @GET("/api/friends/list")
    suspend fun listFriends(
        @Query("uid") uid: String,
        @Header("Authorization") token: String
    ): FriendsListResponse

    @GET("/api/friends/requests")
    suspend fun listFriendRequests(
        @Query("uid") uid: String,
        @Header("Authorization") token: String
    ): FriendRequestsListResponse

    // ============ /api Endpoints ============

    @GET("/api/status")
    suspend fun getStatus(@Query("game_id") gameId: String? = null): GameStatusResponse

    @POST("/api/join")
    suspend fun joinGame(@Body payload: Map<String, String>): JoinResponse

    @POST("/api/join")
    suspend fun joinGameWithPosition(@Body request: JoinGameRequest): JoinGameResponse

    @POST("/api/create_room")
    suspend fun createRoomV2(): CreateRoomResponse

    @GET("/api/rooms")
    suspend fun getRooms(): RoomsResponse

    @GET("/api/hand/{playerId}")
    suspend fun getHand(
        @Path("playerId") playerId: String,
        @Query("game_id") gameId: String? = null
    ): HandResponse

    @POST("/api/play")
    suspend fun playCard(@Body payload: PlayRequest): GenericResponse

    @POST("/api/cut_deck")
    suspend fun cutDeck(@Body payload: CutDeckRequest): GenericResponse

    @POST("/api/select_trump")
    suspend fun selectTrump(@Body payload: SelectTrumpRequest): GenericResponse

    @POST("/api/reset")
    suspend fun resetGame(): GenericResponse

    @POST("/api/room_visibility")
    suspend fun setRoomVisibility(@Body request: RoomVisibilityRequest): Response<GenericResponse>

    // =========== /api/room Endpoints ============

    @GET("/api/room/{gameId}/match_points")
    suspend fun getMatchPoints(@Path("gameId") gameId: String): MatchPointsResponse

    @POST("/api/room/{gameId}/rematch")
    suspend fun requestRematch(@Path("gameId") gameId: String): GenericResponse

    @POST("/api/start")
    suspend fun startGame(@Body request: StartGameRequest): StartGameResponse

    @POST("/api/add_bot")
    suspend fun addBot(@Body request: AddBotRequest): AddBotResponse

    @POST("/api/the_council_has_decided_your_fate")
    suspend fun removeParticipant(@Body request: RemoveParticipantRequest): GenericResponse

    // =========== /room Endpoints ============

    @POST("/room/create")
    suspend fun createRoom(@Body request: CreateRoomRequest): CreateRoomResponse

    @POST("/room/join")
    suspend fun joinRoom(@Body request: JoinRoomRequest): JoinRoomResponse

    @GET("/room/{roomId}/state")
    suspend fun getRoomState(@Path("roomId") roomId: String): RoomState

    // =========== /game Endpoints ============

    @POST("game/ready/{gameId}")
    suspend fun startGameReady(@Path("gameId") gameId: String): StartGameResponse

    @POST("game/new_round/{gameId}")
    suspend fun startNewRound(@Path("gameId") gameId: String): StartGameResponse

}