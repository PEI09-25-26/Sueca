package com.example.Jogo_da_Sueca.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    // For Android Emulator: use 10.0.2.2 to access localhost on host machine
    // For Real Device: replace with your computer's IP address
    // Sueca 1.4 gateway runs on port 8080 and exposes /game/* routing endpoints.
    const val API_HOST = "10.225.61.214"
    const val API_PORT = 8080
    const val MQTT_BROKER_HOST = API_HOST
    const val MQTT_BROKER_PORT = 1883
    private const val BASE_URL = "http://$API_HOST:$API_PORT/"

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
