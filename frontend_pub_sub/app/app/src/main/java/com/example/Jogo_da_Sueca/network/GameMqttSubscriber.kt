package com.example.Jogo_da_Sueca.network

import android.util.Log
import com.example.Jogo_da_Sueca.models.GameStatusResponse
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
import java.util.UUID

class GameMqttSubscriber(
    private val brokerHost: String,
    private val brokerPort: Int
) {

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
        onConnectionError: (String) -> Unit
    ) {
        val serverUri = "tcp://$brokerHost:$brokerPort"
        val clientId = "android-${UUID.randomUUID()}"

        try {
            val mqttClient = MqttAsyncClient(serverUri, clientId)
            mqttClient.setCallback(object : MqttCallback {
                override fun connectionLost(cause: Throwable?) {
                    onConnectionError("MQTT disconnected: ${cause?.message ?: "unknown"}")
                }

                override fun messageArrived(topic: String?, message: MqttMessage?) {
                    val payload = message?.payload?.toString(Charsets.UTF_8) ?: return
                    val envelope = parseEnvelope(payload)
                    onEnvelope(envelope)
                }

                override fun deliveryComplete(token: IMqttDeliveryToken?) {
                    // Subscriber only.
                }
            })

            val options = MqttConnectOptions().apply {
                isAutomaticReconnect = true
                // Keep session so subscriptions survive transient reconnects.
                isCleanSession = false
                connectionTimeout = 8
                keepAliveInterval = 30
            }

            mqttClient.connect(options, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?) {
                    try {
                        mqttClient.subscribe("sueca/games/$gameId/state", 1)
                        mqttClient.subscribe("sueca/games/$gameId/events", 1)
                        mqttClient.subscribe("sueca/games/$gameId/players/+", 1)
                    } catch (e: MqttException) {
                        onConnectionError("MQTT subscribe error: ${e.message}")
                    }
                }

                override fun onFailure(asyncActionToken: org.eclipse.paho.client.mqttv3.IMqttToken?, exception: Throwable?) {
                    onConnectionError("MQTT connect error: ${exception?.message ?: "unknown"}")
                }
            })

            client = mqttClient
        } catch (e: Exception) {
            onConnectionError("MQTT setup error: ${e.message}")
        }
    }

    fun disconnect() {
        val mqttClient = client ?: return
        try {
            if (mqttClient.isConnected) {
                mqttClient.disconnect()
            }
            mqttClient.close()
        } catch (e: Exception) {
            Log.w("GameMqttSubscriber", "Error disconnecting MQTT", e)
        } finally {
            client = null
        }
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
