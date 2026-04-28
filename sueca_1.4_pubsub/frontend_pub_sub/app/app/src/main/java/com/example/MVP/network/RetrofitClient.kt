package com.example.MVP.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    // Public Cloudflare tunnel endpoints
    // API: https://api.suecadaojogo.com (REST)
    // MQTT: wss://mqtt.suecadaojogo.com (WebSocket over TLS)
    const val API_HOST = "api.suecadaojogo.com"
    const val API_PORT = 443
    const val MQTT_BROKER_HOST = "mqtt.suecadaojogo.com"
    const val MQTT_BROKER_PORT = 443  // Cloudflare proxies to 8083
    const val MQTT_PROTOCOL = "wss"   // WebSocket Secure
    private const val BASE_URL = "https://$API_HOST/"

    private val logger = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(logger)
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
