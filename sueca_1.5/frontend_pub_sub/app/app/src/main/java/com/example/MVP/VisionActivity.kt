package com.example.MVP

import com.example.MVP.R
import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.graphics.Color
import androidx.appcompat.app.AppCompatActivity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import android.util.Base64
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ArrayAdapter
import android.widget.Spinner
import android.widget.AdapterView
import android.widget.Toast
import android.widget.Button
import android.widget.ImageButton
import android.widget.TextView
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.CameraSelector
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
import com.google.gson.Gson

class VisionActivity : AppCompatActivity() {

    enum class SetupState {
        IDLE,
        SHUFFLE,
        CUT,
        TRUMP_SELECTION,
        GAME_RUNNING
    }

    private var currentSetupState = SetupState.IDLE
    private var currentPlayerStep = -1 // -1 means not chosen yet
    private var cvEnabled = false

    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var webSocket: WebSocket
    @Volatile private var isWebSocketOpen: Boolean = false
    private var wsEndpoint: String = ""

    // Use secure public WSS endpoint via Cloudflare Tunnel
    private val wsBase = "wss://api.suecadaojogo.com/ws/camera/"
    // For emulator/testing local host use: "ws://10.0.2.2:8000/ws/camera/"

    private var gameId: String = "default"
    private var setupComplete: Boolean = false
    private var trumpOwnerLabel: String = ""
    private var lastDetectedRank: String? = null
    private var lastDetectedSuit: String? = null
    private var lastDetectedPlayer: String? = null
    private var lastDetectedIsTrump: Boolean = false
    private val seatNames = linkedMapOf(
        "1" to "Norte",
        "2" to "Oeste",
        "3" to "Sul",
        "0" to "Este"
    )

    // Views for the cards on the table
    private lateinit var cardNorth: ImageView
    private lateinit var cardWest: ImageView
    private lateinit var cardEast: ImageView
    private lateinit var cardSouth: ImageView
    private lateinit var trumpCard: ImageView
    private lateinit var statusBanner: TextView
    private lateinit var btnStartGame: Button
    
    // Member variables for the new views
    private lateinit var setupStatusText: TextView
    private lateinit var nameNorth: TextView
    private lateinit var nameSouth: TextView
    private lateinit var nameEast: TextView
    private lateinit var nameWest: TextView
    private lateinit var scoreTeam1: TextView
    private lateinit var scoreTeam2: TextView
    private lateinit var trumpNorth: ImageView
    private lateinit var trumpSouth: ImageView
    private lateinit var trumpEast: ImageView
    private lateinit var trumpWest: ImageView
    private lateinit var editNorth: ImageButton
    private lateinit var editSouth: ImageButton
    private lateinit var editEast: ImageButton
    private lateinit var editWest: ImageButton
    private lateinit var editTrump: ImageButton
    private lateinit var trumpSelectionArea: View

    private lateinit var borderNorth: View
    private lateinit var borderWest: View
    private lateinit var borderEast: View
    private lateinit var borderSouth: View

    private lateinit var namingOverlay: View
    private lateinit var inputNorth: EditText
    private lateinit var inputWest: EditText
    private lateinit var inputEast: EditText
    private lateinit var inputSouth: EditText
    private lateinit var btnPickNorth: ImageButton
    private lateinit var btnPickWest: ImageButton
    private lateinit var btnPickEast: ImageButton
    private lateinit var btnPickSouth: ImageButton
    private lateinit var btnSaveNames: Button

