package com.example.MVP.network

import com.example.MVP.models.*
import retrofit2.http.*

interface ApiService {
    @GET("/game/status")
    suspend fun getStatus(): GameStatusResponse

    @POST("/game/join")
    suspend fun joinGame(@Body payload: Map<String, String>): JoinResponse

    @GET("/game/hand/{playerName}")
    suspend fun getHand(@Path("playerName") playerName: String): HandResponse

    @POST("/game/play")
    suspend fun playCard(@Body payload: PlayRequest): GenericResponse

    @POST("/game/cut_deck")
    suspend fun cutDeck(@Body payload: CutDeckRequest): GenericResponse

    @POST("/game/select_trump")
    suspend fun selectTrump(@Body payload: SelectTrumpRequest): GenericResponse

    @POST("/game/reset")
    suspend fun resetGame(): GenericResponse

    // Room-based endpoints (for RoomActivity compatibility)
    @POST("/room/create")
    suspend fun createRoom(@Body request: CreateRoomRequest): CreateRoomResponse

    @POST("/room/join")
    suspend fun joinRoom(@Body request: JoinRoomRequest): JoinRoomResponse

    @GET("/room/{roomId}/state")
    suspend fun getRoomState(@Path("roomId") roomId: String): RoomState

    @POST("/game/start")
    suspend fun startGame(@Body request: StartGameRequest): StartGameResponse

    @POST("game/ready/{gameId}")
    suspend fun startGameReady(@Path("gameId") gameId: String): StartGameResponse

    @POST("game/new_round/{gameId}")
    suspend fun startNewRound(@Path("gameId") gameId: String): StartGameResponse

}