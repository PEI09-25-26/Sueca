package com.example.MVP

object GameSessionManager {
    private val roomTokens = mutableMapOf<String, String>()

    fun saveToken(roomId: String, token: String?) {
        val normalizedRoomId = roomId.trim()
        if (normalizedRoomId.isBlank()) return
        if (token.isNullOrBlank()) {
            roomTokens.remove(normalizedRoomId)
        } else {
            roomTokens[normalizedRoomId] = token
        }
    }

    fun getToken(roomId: String?): String? {
        val normalizedRoomId = roomId?.trim().orEmpty()
        if (normalizedRoomId.isBlank()) return null
        return roomTokens[normalizedRoomId]
    }

    fun getAuthHeader(roomId: String?): String? {
        val token = getToken(roomId) ?: return null
        return "Bearer $token"
    }

    fun clearToken(roomId: String?) {
        val normalizedRoomId = roomId?.trim().orEmpty()
        if (normalizedRoomId.isNotBlank()) {
            roomTokens.remove(normalizedRoomId)
        }
    }
}
