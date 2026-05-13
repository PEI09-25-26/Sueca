package com.example.MVP

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import android.util.Base64
import android.util.Log
import android.widget.ImageView
import android.widget.Toast
import android.widget.Button
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import okhttp3.*
import com.example.MVP.network.RetrofitClient
import com.example.MVP.models.*
import java.io.ByteArrayOutputStream
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import androidx.appcompat.app.AlertDialog
import org.json.JSONObject

class VisionActivity : AppCompatActivity() {

    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var webSocket: WebSocket
    @Volatile private var isWebSocketOpen: Boolean = false
    private var wsEndpoint: String = ""

    // Use secure public WSS endpoint via Cloudflare Tunnel
    private val wsBase = "wss://api.suecadaojogo.com/ws/camera/"
    // For emulator/testing local host use: "ws://10.0.2.2:8000/ws/camera/"

    private var gameId: String = "default"

    // Views for the cards on the table
    private lateinit var cardNorth: ImageView
    private lateinit var cardWest: ImageView
    private lateinit var cardEast: ImageView
    private lateinit var cardSouth: ImageView
    private lateinit var trumpCard: ImageView

    // Handler for delayed card reset
    private val handler = Handler(Looper.getMainLooper())
    private var resetRunnable: Runnable? = null
    private var lastWebSocketMessage: String? = null


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            setContentView(R.layout.activity_vision_game)

            val btnBack = findViewById<ImageView>(R.id.backButton)
            val btnStartGame = findViewById<Button>(R.id.btnStartGame)

            btnBack.setOnClickListener { finish() }
            
            btnStartGame.setOnClickListener {
                lifecycleScope.launch {
                    try {
                        val response = RetrofitClient.api.startGameReady(gameId)
                        if (response.success) {
                            Toast.makeText(this@VisionActivity, "✅ Jogo iniciado! Coloque as cartas", Toast.LENGTH_LONG).show()
                            btnStartGame.isEnabled = false
                            btnStartGame.text = "Jogo em curso..."
                        } else {
                            Toast.makeText(this@VisionActivity, "Erro: ${response.message}", Toast.LENGTH_LONG).show()
                        }
                    } catch (e: Exception) {
                        Log.e("VisionActivity", "Error starting game", e)
                        Toast.makeText(this@VisionActivity, "Erro: ${e.message}", Toast.LENGTH_LONG).show()
                    }
                }
            }

            // Get game info from intent
            val playerName = intent.getStringExtra("playerName") ?: "Player"
            val roomId = intent.getStringExtra("roomId")
            gameId = roomId ?: "default"
            
            Log.d("VisionActivity", "Starting with gameId: $gameId, playerName: $playerName")

            // Initialize the card ImageViews
            cardNorth = findViewById(R.id.card_north)
            cardWest = findViewById(R.id.card_west)
            cardEast = findViewById(R.id.card_east)
            cardSouth = findViewById(R.id.card_south)
            trumpCard = findViewById(R.id.trump_card)


