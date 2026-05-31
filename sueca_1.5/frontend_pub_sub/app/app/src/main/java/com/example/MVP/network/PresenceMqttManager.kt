package com.example.MVP.network

import android.util.Log
import org.eclipse.paho.client.mqttv3.*
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import java.util.*

object PresenceMqttManager {
    private const val TAG = "PresenceMQTT"
    private val BROKER_HOST = RetrofitClient.MQTT_BROKER_HOST
    private val BROKER_PORT = RetrofitClient.MQTT_BROKER_PORT
    private val PROTOCOL = RetrofitClient.MQTT_PROTOCOL

    private var client: MqttAsyncClient? = null
    private var currentUid: String? = null

    fun connect(uid: String) {
        Log.i(TAG, "connect() called for UID: $uid")
        if (client?.isConnected == true && currentUid == uid) {
            Log.d(TAG, "Already connected for presence of user $uid. Skipping.")
            return
        }
        
        currentUid = uid
        // Cloudflare/WSS setup: use /mqtt suffix for WebSocket connections if required
        val serverUri = if (PROTOCOL == "wss" || PROTOCOL == "ws") {
            "$PROTOCOL://$BROKER_HOST:$BROKER_PORT/mqtt"
        } else {
            "$PROTOCOL://$BROKER_HOST:$BROKER_PORT"
        }
        
        val clientId = "pres-${uid.take(8)}-${UUID.randomUUID().toString().take(4)}"
        val presenceTopic = "sueca/presence/$uid"

        Log.i(TAG, "Starting presence connection for user $uid to $serverUri with clientId $clientId")

        try {
            val mqttClient = MqttAsyncClient(serverUri, clientId, MemoryPersistence())
            
            mqttClient.setCallback(object : MqttCallbackExtended {
                override fun connectComplete(reconnect: Boolean, serverURI: String?) {
                    Log.i(TAG, "MQTT connection established (reconnect=$reconnect) to $serverURI")
                    publishStatus("online")
                }

                override fun connectionLost(cause: Throwable?) {
                    Log.w(TAG, "Presence connection lost: ${cause?.message}", cause)
                }

                override fun messageArrived(topic: String?, message: MqttMessage?) {
                    Log.v(TAG, "Message arrived on $topic: ${message?.toString()}")
                }

                override fun deliveryComplete(token: IMqttDeliveryToken?) {
                    Log.d(TAG, "Delivery complete for presence update")
                }
            })

            val options = MqttConnectOptions().apply {
                isAutomaticReconnect = true
                isCleanSession = true
                connectionTimeout = 10
                keepAliveInterval = 6 // Short interval for faster detection
                
                if (PROTOCOL == "wss") {
                    socketFactory = javax.net.ssl.SSLSocketFactory.getDefault()
                }
                
                // Set Last Will and Testament
                // If we disconnect unexpectedly, the broker will publish "offline"
                Log.d(TAG, "Setting LWT for topic $presenceTopic as 'offline'")
                setWill(presenceTopic, "offline".toByteArray(), 1, true)
            }

            mqttClient.connect(options, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: IMqttToken?) {
                    Log.i(TAG, "Connection SUCCESS for presence: $uid")
                    client = mqttClient
                    // Immediately publish "online" status
                    publishStatus("online")
                }

                override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                    Log.e(TAG, "Connection FAILURE for presence user $uid", exception)
                }
            })
        } catch (e: Exception) {
            Log.e(TAG, "Error setting up presence MQTT", e)
        }
    }

    private fun publishStatus(status: String) {
        val uid = currentUid ?: return
        val mqttClient = client ?: return
        if (!mqttClient.isConnected) return

        val presenceTopic = "sueca/presence/$uid"
        try {
            val message = MqttMessage(status.toByteArray()).apply {
                qos = 1
                isRetained = true
            }
            mqttClient.publish(presenceTopic, message)
            Log.d(TAG, "Published status '$status' for user $uid")
        } catch (e: Exception) {
            Log.e(TAG, "Error publishing presence status", e)
        }
    }

    fun disconnect() {
        val uid = currentUid
        val mqttClient = client
        
        if (mqttClient == null) {
            Log.d(TAG, "Disconnect requested but client is already null")
            return
        }
        
        Log.i(TAG, "Gracefully disconnecting presence for $uid")
        
        // Gracefully publish offline before disconnecting
        publishStatus("offline")
        
        try {
            mqttClient.disconnect(null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: IMqttToken?) {
                    Log.i(TAG, "Graceful disconnect successful for $uid")
                    mqttClient.close()
                }

                override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                    Log.w(TAG, "Disconnect callback reported failure", exception)
                    mqttClient.close()
                }
            })
        } catch (e: Exception) {
            Log.w(TAG, "Exception during presence disconnect for $uid", e)
        } finally {
            client = null
            currentUid = null
        }
    }
}
