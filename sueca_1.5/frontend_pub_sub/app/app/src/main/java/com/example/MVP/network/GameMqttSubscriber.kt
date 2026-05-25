package com.example.MVP.network

import android.util.Log
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.HybridRuntimeState
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import org.eclipse.paho.client.mqttv3.IMqttActionListener
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.MqttAsyncClient
import org.eclipse.paho.client.mqttv3.MqttCallback
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttException
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import java.util.UUID
import java.util.concurrent.atomic.AtomicInteger

class GameMqttSubscriber(
    private val brokerHost: String,
    private val brokerPort: Int,
    private val protocol: String = "wss"
) {
    private val tag = "SuecaMQTT"

    data class Envelope(
        val eventType: String?,
        val gameId: String?,
        val state: GameStatusResponse?,
        val hybridState: HybridRuntimeState?,
        val cameraFrame: String?,
        val hands: Map<String, List<String>> = emptyMap()
    )

    private val gson = Gson()
    private var client: MqttAsyncClient? = null
    @Volatile private var connectInProgress: Boolean = false
    private val activeSessionId = AtomicInteger(0)
    private var probeAcked = false

    fun connectAndSubscribe(
        gameId: String,
        onEnvelope: (Envelope) -> Unit,
        onConnectionError: (String) -> Unit,
        onBrokerRoundTrip: () -> Unit = {}
    ) {
        val sid = activeSessionId.incrementAndGet()
        Log.d(tag, "connectAndSubscribe requested gameId=$gameId sid=$sid")
        connectAndSubscribeInternal(gameId, onEnvelope, onConnectionError, onBrokerRoundTrip, 0, sid)
    }

    private fun connectAndSubscribeInternal(
        gameId: String,
        onEnvelope: (Envelope) -> Unit,
        onConnectionError: (String) -> Unit,
        onBrokerRoundTrip: () -> Unit,
        attempt: Int,
        sid: Int
    ) {
        if (sid != activeSessionId.get()) {
            Log.i(tag, "Aborting connectAndSubscribe: session $sid is no longer active")
            return
        }

        val oldClient: MqttAsyncClient?
        synchronized(this) {
            if (connectInProgress && attempt == 0) {
                Log.w(tag, "connectAndSubscribe skipped gameId=$gameId because a connect is already in progress")
                return
            }
            val existing = client
            if (existing?.isConnected == true) {
                Log.i(tag, "connectAndSubscribe skipped gameId=$gameId because client is already connected")
                return
            }

            oldClient = existing
            connectInProgress = true
            client = null
        }

        if (oldClient != null) {
            try {
                Log.d(tag, "Closing old client for gameId=$gameId")
                if (oldClient.isConnected) {
                    oldClient.disconnectForcibly(200, 200)
                }
                oldClient.close()
            } catch (_: Exception) {}
        }

        // Fix: Use standard URI without port for 443/80 to avoid Paho WebSocket piping bug
        val serverUri = when {
            protocol == "wss" && brokerPort == 443 -> "wss://$brokerHost/mqtt"
            protocol == "ws" && brokerPort == 80 -> "ws://$brokerHost/mqtt"
            else -> "$protocol://$brokerHost:$brokerPort/mqtt"
        }
        
        // Fix: High-entropy clientId to prevent session collisions on broker or local library
        val clientId = "and-${UUID.randomUUID().toString().take(6)}-${System.currentTimeMillis() % 1000}"
        val probeTopic = "sueca/games/$gameId/client_probe/$clientId"
        val probePayload = "probe-${UUID.randomUUID()}"
        probeAcked = false

        Log.i(tag, "connectAndSubscribe start gameId=$gameId sid=$sid uri=$serverUri clientId=$clientId (attempt=$attempt)")

        try {
            val mqttClient = MqttAsyncClient(serverUri, clientId, MemoryPersistence())
            mqttClient.setCallback(object : MqttCallback {
                override fun connectionLost(cause: Throwable?) {
                    if (sid != activeSessionId.get()) return
                    Log.e(tag, "connectionLost gameId=$gameId sid=$sid cause=${cause?.message}", cause)
                    onConnectionError("MQTT disconnected: ${cause?.message ?: "unknown"}")
                }

                override fun messageArrived(topic: String?, message: MqttMessage?) {
                    if (sid != activeSessionId.get()) return
                    val payload = message?.payload?.toString(Charsets.UTF_8) ?: return
                    
                    Log.d(tag, "Message arrived (sid=$sid) topic=$topic payloadBytes=${message.payload.size}")

                    if (!probeAcked && topic == probeTopic && payload == probePayload) {
                        probeAcked = true
                        Log.i(tag, "broker round-trip ack received gameId=$gameId sid=$sid")
                        onBrokerRoundTrip()
                        return
                    }
                    val envelope = parseEnvelope(payload)
                    Log.d(tag, "Parsed envelope (sid=$sid) eventType=${envelope.eventType} hasState=${envelope.state != null}")
                    onEnvelope(envelope)
                }

                override fun deliveryComplete(token: IMqttDeliveryToken?) {}
            })

            val options = MqttConnectOptions().apply {
                isAutomaticReconnect = true
                isCleanSession = true
                connectionTimeout = 30
                keepAliveInterval = 60
                if (protocol == "wss") {
                    socketFactory = javax.net.ssl.SSLSocketFactory.getDefault()
                    isHttpsHostnameVerificationEnabled = false
                }
            }

            mqttClient.connect(options, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?) {
                    if (sid != activeSessionId.get()) {
                        Log.w(tag, "Connect success for stale session $sid, disconnecting...")
                        try { mqttClient.disconnectForcibly(100, 100); mqttClient.close() } catch (_: Exception) {}
                        return
                    }

                    Log.i(tag, "connect success gameId=$gameId sid=$sid")
                    connectInProgress = false
                    client = mqttClient
                    
                    try {
                        subscribeWithLog(mqttClient, "sueca/games/$gameId/state", gameId, sid)
                        subscribeWithLog(mqttClient, "sueca/games/$gameId/events", gameId, sid)
                        subscribeWithLog(mqttClient, "sueca/games/$gameId/players/+", gameId, sid)
                        subscribeWithLog(
                            mqttClient = mqttClient,
                            topic = probeTopic,
                            gameId = gameId,
                            sid = sid,
                            onSubscribed = {
                                publishProbe(mqttClient, probeTopic, probePayload, gameId, sid)
                            }
                        )
                    } catch (e: MqttException) {
                        Log.e(tag, "subscribe error gameId=$gameId sid=$sid", e)
                        onConnectionError("MQTT subscribe error: ${e.message}")
                    }
                }

                override fun onFailure(
                    asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?,
                    exception: Throwable?
                ) {
                    if (sid != activeSessionId.get()) {
                        Log.d(tag, "Ignoring connect failure for stale session $sid")
                        try { mqttClient.close() } catch (_: Exception) {}
                        return
                    }

                    val stackTrace = Log.getStackTraceString(exception)
                    val errorMsg = exception?.message ?: "unknown"
                    Log.e(tag, "connect failure gameId=$gameId sid=$sid error=$errorMsg", exception)
                    
                    val alreadyConnected = stackTrace.lowercase().contains("already connected") ||
                            errorMsg.lowercase().contains("already connected")

                    if (alreadyConnected && attempt < 5) {
                        // Exponential backoff with jitter
                        val delay = (1500L * (attempt + 1)) + (Math.random() * 500).toLong()
                        Log.w(tag, "Hit Paho 'Already connected' bug (sid=$sid). Retrying in ${delay}ms... (attempt ${attempt + 1})")
                        connectInProgress = false
                        try { mqttClient.close() } catch (_: Exception) {}
                        
                        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                            connectAndSubscribeInternal(gameId, onEnvelope, onConnectionError, onBrokerRoundTrip, attempt + 1, sid)
                        }, delay)
                        return
                    }

                    connectInProgress = false
                    try {
                        if (mqttClient.isConnected) mqttClient.disconnectForcibly(200, 200)
                        mqttClient.close()
                    } catch (_: Exception) {}
                    
                    onConnectionError("MQTT connect error: $errorMsg")
                }
            })

        } catch (e: Exception) {
            if (sid == activeSessionId.get()) {
                connectInProgress = false
                Log.e(tag, "setup error gameId=$gameId sid=$sid", e)
                onConnectionError("MQTT setup error: ${e.message}")
            }
        }
    }

    fun disconnect() {
        val sid = activeSessionId.incrementAndGet() // Invalidate any ongoing connect attempts
        val mqttClient = client
        client = null
        connectInProgress = false
        
        Log.i(tag, "disconnect requested, new sid=$sid")
        
        if (mqttClient == null) return

        Thread {
            try {
                if (mqttClient.isConnected) {
                    mqttClient.disconnect().waitForCompletion(500)
                }
                mqttClient.close()
                Log.d(tag, "Client closed successfully (sid=$sid)")
            } catch (e: Exception) {
                Log.w(tag, "Error during disconnect (sid=$sid): ${e.message}")
                try { mqttClient.close() } catch (_: Exception) {}
            }
        }.start()
    }

    private fun subscribeWithLog(
        mqttClient: MqttAsyncClient,
        topic: String,
        gameId: String,
        sid: Int,
        onSubscribed: (() -> Unit)? = null
    ) {
        if (sid != activeSessionId.get()) return
        
        mqttClient.subscribe(topic, 1, null, object : IMqttActionListener {
            override fun onSuccess(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?) {
                Log.i(tag, "subscribed gameId=$gameId sid=$sid topic=$topic")
                onSubscribed?.invoke()
            }

            override fun onFailure(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?, exception: Throwable?) {
                if (sid != activeSessionId.get()) return
                Log.e(tag, "subscribe failure gameId=$gameId sid=$sid topic=$topic error=${exception?.message}", exception)
            }
        })
    }

    private fun publishProbe(mqttClient: MqttAsyncClient, topic: String, payload: String, gameId: String, sid: Int) {
        if (sid != activeSessionId.get()) return

        mqttClient.publish(topic, payload.toByteArray(Charsets.UTF_8), 1, false, null, object : IMqttActionListener {
            override fun onSuccess(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?) {
                Log.i(tag, "probe published gameId=$gameId sid=$sid topic=$topic")
            }

            override fun onFailure(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?, exception: Throwable?) {
                if (sid != activeSessionId.get()) return
                Log.e(tag, "probe publish failure gameId=$gameId sid=$sid topic=$topic error=${exception?.message}", exception)
            }
        })
    }

    private fun parseEnvelope(payload: String): Envelope {
        return try {
            val root = JsonParser.parseString(payload).asJsonObject
            val state = root.getAsJsonObjectOrNull("state")
                ?.let { gson.fromJson(it, GameStatusResponse::class.java) }

            val hybridState = root.getAsJsonObjectOrNull("hybrid_state")
                ?.let { gson.fromJson(it, HybridRuntimeState::class.java) }

            val cameraFrame = root.getStringOrNull("camera_frame")

            Envelope(
                eventType = root.getStringOrNull("event_type"),
                gameId = root.getStringOrNull("game_id"),
                state = state,
                hybridState = hybridState,
                cameraFrame = cameraFrame,
                hands = root.getHandsMap()
            )
        } catch (e: Exception) {
            Log.w(tag, "parseEnvelope failed", e)
            Envelope(null, null, null, null, null, emptyMap())
        }
    }

    fun publishCameraFrame(gameId: String, frameBase64: String) {
        val mqttClient = client ?: return
        try {
            val topic = "sueca/games/$gameId/camera_frame"
            mqttClient.publish(topic, frameBase64.toByteArray(Charsets.UTF_8), 1, false)
        } catch (e: Exception) {
            Log.w(tag, "publishCameraFrame failed: ${e.message}")
        }
    }

    private fun JsonObject.getAsJsonObjectOrNull(key: String): JsonObject? {
        if (!has(key)) return null
        val value = get(key)
        return if (value != null && value.isJsonObject) value.asJsonObject else null
    }

    private fun JsonObject.getStringOrNull(key: String): String? {
        if (!has(key)) return null
        val value = get(key)
        return if (value != null && value.isJsonPrimitive) value.asString else null
    }

    private fun JsonObject.getHandsMap(): Map<String, List<String>> {
        val handsObj = getAsJsonObjectOrNull("hands") ?: return emptyMap()
        val out = mutableMapOf<String, List<String>>()

        for ((playerId, handJson) in handsObj.entrySet()) {
            if (!handJson.isJsonArray) continue
            out[playerId] = handJson.asJsonArray.mapNotNull { element ->
                if (element != null && element.isJsonPrimitive) element.asString else null
            }
        }
        return out
    }
}
