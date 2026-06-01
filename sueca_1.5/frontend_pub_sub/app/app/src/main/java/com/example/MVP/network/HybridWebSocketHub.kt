package com.example.MVP.network

import java.util.concurrent.ConcurrentHashMap

/**
 * Keeps one hybrid WebSocket client per room id.
 *
 * This avoids accidental sharing of a single client across rooms and lets
 * multiple hybrid games stay connected at the same time inside the same app
 * process.
 */
object HybridWebSocketHub {
    private val clients = ConcurrentHashMap<String, HybridWebSocketClient>()

    fun get(roomId: String): HybridWebSocketClient? = clients[roomId]

    fun put(roomId: String, client: HybridWebSocketClient) {
        clients[roomId] = client
    }

    fun remove(roomId: String) {
        clients.remove(roomId)
    }

    fun disconnect(roomId: String) {
        clients.remove(roomId)?.disconnect()
    }
}