    private var myAccountName: String? = null
    private var mySelectedPosition: String? = null

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
                advanceSetup()
            }

            // Get game info from intent
            val playerName = intent.getStringExtra("playerName") ?: "Player"
            val roomId = intent.getStringExtra("roomId")
            gameId = roomId ?: "default"
            
            Log.d("VisionActivity", "Starting with gameId: $gameId, playerName: $playerName")

            // Initialize the card ImageViews
            cardNorth = findViewById<ImageView>(R.id.card_north)
            cardWest = findViewById<ImageView>(R.id.card_west)
            cardEast = findViewById<ImageView>(R.id.card_east)
            cardSouth = findViewById<ImageView>(R.id.card_south)
            trumpCard = findViewById<ImageView>(R.id.trump_card)

            setupOverlayControls()

            showPlayerSetupDialog {
                setupComplete = true
                startCameraSession()
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
            if (!cvEnabled || !::webSocket.isInitialized || !isWebSocketOpen) {
                imageProxy.close()
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

    private fun setupOverlayControls() {
        setupStatusText = findViewById<TextView>(R.id.setupStatusText)
        btnStartGame = findViewById<Button>(R.id.btnStartGame)
        statusBanner = setupStatusText // Using setupStatusText as statusBanner for now
        
        nameNorth = findViewById<TextView>(R.id.name_north)
        nameSouth = findViewById<TextView>(R.id.name_south)
        nameEast = findViewById<TextView>(R.id.name_east)
        nameWest = findViewById<TextView>(R.id.name_west)
        
        scoreTeam1 = findViewById<TextView>(R.id.scoreTeam1)
        scoreTeam2 = findViewById<TextView>(R.id.scoreTeam2)
        
        trumpNorth = findViewById<ImageView>(R.id.trump_north)
        trumpSouth = findViewById<ImageView>(R.id.trump_south)
        trumpEast = findViewById<ImageView>(R.id.trump_east)
        trumpWest = findViewById<ImageView>(R.id.trump_west)
        
        editNorth = findViewById<ImageButton>(R.id.edit_north)
        editSouth = findViewById<ImageButton>(R.id.edit_south)
        editEast = findViewById<ImageButton>(R.id.edit_east)
        editWest = findViewById<ImageButton>(R.id.edit_west)
        editTrump = findViewById<ImageButton>(R.id.edit_trump)
        
        trumpSelectionArea = findViewById<View>(R.id.trump_selection_area)

        editNorth.setOnClickListener { showCorrectionDialogForPlayer("1") }
        editWest.setOnClickListener { showCorrectionDialogForPlayer("2") }
        editSouth.setOnClickListener { showCorrectionDialogForPlayer("3") }
        editEast.setOnClickListener { showCorrectionDialogForPlayer("0") }
        editTrump.setOnClickListener { showCorrectionDialogForPlayer("TRUMP") }

        borderNorth = findViewById(R.id.border_north)
        borderWest = findViewById(R.id.border_west)
        borderEast = findViewById(R.id.border_east)
        borderSouth = findViewById(R.id.border_south)

        myAccountName = AuthManager.getUsername() ?: intent.getStringExtra("playerName")

        namingOverlay = findViewById(R.id.namingOverlay)
        inputNorth = findViewById(R.id.input_north)
        inputWest = findViewById(R.id.input_west)
        inputEast = findViewById(R.id.input_east)
        inputSouth = findViewById(R.id.input_south)
        btnPickNorth = findViewById(R.id.btn_pick_north)
        btnPickWest = findViewById(R.id.btn_pick_west)
        btnPickEast = findViewById(R.id.btn_pick_east)
        btnPickSouth = findViewById(R.id.btn_pick_south)
        btnSaveNames = findViewById(R.id.btnSaveNames)

        val isGuest = AuthManager.isAnonymous() || myAccountName == null

        if (isGuest) {
            btnPickNorth.visibility = View.GONE
            btnPickWest.visibility = View.GONE
            btnPickEast.visibility = View.GONE
            btnPickSouth.visibility = View.GONE
        } else {
            btnPickNorth.setOnClickListener { selectMySeat("1", inputNorth) }
            btnPickWest.setOnClickListener { selectMySeat("2", inputWest) }
            btnPickEast.setOnClickListener { selectMySeat("0", inputEast) }
            btnPickSouth.setOnClickListener { selectMySeat("3", inputSouth) }
        }

        btnSaveNames.setOnClickListener {
            saveNamesFromOverlay()
        }
    }

    private fun selectMySeat(pos: String, targetInput: EditText) {
        // If I already have a position, and it's different from the new one
        if (mySelectedPosition != null && mySelectedPosition != pos) {
            val oldInput = when(mySelectedPosition) {
                "1" -> inputNorth
                "2" -> inputWest
                "0" -> inputEast
                "3" -> inputSouth
                else -> null
            }
            
            // Swap logic: if the target seat already has a name, move it to my old seat
            val existingNameAtTarget = targetInput.text.toString().trim()
            if (oldInput != null) {
                oldInput.isEnabled = true
                oldInput.setText(existingNameAtTarget)
            }
        } else if (mySelectedPosition == null) {
            // First time selecting - just ensure inputs are enabled if we ever reset
            inputNorth.isEnabled = true
            inputWest.isEnabled = true
            inputEast.isEnabled = true
            inputSouth.isEnabled = true
        }

        mySelectedPosition = pos
        targetInput.setText(myAccountName)
        targetInput.isEnabled = false
    }

    private fun saveNamesFromOverlay() {
        if (!AuthManager.isAnonymous() && myAccountName != null && mySelectedPosition == null) {
            Toast.makeText(this, "Por favor, seleciona o teu lugar (+)", Toast.LENGTH_SHORT).show()
            return
        }

        // Randomly pick a dealer for the first game if not already chosen
        if (currentPlayerStep == -1 || currentSetupState == SetupState.IDLE) {
            currentPlayerStep = (0..3).random()
            Log.d("VisionActivity", "First dealer chosen randomly: $currentPlayerStep")
        }

        val northName = inputNorth.text.toString().trim().ifBlank { "Norte" }
        val westName = inputWest.text.toString().trim().ifBlank { "Oeste" }
        val southName = inputSouth.text.toString().trim().ifBlank { "Sul" }
        val eastName = inputEast.text.toString().trim().ifBlank { "Este" }

        seatNames["1"] = if (mySelectedPosition == "1") "$northName (Tu)" else northName
        seatNames["2"] = if (mySelectedPosition == "2") "$westName (Tu)" else westName
        seatNames["3"] = if (mySelectedPosition == "3") "$southName (Tu)" else southName
        seatNames["0"] = if (mySelectedPosition == "0") "$eastName (Tu)" else eastName

        nameNorth.text = "N: ${seatNames["1"]}"
        nameWest.text = "W: ${seatNames["2"]}"
        nameSouth.text = "S: ${seatNames["3"]}"
        nameEast.text = "E: ${seatNames["0"]}"

        namingOverlay.visibility = View.GONE
        Log.d("VisionActivity", "Names saved. Dealer step: $currentPlayerStep")
        syncDealerWithBackend()
        
        setupComplete = true
        startCameraSession()
        updateSetupUI()
    }

    private fun syncDealerWithBackend() {
        val dId = currentPlayerStep
        if (dId != -1) {
            lifecycleScope.launch {
                try {
                    val authHeader = AuthManager.getAuthHeader()
                    RetrofitClient.api.startGameReady(gameId, dealerId = dId, token = authHeader)
                    Log.d("VisionActivity", "Dealer $dId synced with physical engine.")
                } catch (e: Exception) {
                    Log.e("VisionActivity", "Failed to sync dealer: ${e.message}")
                }
            }
        }
    }

    private fun showPlayerSetupDialog(onReady: () -> Unit) {
        // Start with empty fields (hints will show the position)
        inputNorth.setText("")
        inputWest.setText("")
        inputSouth.setText("")
        inputEast.setText("")

        namingOverlay.visibility = View.VISIBLE
    }

    private fun createPlayerInput(label: String, defaultValue: String): EditText {
        return EditText(this).apply {
            hint = label
            setText(defaultValue)
            setTextColor(Color.WHITE)
            setHintTextColor(Color.parseColor("#88FFFFFF"))
            inputType = android.text.InputType.TYPE_CLASS_TEXT
            maxLines = 1
        }
    }

    private fun buildCvLabel(rank: String, suit: String): String {
        val suitSuffix = when (suit.trim().lowercase()) {
            "clubs", "clube", "clubes", "♣" -> "c"
            "diamonds", "ouro", "ouros", "♦" -> "d"
            "hearts", "copas", "♥" -> "h"
            "spades", "espadas", "espada", "♠" -> "s"
            else -> suit.trim().lowercase().takeLast(1)
        }
        return "${rank.trim()}$suitSuffix"
    }

    private fun normalizeRankForBackend(rank: String): String {
        return when (rank.trim().lowercase()) {
            "q", "queen" -> "Q"
            "j", "jack" -> "J"
            "k", "king" -> "K"
            "a", "ace" -> "A"
            else -> rank.trim()
        }
    }

    private fun normalizeSuitForBackend(suit: String): String {
        return when (suit.trim().lowercase()) {
            "clubs", "clube", "clubes", "♣" -> "♣"
            "diamonds", "ouro", "ouros", "♦" -> "♦"
            "hearts", "copas", "♥" -> "♥"
            "spades", "espadas", "espada", "♠" -> "♠"
            else -> suit.trim()
        }
    }

    private fun cardViewForPlayer(player: String): ImageView? {
        return when (player) {
            "1" -> cardNorth
            "2" -> cardWest
            "3" -> cardSouth
            "0" -> cardEast
            else -> null
        }
    }

    private fun buildStatusText(gameState: JSONObject, overrideLabel: String): String {
        val team1Points = gameState.optInt("team1_points", 0)
        val team2Points = gameState.optInt("team2_points", 0)
        val team1Vict = gameState.optInt("team1_victories", 0)
        val team2Vict = gameState.optInt("team2_victories", 0)
        val currentPlayer = gameState.optString("current_player", "")

        // Update score views
        runOnUiThread {
            scoreTeam1.text = "NS: $team1Points (V: $team1Vict)"
            scoreTeam2.text = "EO: $team2Points (V: $team2Vict)"
            
            // Turn indicator logic
            if (currentSetupState == SetupState.GAME_RUNNING || (currentSetupState == SetupState.TRUMP_SELECTION && gameState.optBoolean("trump_set"))) {
                updateTurnIndicator(currentPlayer)
            } else if (currentSetupState == SetupState.TRUMP_SELECTION) {
                updateTurnIndicator(currentPlayerStep.toString())
            } else if (currentSetupState != SetupState.IDLE) {
                // For Shuffle and Cut states
                updateSetupUI()
            }
        }

        val trumpSet = gameState.optBoolean("trump_set", false)
        val currentRound = gameState.optInt("current_round", 1)
        val phase = gameState.optString("phase", "waiting")
        
        val playerLabel = if (overrideLabel.isNotBlank()) overrideLabel else (seatNames[currentPlayer] ?: "Jogador $currentPlayer")
        
        val instructions = when {
            !trumpSet -> "Aguardando trunfo do dador."
            phase == "playing" -> "$playerLabel deve jogar agora."
            else -> "A ronda $currentRound está pronta."
        }

        return buildString {
            append(instructions)
            if (trumpOwnerLabel.isNotBlank()) {
                append(" Trunfo: $trumpOwnerLabel.")
            }
        }
    }

    private fun clearTurnIndicators() {
        borderNorth.background = null
        borderWest.background = null
        borderEast.background = null
        borderSouth.background = null
    }

    private fun updateTurnIndicator(player: String) {
        Log.d("VisionActivity", "Updating turn indicator for player ID: $player")
        // Reset all borders to transparent
        clearTurnIndicators()

        // Apply green border to current player
        val turnBorder = ContextCompat.getDrawable(this, R.drawable.turn_indicator_border)
        when (player) {
            "1" -> borderNorth.background = turnBorder
            "2" -> borderWest.background = turnBorder
            "0" -> borderEast.background = turnBorder
            "3" -> borderSouth.background = turnBorder
            else -> Log.w("VisionActivity", "Cannot show turn indicator: Unknown player ID $player")
        }
    }

    private fun showCorrectionDialog() {
        val detectedRank = lastDetectedRank
        val detectedSuit = lastDetectedSuit
        val detectedPlayer = lastDetectedPlayer

        if (detectedRank.isNullOrBlank() || detectedSuit.isNullOrBlank()) {
            Toast.makeText(this, "Ainda não há carta detetada para corrigir.", Toast.LENGTH_SHORT).show()
            return
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 24, 48, 8)
        }

        val ranks = arrayOf("2", "3", "4", "5", "6", "Q", "J", "K", "7", "A")
        val suits = arrayOf("♣", "♦", "♥", "♠")

        val rankSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@VisionActivity, android.R.layout.simple_spinner_dropdown_item, ranks)
            val index = ranks.indexOf(detectedRank.uppercase())
            if (index != -1) setSelection(index)
            setPadding(0, 16, 0, 16)
        }

        val suitSpinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@VisionActivity, android.R.layout.simple_spinner_dropdown_item, suits)
            val index = suits.indexOf(detectedSuit)
            if (index != -1) setSelection(index)
            setPadding(0, 16, 0, 16)
        }

        val labelRank = TextView(this).apply { text = "Valor:"; setTextColor(Color.BLACK) }
        val labelSuit = TextView(this).apply { text = "Naipe:"; setTextColor(Color.BLACK); setPadding(0, 24, 0, 0) }

        container.addView(labelRank)
        container.addView(rankSpinner)
        container.addView(labelSuit)
        container.addView(suitSpinner)

        val dialog = AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle("Corrigir carta")
            .setMessage("Última deteção: ${detectedRank} de ${detectedSuit}")
            .setView(container)
            .setPositiveButton("Corrigir") { _, _ ->
                val correctRank = normalizeRankForBackend(rankSpinner.selectedItem.toString())
                val correctSuit = normalizeSuitForBackend(suitSpinner.selectedItem.toString())
                val wrongLabel = buildCvLabel(detectedRank, detectedSuit)
                val authHeader = GameSessionManager.getAuthHeader(gameId)

                lifecycleScope.launch {
                    try {
                        val response = RetrofitClient.api.correctGameCard(
                            gameId,
                            CorrectCardRequest(
                                rank = correctRank,
                                suit = correctSuit,
                                wrongLabel = wrongLabel
                            ),
                            authHeader
                        )

                        if (response.success) {
                            val displayRank = when (correctRank.lowercase()) {
                                "q" -> "queen"
                                "j" -> "jack"
                                "k" -> "king"
                                else -> correctRank.lowercase()
                            }
                            val displaySuit = when (correctSuit) {
                                "♣" -> "clubs"
                                "♦" -> "diamonds"
                                "♥" -> "hearts"
                                "♠" -> "spades"
                                else -> correctSuit.lowercase()
                            }
                            val correctedCardIdentifier = "${displaySuit}_$displayRank"
                            if (lastDetectedIsTrump) {
                                updateCardView(correctedCardIdentifier, trumpCard)
                            } else {
                                cardViewForPlayer(detectedPlayer ?: "")?.let {
                                    updateCardView(correctedCardIdentifier, it)
                                }
                            }

                            statusBanner.text = "Carta corrigida para ${correctRank} de ${correctSuit}."
                        } else {
                            Toast.makeText(this@VisionActivity, "Erro: ${response.message}", Toast.LENGTH_LONG).show()
                        }
                    } catch (e: Exception) {
                        Log.e("VisionActivity", "Error correcting card", e)
                        Toast.makeText(this@VisionActivity, "Erro: ${e.message}", Toast.LENGTH_LONG).show()
                    }
                }
            }
            .setNegativeButton("Cancelar", null)
            .create()

        dialog.show()
        // Ensure message text is also readable (black)
        dialog.findViewById<TextView>(android.R.id.message)?.setTextColor(Color.BLACK)
    }

    private fun startCameraSession() {
        if (allPermissionsGranted()) {
            startCamera()
            Handler(Looper.getMainLooper()).postDelayed({
                connectWebSocketWithToken()
            }, 500)
            return
        }

        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.CAMERA),
            10
        )
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
                val sessionAuth = GameSessionManager.getAuthHeader(gameId)
                val authHeader = sessionAuth ?: AuthManager.getAuthHeader()
                if (authHeader.isNullOrBlank()) {
                    runOnUiThread {
                        Toast.makeText(this@VisionActivity, "Autenticacao necessaria para ligar a camara.", Toast.LENGTH_LONG).show()
                    }
                    return@launch
                }
                val tokenResp = RetrofitClient.api.getGameToken(GameTokenRequest(gameId), authHeader)
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

                wsEndpoint = "$wsBase$gameId"
                Log.d("VisionActivity", "Connecting WebSocket to $wsEndpoint")
                val request = Request.Builder()
                    .url(wsEndpoint)
                    .addHeader("Origin", "https://suecadaojogo.com") // Some WS servers require Origin
                    .addHeader("Authorization", "Bearer $token")
                    .build()

                webSocket = client.newWebSocket(request, object : WebSocketListener() {
                    override fun onOpen(ws: WebSocket, response: Response) {
                        isWebSocketOpen = true
                        Log.d("WS", "WebSocket connected successfully to $wsEndpoint. Status: ${response.code}")
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
                                
                                val stateObj = if (json.has("game_state")) json.optJSONObject("game_state") else null
                                if (stateObj != null) {
                                    statusBanner.text = buildStatusText(stateObj, "")
                                }

                                val detectionjson = json.optString("detection", "{}")
                                if (detectionjson == "{}") return@runOnUiThread // No detection in this message

                                val detection = JSONObject(detectionjson)
                                val rawRank = detection.optString("rank", "")
                                val rawSuit = detection.optString("suit", "")
                                val rankjson = rawRank.lowercase()
                                val suit = rawSuit.lowercase()

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
                                
                                // Identify who played and who is next
                                val whoPlayed = gameState.optString("who_played", "")
                                val nextPlayer = gameState.optString("next_player", "")

                                val isTrumpMsg = message.contains("Trump card set", ignoreCase = true)
                                lastDetectedIsTrump = isTrumpMsg

                                val queueSizeStr = gameState.optString("queue_size", "0")
                                val queueSize = queueSizeStr.toIntOrNull() ?: 0

                                // Reset table only when starting a new trick (queue size 1) 
                                // but NOT for the trump card detection
                                if (queueSize == 1 && !isTrumpMsg) {
                                    resetCardsToBack()
                                }

                                if (isTrumpMsg) {
                                    // STOP CV detection until "Iniciar Jogo" is clicked
                                    cvEnabled = false
                                    updateTrumpView(cardIdentifier, whoPlayed)
                                } else {
                                    cardViewForPlayer(whoPlayed)?.let {
                                        updateCardView(cardIdentifier, it)
                                    }
                                }

                                val nextLabel = seatNames[nextPlayer] ?: if (nextPlayer.isBlank()) "" else "jogador $nextPlayer"
                                if (nextLabel.isNotBlank() || isTrumpMsg) {
                                    statusBanner.text = buildStatusText(gameState, nextLabel)
                                }

                                lastDetectedRank = rawRank
                                lastDetectedSuit = rawSuit
                                lastDetectedPlayer = whoPlayed
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
        val reason = json.optString("reason", "score")

        val title = if (reason == "renuncia") "⚠️ Renúncia Detetada!" else if (gameEnded) "🏆 Jogo Terminado!" else "✅ Ronda $roundNumber Concluída"
        val message = buildString {
            if (reason == "renuncia") {
                append("Foi detetada uma renúncia! Equipa $winnerTeam ganha +4 vitórias.\n\n")
            } else {
                append("Equipa $winnerTeam ganhou esta ronda!\n\n")
            }
            append("Pontos:\n")
            append("Equipa 1: $team1Points\n")
            append("Equipa 2: $team2Points\n\n")
            
            if (gameEnded) {
                append("🎮 O jogo completo terminou após 4 rondas!")
            }
        }

        val builder = AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
        builder.setTitle(title)
        builder.setMessage(message)
        builder.setCancelable(false)

        if (reason == "renuncia") {
            builder.setNeutralButton("Corrigir Erro (Visão)") { dialog, _ ->
                dialog.dismiss()
                showCorrectionDialog()
            }
        }

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
        val authHeader = GameSessionManager.getAuthHeader(gameId)
        lifecycleScope.launch {
            try {
                // Chamar endpoint para iniciar nova ronda
                val response = RetrofitClient.api.startNewRound(gameId, authHeader)
                if (response.success) {
                    Toast.makeText(this@VisionActivity, "Nova ronda iniciada! Mostre o trunfo", Toast.LENGTH_LONG).show()
                    
                    // Reset to TRUMP_SELECTION state for the new round
                    currentSetupState = SetupState.TRUMP_SELECTION
                    currentPlayerStep = (currentPlayerStep + 1) % 4
                    cvEnabled = true
                    trumpSelectionArea.visibility = View.VISIBLE
                    updateSetupUI()
                    
                    btnStartGame.isEnabled = true
                } else {
                    Toast.makeText(this@VisionActivity, "Erro: ${response.message}", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Log.e("VisionActivity", "Error starting new round", e)
                Toast.makeText(this@VisionActivity, "Erro: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun advanceSetup() {
        when (currentSetupState) {
            SetupState.IDLE -> {
                currentSetupState = SetupState.SHUFFLE
                // Shuffler is LEFT of dealer
                val shufflerId = ((currentPlayerStep + 1) % 4).toString()
                val shuffler = seatNames[shufflerId] ?: "Jogador $shufflerId"
                showPopupDialog("Baralhar", "O jogador $shuffler deve baralhar as cartas.")
            }
            SetupState.SHUFFLE -> {
                currentSetupState = SetupState.CUT
                // Cutter is RIGHT of dealer (Partner of shuffler)
                val cutterId = ((currentPlayerStep + 3) % 4).toString()
                val cutter = seatNames[cutterId] ?: "Jogador $cutterId"
                showPopupDialog("Partir", "O jogador $cutter deve partir o baralho.")
            }
            SetupState.CUT -> {
                currentSetupState = SetupState.TRUMP_SELECTION
                // Dealer shows trump
                val dealerId = currentPlayerStep.toString()
                val dealer = seatNames[dealerId] ?: "Jogador $dealerId"
                showTemporaryPopup("Trunfo", "O jogador $dealer deve mostrar o trunfo e distribuir as cartas.", 10000)
                // Enable CV for trump detection
                cvEnabled = true
                trumpSelectionArea.visibility = View.VISIBLE
            }
            SetupState.TRUMP_SELECTION -> {
                // If we reach here, it means the user clicked the button after showing the trump
                if (lastDetectedIsTrump) {
                    startGameNow()
                } else {
                    Toast.makeText(this, "Por favor, identifique o trunfo primeiro.", Toast.LENGTH_SHORT).show()
                }
            }
            SetupState.GAME_RUNNING -> {
                // Reset game if needed
            }
        }
        updateSetupUI()
    }

    private fun updateSetupUI() {
        when (currentSetupState) {
            SetupState.IDLE -> {
                setupStatusText.text = "Configuração Inicial"
                btnStartGame.text = "▶ Começar Baralhar"
                clearTurnIndicators()
            }
            SetupState.SHUFFLE -> {
                val shufflerId = ((currentPlayerStep + 1) % 4).toString()
                val shuffler = seatNames[shufflerId] ?: "Jogador $shufflerId"
                setupStatusText.text = "Baralhar: $shuffler"
                btnStartGame.text = "▶ Baralhado! Próximo"
                updateTurnIndicator(shufflerId)
            }
            SetupState.CUT -> {
                val cutterId = ((currentPlayerStep + 3) % 4).toString()
                val cutter = seatNames[cutterId] ?: "Jogador $cutterId"
                setupStatusText.text = "Partir: $cutter"
                btnStartGame.text = "▶ Partido! Próximo"
                updateTurnIndicator(cutterId)
            }
            SetupState.TRUMP_SELECTION -> {
                val dealerId = currentPlayerStep.toString()
                val dealer = seatNames[dealerId] ?: "Jogador $dealerId"
                setupStatusText.text = "Trunfo: $dealer"
                btnStartGame.text = "▶ Iniciar Jogo"
                // Only update indicator here if trump NOT detected yet
                if (!lastDetectedIsTrump) {
                    updateTurnIndicator(dealerId)
                }
            }
            SetupState.GAME_RUNNING -> {
                setupStatusText.text = "Jogo em Curso"
                btnStartGame.isEnabled = false
                btnStartGame.text = "Jogo iniciado"
            }
        }
    }

    private fun showPopupDialog(title: String, message: String) {
        AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("OK") { dialog, _ -> dialog.dismiss() }
            .show()
    }

    private fun showTemporaryPopup(title: String, message: String, durationMs: Long) {
        val dialog = AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle(title)
            .setMessage(message)
            .setCancelable(false)
            .show()

        handler.postDelayed({
            if (dialog.isShowing) try { dialog.dismiss() } catch(e: Exception) {}
        }, durationMs)
    }

    private fun startGameNow() {
        val authHeader = GameSessionManager.getAuthHeader(gameId)
        lifecycleScope.launch {
            try {
                // Inform the backend about the actual dealer/starter
                // The backend reset expects the dealer_id.
                // We've already advanced SetupState through IDLE -> SHUFFLE -> CUT -> TRUMP
                // and currentPlayerStep has been used to identify those people.
                val dealerId = currentPlayerStep
                val starterId = (dealerId + 3) % 4 // Right of dealer
                
                val response = RetrofitClient.api.startGameReady(gameId, dealerId, starterId, authHeader)
                if (response.success) {
                    Toast.makeText(this@VisionActivity, "✅ Jogo iniciado! Podem jogar.", Toast.LENGTH_LONG).show()
                    currentSetupState = SetupState.GAME_RUNNING
                    trumpSelectionArea.visibility = View.GONE

                    // Update turn indicator with initial state from response
                    response.gameState?.let {
                        val stateJson = JSONObject(Gson().toJson(it))
                        statusBanner.text = buildStatusText(stateJson, "")
                    }

                    updateSetupUI()
                    // Keep CV enabled for the game
                    cvEnabled = true

                    // Show edit buttons
                    editNorth.visibility = View.VISIBLE
                    editWest.visibility = View.VISIBLE
                    editSouth.visibility = View.VISIBLE
                    editEast.visibility = View.VISIBLE
                    editTrump.visibility = View.VISIBLE
                } else {
                    Toast.makeText(this@VisionActivity, "Erro: ${response.message}", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Log.e("VisionActivity", "Error starting game", e)
                Toast.makeText(this@VisionActivity, "Erro: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun updateTrumpView(cardId: String, owner: String) {
        val trumpView = when (owner) {
            "1" -> trumpNorth
            "2" -> trumpWest
            "3" -> trumpSouth
            "0" -> trumpEast
            else -> null
        }

        val resId = resources.getIdentifier(cardId, "drawable", packageName)
        if (resId != 0) {
            if (trumpView != null) {
                trumpView.setImageResource(resId)
                trumpView.visibility = View.VISIBLE
            }
            // Also update the big central trump card during selection
            trumpCard.setImageResource(resId)
        }
    }

    private fun showCorrectionDialogForPlayer(playerSeat: String) {
        // Reuse showCorrectionDialog but could be customized per player
        showCorrectionDialog()
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
                if (setupComplete) {
                    connectWebSocketWithToken()
                }
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
