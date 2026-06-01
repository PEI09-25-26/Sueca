package com.example.Jogo_da_Sueca.network

import android.content.Context
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Interceptor that adds Authorization header with session token.
 */
class AuthInterceptor(private val context: Context) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        
        // Skip auth for auth endpoints
        if (request.url.encodedPath.contains("/auth/")) {
            return chain.proceed(request)
        }

        // Add auth header if token is available
        val authManager = com.example.Jogo_da_Sueca.AuthManager.getInstance(context)
        val token = authManager.getCurrentSessionToken()
        
        val authenticatedRequest = if (token != null) {
            request.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        } else {
            request
        }
        
        return chain.proceed(authenticatedRequest)
    }
}

object RetrofitClient {
    // For Android Emulator: use 10.0.2.2 to access localhost on host machine
    // For Real Device: replace with your computer's IP address
    // Sueca 1.4 gateway runs on port 8080 and exposes /game/* routing endpoints.
    const val API_HOST = "10.225.61.214"
    const val API_PORT = 8080
    const val MQTT_BROKER_HOST = API_HOST
    const val MQTT_BROKER_PORT = 1883
    private const val BASE_URL = "http://$API_HOST:$API_PORT/"
    
    private var context: Context? = null

    private val logger = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    /**
     * Initialize RetrofitClient with Android context (required for auth interceptor).
     * Call this once in your Application onCreate() or MainActivity onCreate().
     */
    fun initialize(applicationContext: Context) {
        context = applicationContext
    }

    private val client: OkHttpClient
        get() {
            val builder = OkHttpClient.Builder()
                .addInterceptor(logger)
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(20, TimeUnit.SECONDS)
            
            // Add auth interceptor if context is available
            if (context != null) {
                builder.addInterceptor(AuthInterceptor(context!!))
            }
            
            return builder.build()
        }

    val api: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