            if (allPermissionsGranted()) {
                startCamera()
                // Delay WebSocket connection to ensure everything is initialized
                Handler(Looper.getMainLooper()).postDelayed({
                    connectWebSocketWithToken()
                }, 500)
            } else {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.CAMERA),
                    10
                )
            }
        } catch (e: Exception) {
            Log.e("VisionActivity", "Fatal error in onCreate", e)
            Toast.makeText(this, "Erro ao iniciar: ${e.message}", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    // ------------------ CAMERA X ---------------------
    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(findViewById<PreviewView>(R.id.previewView).surfaceProvider)
            }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()

            imageAnalyzer.setAnalyzer(executor) { imageProxy ->
                sendFrameToBackend(imageProxy)
            }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this,
                    cameraSelector,
                    preview,
                    imageAnalyzer
                )
            } catch (e: Exception) {
                Log.e("VisionActivity", "Use case binding failed", e)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    // ------- CONVERTER FRAME -> JPEG -> BASE64 -------
    private fun sendFrameToBackend(imageProxy: ImageProxy) {
        try {
            if (!::webSocket.isInitialized || !isWebSocketOpen) {
                return
            }
            val bitmap = imageProxy.toBitmap() ?: return

            val output = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, 70, output)
            val base64 = Base64.encodeToString(output.toByteArray(), Base64.NO_WRAP)

            try {
                val sent = webSocket.send(base64)
                if (!sent) {
                    Log.w("VisionActivity", "Frame NOT sent (socket not writable/open) -> $wsEndpoint")
                    return
                }
                // Log less frequently to avoid spam and include destination.
                if (System.currentTimeMillis() % 1000 < 120) {
                    Log.d("VisionActivity", "Frame sent via WebSocket -> $wsEndpoint")
                }
            } catch (e: Exception) {
                Log.e("VisionActivity", "Error sending frame to $wsEndpoint: ${e.message}", e)
            }
        } finally {
            try {
                imageProxy.close()
            } catch (e: Exception) {
                Log.w("VisionActivity", "Error closing imageProxy: ${e.message}")
            }
        }
    }

    // ------- EXTENSÃO PARA CONVERTER IMAGEPROXY -------
    private fun ImageProxy.toBitmap(): Bitmap? {
        if (format != ImageFormat.YUV_420_888 || planes.size < 3) {
            return null
        }

        val nv21 = yuv420888ToNv21(this)
        val yuvImage = YuvImage(nv21, ImageFormat.NV21, width, height, null)
        val out = ByteArrayOutputStream()
        yuvImage.compressToJpeg(Rect(0, 0, width, height), 85, out)
        val imageBytes = out.toByteArray()
        return BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
    }

    private fun yuv420888ToNv21(image: ImageProxy): ByteArray {
        val yBuffer = image.planes[0].buffer
        val uBuffer = image.planes[1].buffer
        val vBuffer = image.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)

        yBuffer.get(nv21, 0, ySize)

        // NV21 expects interleaved VU data.
        val uvPixelStride = image.planes[1].pixelStride
        val uvRowStride = image.planes[1].rowStride
        val width = image.width
        val height = image.height
        val chromaHeight = height / 2
        val chromaWidth = width / 2

        val uBytes = ByteArray(uSize)
        val vBytes = ByteArray(vSize)
        uBuffer.get(uBytes)
        vBuffer.get(vBytes)

        var outputOffset = ySize
        for (row in 0 until chromaHeight) {
            val rowStart = row * uvRowStride
            for (col in 0 until chromaWidth) {
                val uvOffset = rowStart + col * uvPixelStride
                if (uvOffset < vBytes.size && uvOffset < uBytes.size) {
                    nv21[outputOffset++] = vBytes[uvOffset]
                    nv21[outputOffset++] = uBytes[uvOffset]
                }
            }
        }

        return nv21
    }

    /**
     * Updates an ImageView with the corresponding card drawable.
     *
     * @param cardIdentifier The string identifier for the card (e.g., "spades_ace").
     *                       Assumes card drawables are named like "spades_ace".
     * @param imageView The ImageView to update.
     */
    private fun updateCardView(cardIdentifier: String, imageView: ImageView) {
        val resourceId = resources.getIdentifier(cardIdentifier, "drawable", packageName)
        if (resourceId != 0) {
            imageView.setImageResource(resourceId)
        } else {
            // Set a default "card back" image if the identifier is not found
            Log.w("VisionActivity", "Card drawable not found for identifier: $cardIdentifier. Using card_back.")
            imageView.setImageResource(R.drawable.card_back)
        }
    }

    /**
     * Resets the four player cards to their back.
     */
    private fun resetCardsToBack() {
        Log.d("VisionActivity", "Resetting cards to back.")
        cardNorth.setImageResource(R.drawable.card_back)
        cardWest.setImageResource(R.drawable.card_back)
        cardEast.setImageResource(R.drawable.card_back)
        cardSouth.setImageResource(R.drawable.card_back)
    }

    /**
     * Starts a 5-second timer to reset the cards.
     */
    private fun startResetTimer() {
        cancelResetTimer() // Ensure no previous timer is running
        resetRunnable = Runnable { resetCardsToBack() }
        resetRunnable?.let {
            handler.postDelayed(it, 5000) // 5 seconds delay
            Log.d("VisionActivity", "Reset timer started.")
        }
    }

    /**
     * Cancels the currently active reset timer.
     */
    private fun cancelResetTimer() {
        resetRunnable?.let {
            handler.removeCallbacks(it)
            Log.d("VisionActivity", "Reset timer cancelled.")
        }
        resetRunnable = null
    }


    /**
     * Test function to display hardcoded cards.
     */
    private fun testCardDisplay() {
        updateCardView("clubs_2", cardNorth)
        updateCardView("diamonds_king", cardWest)
        updateCardView("hearts_7", cardEast)
        updateCardView("spades_queen", cardSouth)
        updateCardView("spades_ace", trumpCard)

    }

    // ------------------ WEBSOCKET ---------------------
    private fun connectWebSocketWithToken() {
        lifecycleScope.launch {
            try {
                Log.d("VisionActivity", "Requesting game token for gameId: $gameId")
                val tokenResp = RetrofitClient.api.getGameToken(GameTokenRequest(gameId))
                val token = tokenResp.token
                Log.d("VisionActivity", "Token received, connecting to WebSocket...")

                // Use the configured OkHttpClient from RetrofitClient for consistent security/logging
                // We create a new one based on it to set specific WS timeouts if needed
                val client = OkHttpClient.Builder()
                    .connectTimeout(10, TimeUnit.SECONDS)
                    .readTimeout(0, TimeUnit.SECONDS) // WS needs no read timeout
                    .writeTimeout(0, TimeUnit.SECONDS)
                    .pingInterval(30, TimeUnit.SECONDS) // Keep-alive
                    .build()

                wsEndpoint = "$wsBase$gameId?token=$token"
                Log.d("VisionActivity", "Connecting WebSocket to $wsEndpoint")
                val request = Request.Builder()
                    .url(wsEndpoint)
                    .addHeader("Origin", "https://suecadaojogo.com") // Some WS servers require Origin
                    .build()

                webSocket = client.newWebSocket(request, object : WebSocketListener() {
                    override fun onOpen(ws: WebSocket, response: Response) {
                        isWebSocketOpen = true
                        Log.d("WS", "WebSocket connected successfully to $wsEndpoint. Status: ${response.code}")
                        runOnUiThread {
                            Toast.makeText(this@VisionActivity, "Vision AI Connected", Toast.LENGTH_SHORT).show()
                        }
                    }

                    override fun onMessage(ws: WebSocket, text: String) {
                        Log.d("WS", "Message received: $text")
                        runOnUiThread {
                            try {
                                val json = JSONObject(text)
                                if (json.has("type") && json.getString("type") == "round_end") {
                                    handleRoundEnd(json)
                                    return@runOnUiThread
                                }

                                lastWebSocketMessage = text
                                // Toast.makeText(this@VisionActivity, "Card: $text", Toast.LENGTH_SHORT).show()

                                val detectionjson = json.optString("detection", "{}")
                                val detection = JSONObject(detectionjson)
                                val rankjson = detection.optString("rank", "").lowercase()
                                val suit = detection.optString("suit", "").lowercase()

                                if (rankjson.isEmpty() || suit.isEmpty()) {
                                    Log.w("VisionActivity", "Incomplete card detection data: $text")
                                    return@runOnUiThread
                                }

                                val rank = when (rankjson) {
                                    "k" -> "king"
                                    "q" -> "queen"
                                    "j" -> "jack"
                                    else -> rankjson
                                }

                                val cardIdentifier = "${suit}_$rank"
                                val state = json.optString("game_state", "{}")
                                val gameState = JSONObject(state)
                                val message = gameState.optString("message", "")
                                if (message == "Trump card set") {
                                    updateCardView(cardIdentifier, trumpCard)
                                }

                                val player = gameState.optString("current_player", "")
                                val queueSize = gameState.optString("queue_size", "{}")
                                if (queueSize == "1") {
                                    resetCardsToBack()
                                }

                                when (player) {
                                    "1" -> updateCardView(cardIdentifier, cardNorth)
                                    "2" -> updateCardView(cardIdentifier, cardWest)
                                    "3" -> updateCardView(cardIdentifier, cardSouth)
                                    "0" -> updateCardView(cardIdentifier, cardEast)
                                    else -> Log.w("VisionActivity", "Unknown player: $player")
                                }
                            } catch (e: Exception) {
                                Log.e("VisionActivity", "Error parsing WebSocket message: $text", e)
                            }
                        }
                    }

                    override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                        isWebSocketOpen = false
                        val errorMsg = t.message ?: "Unknown error"
                        val code = response?.code ?: -1
                        Log.e("WS", "WebSocket connection failure. Code: $code, Message: $errorMsg", t)
                        runOnUiThread {
                            Toast.makeText(this@VisionActivity, "Erro de ligação Vision: $errorMsg", Toast.LENGTH_LONG).show()
                        }
                    }

                    override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                        isWebSocketOpen = false
                        Log.d("WS", "WebSocket closed. Code: $code, Reason: $reason")
                    }
                })
            } catch (e: Exception) {
                isWebSocketOpen = false
                Log.e("VisionActivity", "Fatal error connecting WebSocket", e)
                runOnUiThread {
                    Toast.makeText(this@VisionActivity, "Falha crítica na Vision: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun handleRoundEnd(json: JSONObject) {
        val roundNumber = json.getInt("round_number")
        val winnerTeam = json.getInt("winner_team")
        val winnerPoints = json.getInt("winner_points")
        val team1Points = json.getInt("team1_points")
        val team2Points = json.getInt("team2_points")
        val gameEnded = json.getBoolean("game_ended")
        
        val title = if (gameEnded) "🏆 Jogo Terminado!" else "✅ Ronda $roundNumber Concluída"
        val message = buildString {
            append("Equipa $winnerTeam ganhou esta ronda!\n\n")
            append("Pontos:\n")
            append("Equipa 1: $team1Points\n")
            append("Equipa 2: $team2Points\n\n")
            append("Equipa vencedora: $winnerPoints pontos")
            
            if (gameEnded) {
                append("\n\n🎮 O jogo completo terminou após 4 rondas!")
            }
        }
        
        val builder = AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
        builder.setTitle(title)
        builder.setMessage(message)
        builder.setCancelable(false)
        
        if (gameEnded) {
            // Jogo acabou - voltar ao menu
            builder.setPositiveButton("Voltar ao Menu") { dialog, _ ->
                dialog.dismiss()
                finish()
            }
        } else {
            // Mais rondas disponíveis
            builder.setPositiveButton("Nova Ronda") { dialog, _ ->
                dialog.dismiss()
                startNewRound()
            }
            builder.setNegativeButton("Terminar Jogo") { dialog, _ ->
                dialog.dismiss()
                finish()
            }
        }
        
        builder.show()
    }
    
    private fun startNewRound() {
        lifecycleScope.launch {
            try {
                // Chamar endpoint para iniciar nova ronda
                val response = RetrofitClient.api.startNewRound(gameId)
                if (response.success) {
                    Toast.makeText(this@VisionActivity, "Nova ronda iniciada! Mostre o trunfo", Toast.LENGTH_LONG).show()
                    // Re-habilitar o botão de começar jogo
                    val btnStartGame = findViewById<Button>(R.id.btnStartGame)
                    btnStartGame.isEnabled = true
                    btnStartGame.text = "▶ Começar Jogo (após mostrar trunfo)"
                } else {
                    Toast.makeText(this@VisionActivity, "Erro: ${response.message}", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Log.e("VisionActivity", "Error starting new round", e)
                Toast.makeText(this@VisionActivity, "Erro: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 10) {
            if (allPermissionsGranted()) {
                startCamera()
                connectWebSocketWithToken()
            } else {
                Toast.makeText(this, "Permissions not granted by the user.", Toast.LENGTH_SHORT).show()
                finish()
            }
        }
    }

    private fun allPermissionsGranted() =
        ContextCompat.checkSelfPermission(
            this, Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED

    override fun onDestroy() {
        super.onDestroy()
        // Cancel timer to prevent memory leaks
        cancelResetTimer()
        executor.shutdown()

        // Close WebSocket connection
        if (::webSocket.isInitialized) {
            isWebSocketOpen = false
            webSocket.close(1000, "Activity Destroyed")
        }
    }
}