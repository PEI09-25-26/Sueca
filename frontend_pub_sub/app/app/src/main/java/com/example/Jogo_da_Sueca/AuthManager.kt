package com.example.Jogo_da_Sueca

import android.content.Context
import android.content.SharedPreferences
import com.example.Jogo_da_Sueca.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.*

/**
 * Manages authentication for both guest and authenticated users.
 *
 * - Guests: Create temporary session tokens for gameplay without account
 * - Authenticated: JWT tokens obtained via login (to be implemented)
 */
class AuthManager(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences(
        "sueca_auth", Context.MODE_PRIVATE
    )

    private var currentSessionToken: String? = null
    private var sessionTokenExpiryTime: Long = 0
    private var currentPlayerId: String? = null

    /**
     * Get or create a guest session token for gameplay.
     * Tokens are cached in memory and expire after 25 minutes (JWT TTL is 30 min).
     */
    suspend fun getOrCreateGuestSessionToken(playerName: String? = null): String? = withContext(Dispatchers.IO) {
        // Check if we have a valid cached token
        val now = System.currentTimeMillis()
        if (currentSessionToken != null && sessionTokenExpiryTime > now + 60_000) {
            // Token still valid for at least 1 minute
            return@withContext currentSessionToken
        }

        // Get or create session token via backend
        val result = fetchGuestSessionToken(playerName)
        if (result != null) {
            currentSessionToken = result.first
            currentPlayerId = result.second
            // Cache for ~25 minutes (JWT TTL is 30 min, keep 5 min buffer)
            sessionTokenExpiryTime = now + 25 * 60 * 1000
        }
        result?.first
    }

    /**
     * Get current session token without refresh.
     */
    fun getCurrentSessionToken(): String? = currentSessionToken

    /**
     * Get current player ID.
     */
    fun getCurrentPlayerId(): String? = currentPlayerId

    /**
     * Clear session token (e.g., on logout).
     */
    fun clearSessionToken() {
        currentSessionToken = null
        currentPlayerId = null
        sessionTokenExpiryTime = 0
    }

    /**
     * Fetch a guest session token from backend.
     * Returns Pair of (token, playerId) or null on failure.
     */
    private suspend fun fetchGuestSessionToken(playerName: String? = null): Pair<String, String>? = withContext(Dispatchers.IO) {
        try {
            val response = RetrofitClient.api.createGuestSession(
                mapOf("player_name" to (playerName ?: "Guest"))
            )
            if (response.success) {
                return@withContext Pair(response.session_token, response.player_id)
            }
            return@withContext null
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    /**
     * Set a user token (from login endpoint).
     * To be called after successful login.
     */
    fun setUserToken(token: String, playerId: String, expirySeconds: Int = 3600) {
        currentSessionToken = token
        currentPlayerId = playerId
        sessionTokenExpiryTime = System.currentTimeMillis() + (expirySeconds * 1000L)
    }

    /**
     * Check if a token is expired.
     */
    fun isTokenExpired(): Boolean {
        val now = System.currentTimeMillis()
        return sessionTokenExpiryTime <= now
    }

    /**
     * Get time remaining on token in seconds.
     */
    fun getTokenTimeRemaining(): Long {
        val remaining = sessionTokenExpiryTime - System.currentTimeMillis()
        return if (remaining > 0) remaining / 1000 else 0
    }

    companion object {
        @Volatile
        private var instance: AuthManager? = null

        fun getInstance(context: Context): AuthManager {
            return instance ?: synchronized(this) {
                AuthManager(context.applicationContext).also { instance = it }
            }
        }
    }
}
