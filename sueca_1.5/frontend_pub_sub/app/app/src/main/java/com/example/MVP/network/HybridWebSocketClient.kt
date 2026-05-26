package com.example.MVP.network

import android.graphics.BitmapFactory
import android.util.Log
import com.example.MVP.GameSessionManager
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.HybridRuntimeState
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import okhttp3.*
import okio.ByteString
import java.util.concurrent.TimeUnit

/**
 * Cliente WebSocket unificado para o modo Híbrido.
 * Gere comunicação bidirecional com o Gateway:
 * - Envia frames de câmara (binários) e ações de jogo (JSON texto)
 * - Recebe atualizações de estado em tempo real e frames de câmara do host
 */
class HybridWebSocketClient(
    private val roomId: String,
    private val onStateUpdate: (hybridState: HybridRuntimeState?, gameState: GameStatusResponse?) -> Unit,
    private val onFrameReceived: (ByteArray) -> Unit,
    private val onActionResponse: (action: String, response: JsonObject) -> Unit,
    private val onConnectionLost: (String) -> Unit = {}
) {
    companion object {
        private const val TAG = "HybridWS"
        private const val NORMAL_CLOSE = 1000
        private const val RECONNECT_DELAY_MS = 3000L
        private const val MAX_RECONNECT_ATTEMPTS = 10
    }

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS) // No read timeout for WS
        .pingInterval(30, TimeUnit.SECONDS)     // Keepalive
        .build()

    private val gson = Gson()
    private var webSocket: WebSocket? = null
    @Volatile private var connected = false
    @Volatile private var intentionalClose = false
    private var reconnectAttempts = 0

    fun connect() {
        intentionalClose = false
        reconnectAttempts = 0
        doConnect()
    }

    private fun doConnect() {
        val token = GameSessionManager.getToken(roomId)
        val url = if (!token.isNullOrBlank()) {
            "wss://${RetrofitClient.API_HOST}/ws/hybrid/$roomId?token=$token"
        } else {
            "wss://${RetrofitClient.API_HOST}/ws/hybrid/$roomId"
        }

        Log.i(TAG, "Connecting to $url")

        val request = Request.Builder()
            .url(url)
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                connected = true
                reconnectAttempts = 0
                Log.i(TAG, "Connected to hybrid WebSocket for room $roomId")
            }

            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                // Binary message = camera frame from host
                onFrameReceived(bytes.toByteArray())
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                // JSON text message = state update or action response
                try {
                    val root = JsonParser.parseString(text).asJsonObject
                    val type = root.get("type")?.asString

                    when (type) {
                        "state_update" -> {
                            val hybridState = root.getAsJsonObject("hybrid_state")
                                ?.let { gson.fromJson(it, HybridRuntimeState::class.java) }
                            val gameState = root.getAsJsonObject("game_state")
                                ?.let { gson.fromJson(it, GameStatusResponse::class.java) }
                            onStateUpdate(hybridState, gameState)
                        }
                        "action_response" -> {
                            val action = root.get("action")?.asString ?: ""
                            val response = root.getAsJsonObject("response") ?: JsonObject()
                            onActionResponse(action, response)
                        }
                        else -> {
                            Log.w(TAG, "Unknown message type: $type")
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing WS message: ${text.take(200)}", e)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "WebSocket closing: $code $reason")
                webSocket.close(NORMAL_CLOSE, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                connected = false
                Log.i(TAG, "WebSocket closed: $code $reason")
                if (!intentionalClose) {
                    scheduleReconnect()
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                connected = false
                Log.e(TAG, "WebSocket failure: ${t.message}", t)
                onConnectionLost("WebSocket error: ${t.message}")
                if (!intentionalClose) {
                    scheduleReconnect()
                }
            }
        })
    }

    private fun scheduleReconnect() {
        if (intentionalClose) return
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            Log.w(TAG, "Max reconnect attempts reached for room $roomId")
            onConnectionLost("WebSocket: max reconnect attempts reached")
            return
        }

        reconnectAttempts++
        val delay = RECONNECT_DELAY_MS * reconnectAttempts
        Log.i(TAG, "Scheduling reconnect attempt $reconnectAttempts in ${delay}ms")

        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            if (!intentionalClose && !connected) {
                doConnect()
            }
        }, delay)
    }

    fun disconnect() {
        intentionalClose = true
        connected = false
        webSocket?.close(NORMAL_CLOSE, "User disconnected")
        webSocket = null
    }

    /**
     * Envia uma ação de jogo via WebSocket (texto JSON).
     * O Gateway traduz a ação para um HTTP POST ao hybrid_engine.
     */
    fun sendAction(action: String, payload: Any) {
        val envelope = JsonObject().apply {
            addProperty("type", "action")
            addProperty("action", action)
            add("payload", gson.toJsonTree(payload))
        }
        val sent = webSocket?.send(envelope.toString()) ?: false
        if (!sent) {
            Log.w(TAG, "Failed to send action $action (WS not connected)")
        }
    }

    /**
     * Envia um frame de câmara como dados binários.
     * O Gateway reencaminha para todos os outros clientes no mesmo jogo.
     */
    fun sendBinaryFrame(bytes: ByteArray) {
        webSocket?.send(ByteString.of(*bytes))
    }

    fun isConnected(): Boolean = connected
}
