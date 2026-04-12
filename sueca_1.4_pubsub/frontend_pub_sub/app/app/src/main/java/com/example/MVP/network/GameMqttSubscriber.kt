package com.example.MVP.network

import android.util.Log
import com.example.MVP.models.GameStatusResponse
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

class GameMqttSubscriber(
    private val brokerHost: String,
    private val brokerPort: Int
) {
    private val tag = "SuecaMQTT"

    data class Envelope(
        val eventType: String?,
        val gameId: String?,
        val state: GameStatusResponse?,
        val hands: Map<String, List<String>>
    )

    private val gson = Gson()
    private var client: MqttAsyncClient? = null

    fun connectAndSubscribe(
        gameId: String,
        onEnvelope: (Envelope) -> Unit,
        onConnectionError: (String) -> Unit,
        onBrokerRoundTrip: () -> Unit = {}
    ) {
        val serverUri = "tcp://$brokerHost:$brokerPort"
        val clientId = "android-${UUID.randomUUID()}"
        val probeTopic = "sueca/games/$gameId/client_probe/$clientId"
        val probePayload = "probe-${UUID.randomUUID()}"
        var probeAcked = false
        Log.i(tag, "connectAndSubscribe start gameId=$gameId uri=$serverUri clientId=$clientId (pls work)")

        try {
            // Android file persistence was randomly exploding, so memory persistence it is.
            val mqttClient = MqttAsyncClient(serverUri, clientId, MemoryPersistence())
            mqttClient.setCallback(object : MqttCallback {
                override fun connectionLost(cause: Throwable?) {
                    Log.e(tag, "connectionLost gameId=$gameId cause=${cause?.message} (well... there it goes)", cause)
                    onConnectionError("MQTT disconnected: ${cause?.message ?: "unknown"}")
                }

                override fun messageArrived(topic: String?, message: MqttMessage?) {
                    val payload = message?.payload?.toString(Charsets.UTF_8) ?: return
                    if (!probeAcked && topic == probeTopic && payload == probePayload) {
                        probeAcked = true
                        Log.i(tag, "broker round-trip ack received gameId=$gameId topic=$probeTopic (nice)")
                        onBrokerRoundTrip()
                        return
                    }
                    Log.d(
                        tag,
                        "messageArrived gameId=$gameId topic=$topic payloadBytes=${message?.payload?.size ?: 0} qos=${message?.qos} retained=${message?.isRetained}"
                    )
                    val envelope = parseEnvelope(payload)
                    if (envelope.state == null && envelope.eventType == null && envelope.hands.isEmpty()) {
                        Log.w(tag, "message parsed with empty envelope gameId=$gameId topic=$topic (maybe backend sent vibes)")
                    }
                    onEnvelope(envelope)
                }

                override fun deliveryComplete(token: IMqttDeliveryToken?) {
                    // Subscriber only.
                }
            })

            val options = MqttConnectOptions().apply {
                isAutomaticReconnect = true
                isCleanSession = false
                connectionTimeout = 8
                keepAliveInterval = 30
            }

            mqttClient.connect(options, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?) {
                    Log.i(tag, "connect success gameId=$gameId, subscribing topics (go go go)")
                    try {
                        subscribeWithLog(mqttClient, "sueca/games/$gameId/state", gameId)
                        subscribeWithLog(mqttClient, "sueca/games/$gameId/events", gameId)
                        subscribeWithLog(mqttClient, "sueca/games/$gameId/players/+", gameId)
                        subscribeWithLog(
                            mqttClient = mqttClient,
                            topic = probeTopic,
                            gameId = gameId,
                            onSubscribed = {
                                publishProbe(mqttClient, probeTopic, probePayload, gameId)
                            }
                        )
                    } catch (e: MqttException) {
                        Log.e(tag, "subscribe error gameId=$gameId (pain)", e)
                        onConnectionError("MQTT subscribe error: ${e.message}")
                    }
                }

                override fun onFailure(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?, exception: Throwable?) {
                    Log.e(tag, "connect failure gameId=$gameId error=${exception?.message} (not today)", exception)
                    onConnectionError("MQTT connect error: ${exception?.message ?: "unknown"}")
                }
            })

            client = mqttClient
            Log.d(tag, "client instance created gameId=$gameId (caffeine mode)")
        } catch (e: Exception) {
            Log.e(tag, "setup error gameId=$gameId (well, I guess it's not working)", e)
            onConnectionError("MQTT setup error: ${e.message}")
        }
    }

    fun disconnect() {
        val mqttClient = client ?: return
        try {
            if (mqttClient.isConnected) {
                Log.i(tag, "disconnect requested (someone kick this guy out)")
                mqttClient.disconnect()
            }
            mqttClient.close()
            Log.i(tag, "client closed (done)")
        } catch (e: Exception) {
            Log.w("GameMqttSubscriber", "Error disconnecting MQTT", e)
        } finally {
            client = null
        }
    }

    private fun subscribeWithLog(
        mqttClient: MqttAsyncClient,
        topic: String,
        gameId: String,
        onSubscribed: (() -> Unit)? = null
    ) {
        mqttClient.subscribe(topic, 1, null, object : IMqttActionListener {
            override fun onSuccess(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?) {
                Log.i(tag, "subscribed gameId=$gameId topic=$topic (ok this one worked)")
                onSubscribed?.invoke()
            }

            override fun onFailure(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?, exception: Throwable?) {
                Log.e(tag, "subscribe failure gameId=$gameId topic=$topic error=${exception?.message} (why)", exception)
            }
        })
    }

    private fun publishProbe(mqttClient: MqttAsyncClient, topic: String, payload: String, gameId: String) {
        mqttClient.publish(topic, payload.toByteArray(Charsets.UTF_8), 1, false, null, object : IMqttActionListener {
            override fun onSuccess(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?) {
                Log.i(tag, "probe published gameId=$gameId topic=$topic (pls echo back)")
            }

            override fun onFailure(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?, exception: Throwable?) {
                Log.e(tag, "probe publish failure gameId=$gameId topic=$topic error=${exception?.message} (sad)", exception)
            }
        })
    }

    private fun parseEnvelope(payload: String): Envelope {
        return try {
            val root = JsonParser.parseString(payload).asJsonObject
            val state = root.getAsJsonObjectOrNull("state")
                ?.let { gson.fromJson(it, GameStatusResponse::class.java) }

            Envelope(
                eventType = root.getStringOrNull("event_type"),
                gameId = root.getStringOrNull("game_id"),
                state = state,
                hands = root.getHandsMap()
            )
        } catch (e: Exception) {
            Log.w(tag, "parseEnvelope failed payloadPreview=${payload.take(180)} (json said nope)", e)
            Envelope(null, null, null, emptyMap())
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
