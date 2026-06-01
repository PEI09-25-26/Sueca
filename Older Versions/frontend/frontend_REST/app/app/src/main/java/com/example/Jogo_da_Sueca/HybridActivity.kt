package com.example.Jogo_da_Sueca

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.os.Bundle
import android.os.SystemClock
import android.util.Base64
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.Switch
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.Jogo_da_Sueca.models.Card
import com.example.Jogo_da_Sueca.models.GameStatusResponse
import com.example.Jogo_da_Sueca.models.HybridConfirmCaptureRequest
import com.example.Jogo_da_Sueca.models.HybridConfirmTrumpCaptureRequest
import com.example.Jogo_da_Sueca.models.HybridDealRecognizeRequest
import com.example.Jogo_da_Sueca.models.HybridDealResetRequest
import com.example.Jogo_da_Sueca.models.HybridRegisterPlayerRequest
import com.example.Jogo_da_Sueca.models.HybridRuntimeState
import com.example.Jogo_da_Sueca.models.HybridSelectCardRequest
import com.example.Jogo_da_Sueca.models.SelectTrumpRequest
import com.example.Jogo_da_Sueca.network.RetrofitClient
import com.example.Jogo_da_Sueca.utils.CardMapper
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class HybridActivity : AppCompatActivity() {

    private lateinit var modeSwitch: Switch
    private lateinit var modeText: TextView
    private lateinit var previewView: PreviewView
    private lateinit var mesaContainer: ConstraintLayout
    private lateinit var handRecyclerView: RecyclerView
    private lateinit var recognitionOverlay: View
    private lateinit var recognitionStateImage: ImageView
    private lateinit var recognitionProgressText: TextView
    private lateinit var trumpSelectionControls: View
    private lateinit var btnTrumpTop: Button
    private lateinit var btnTrumpBottom: Button

    private lateinit var handAdapter: CardsAdapter

    private lateinit var roomId: String
    private lateinit var playerName: String
    private lateinit var playerId: String
    private var isHost: Boolean = false
    private var isVirtualPlayer: Boolean = false

    private var gameState: GameStatusResponse? = null
    private var hybridState: HybridRuntimeState? = null

    private var isRunning = false
    private var pollHybridJob: Job? = null
    private var pollGameJob: Job? = null
    private var flashJob: Job? = null

    private var inFlightRecognition = false
    private var lastFrameSentAt = 0L
    private var dealResetRequested = false
    private var hybridRoleRegistered = false

    private var cameraProvider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var frameExecutor: ExecutorService? = null

    private val cardsPerVirtual = 10
    private val minFrameIntervalMs = 700L
    private val cameraPermissionRequestCode = 11

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_hybrid)

        roomId = intent.getStringExtra("roomId")?.trim().orEmpty()
        playerName = intent.getStringExtra("playerName") ?: "Player"
        playerId = intent.getStringExtra("playerId") ?: ""
        isHost = intent.getBooleanExtra("isHost", false)
        isVirtualPlayer = intent.getBooleanExtra("isVirtualPlayer", !isHost)

        if (roomId.isBlank()) {
            recognitionProgressText = findViewById(R.id.txtRecognitionProgress)
            recognitionProgressText.text = "Sala invalida para modo hibrido"
            finish()
            return
        }

        findViewById<ImageView>(R.id.backButton).setOnClickListener { finish() }

        modeSwitch = findViewById(R.id.activity_hybrid_switch)
        modeText = findViewById(R.id.txtHybridMode)
        previewView = findViewById(R.id.previewView)
        mesaContainer = findViewById(R.id.mesaContainer)
        handRecyclerView = findViewById(R.id.playerHandRecyclerView)
        recognitionOverlay = findViewById(R.id.recognitionOverlay)
        recognitionStateImage = findViewById(R.id.imgRecognitionState)
        recognitionProgressText = findViewById(R.id.txtRecognitionProgress)
        trumpSelectionControls = findViewById(R.id.trumpSelectionControls)
        btnTrumpTop = findViewById(R.id.btnTrumpTop)
        btnTrumpBottom = findViewById(R.id.btnTrumpBottom)

        clearTableCards()
        setupHand()
        setupSwitch()
        setupTrumpControls()

        if (isHost) {
            ensureCameraPermissionsAndStart()
        } else {
            previewView.visibility = View.GONE
            modeSwitch.isChecked = true
            modeSwitch.isEnabled = false
        }

        lifecycleScope.launch {
            hybridRoleRegistered = registerHybridRole()
            startRuntimeLoops()
        }
    }

    private fun setupTrumpControls() {
        btnTrumpTop.setOnClickListener { submitTrumpChoice("top") }
        btnTrumpBottom.setOnClickListener { submitTrumpChoice("bottom") }
    }

    private fun setupHand() {
        handAdapter = CardsAdapter(emptyList()) { card ->
            onVirtualCardTap(card)
        }
        handRecyclerView.layoutManager = GridLayoutManager(this, 5)
        handRecyclerView.adapter = handAdapter
        handAdapter.isEnabled = false
    }

    private fun setupSwitch() {
        modeSwitch.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                modeSwitch.text = "Mesa ativa"
                modeText.text = "Modo atual: mesa"
                previewView.visibility = View.GONE
                recognitionOverlay.visibility = View.GONE
                mesaContainer.visibility = View.VISIBLE
            } else {
                modeSwitch.text = "Camera ativa"
                modeText.text = "Modo atual: camera"
                mesaContainer.visibility = View.GONE
                previewView.visibility = if (isHost) View.VISIBLE else View.GONE
                recognitionOverlay.visibility = if (isRunning) View.VISIBLE else View.GONE
            }
        }
    }

    private suspend fun registerHybridRole(): Boolean {
        if (playerId.isBlank()) {
            syncPlayerIdFromStatus()
        }

        if (playerId.isBlank()) {
            recognitionProgressText.text = "Nao foi possivel identificar o jogador nesta sala"
            return false
        }

        try {
            RetrofitClient.api.hybridRegisterPlayer(
                HybridRegisterPlayerRequest(
                    gameId = roomId,
                    playerId = playerId,
                    role = if (isVirtualPlayer) "virtual" else "real",
                    isHost = isHost
                )
            )
            return true
        } catch (e: Exception) {
            Log.w("HybridActivity", "registerHybridRole failed: ${e.message}")
            return false
        }
    }

    private suspend fun resetDealForHost() {
        if (playerId.isBlank()) {
            return
        }
        try {
            val response = RetrofitClient.api.hybridDealReset(
                HybridDealResetRequest(
                    gameId = roomId,
                    playerId = playerId,
                    cardsPerVirtual = cardsPerVirtual
                )
            )
            hybridState = response.state
            updateUiFromHybridState(response.state)
            dealResetRequested = true
        } catch (e: Exception) {
            Log.w("HybridActivity", "resetDealForHost failed: ${e.message}")
            dealResetRequested = false
        }
    }

    private fun startRuntimeLoops() {
        if (isRunning) {
            return
        }
        isRunning = true
        recognitionOverlay.visibility = View.VISIBLE
        modeSwitch.isEnabled = false

        pollHybridJob?.cancel()
        pollGameJob?.cancel()

        pollHybridJob = lifecycleScope.launch {
            while (isRunning) {
                try {
                    if (!hybridRoleRegistered) {
                        hybridRoleRegistered = registerHybridRole()
                    }
                    val response = RetrofitClient.api.hybridState(roomId)
                    hybridState = response.state
                    updateUiFromHybridState(response.state)
                } catch (e: Exception) {
                    Log.w("HybridActivity", "hybridState poll failed: ${e.message}")
                }
                delay(700)
            }
        }

        pollGameJob = lifecycleScope.launch {
            while (isRunning) {
                try {
                    if (!hybridRoleRegistered) {
                        hybridRoleRegistered = registerHybridRole()
                    }
                    val state = RetrofitClient.api.getStatus(roomId)
                    gameState = state
                    updateUiFromGameState(state)
                } catch (e: Exception) {
                    Log.w("HybridActivity", "game status poll failed: ${e.message}")
                }
                delay(700)
            }
        }
    }

    private fun updateUiFromHybridState(state: HybridRuntimeState) {
        if (gameState?.phase != "playing") {
            handAdapter.isEnabled = false
            return
        }

        if (!state.dealDone) {
            showDealPhase(state)
            return
        }

        showPlayPhase(state)
    }

    private fun showDealPhase(state: HybridRuntimeState) {
        recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)

        if (isHost) {
            val nextTarget = state.virtualPlayers.firstOrNull { it.cardsCount < state.cardsPerVirtual }
            if (nextTarget != null) {
                recognitionProgressText.text =
                    "Distribui para ${nextTarget.playerName}: ${nextTarget.cardsCount + 1}/${state.cardsPerVirtual}"
                val hostViewCards = List(nextTarget.cardsCount) { idx -> Card(idx.toString(), "hidden", "hidden") }
                handAdapter.updateCards(hostViewCards)
            } else {
                recognitionProgressText.text = "Distribuicao concluida"
            }
            handAdapter.isEnabled = false
            return
        }

        if (isVirtualPlayer) {
            val me = state.virtualPlayers.firstOrNull { it.playerId == playerId }
            if (me != null) {
                val cards = me.cards.map { id -> cardIdToCard(id) }
                handAdapter.updateCards(cards)
                recognitionProgressText.text = "A receber cartas: ${me.cardsCount}/${state.cardsPerVirtual}"
            } else {
                handAdapter.updateCards(emptyList())
                recognitionProgressText.text = "Aguardando configuracao do host"
            }
        } else {
            handAdapter.updateCards(emptyList())
            recognitionProgressText.text = "Jogador real: aguarda distribuicao dos virtuais"
        }

        handAdapter.isEnabled = false
    }

    private fun showPlayPhase(state: HybridRuntimeState) {
        val pending = state.pendingVirtualPlay
        val currentPlayerId = gameState?.currentPlayerId

        if (isHost) {
            if (pending != null) {
                recognitionProgressText.text =
                    "Carta escolhida por ${pending.playerName}. Joga-a na mesa para confirmar"
                handAdapter.updateCards(buildRealCopyHand(state, currentPlayerId, pending))
            } else {
                val current = gameState?.currentPlayer ?: "-"
                recognitionProgressText.text = "Aguardar jogada captada. Vez: $current"
                handAdapter.updateCards(buildRealCopyHand(state, currentPlayerId, pending))
            }
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
            handAdapter.isEnabled = false
            return
        }

        if (isVirtualPlayer) {
            val me = state.virtualPlayers.firstOrNull { it.playerId == playerId }
            val cards = me?.cards?.map { id ->
                if (pending != null && pending.playerId == playerId) {
                    if (pending.cardId == id) cardIdToCard(id) else Card(id.toString(), "hidden", "hidden")
                } else {
                    cardIdToCard(id)
                }
            }.orEmpty()
            handAdapter.updateCards(cards)

            val isMyTurn = gameState?.currentPlayerId == playerId && pending == null
            handAdapter.isEnabled = isMyTurn

            recognitionProgressText.text = if (isMyTurn) {
                "Escolhe a carta para o host jogar"
            } else if (pending?.playerId == playerId) {
                "Host a confirmar a tua carta na mesa"
            } else {
                "A aguardar a tua vez"
            }
            recognitionStateImage.setImageResource(
                if (pending?.playerId == playerId) R.drawable.ic_hybrid_check else R.drawable.ic_hybrid_eye
            )
        } else {
            handAdapter.updateCards(buildRealCopyHand(state, currentPlayerId, pending))
            handAdapter.isEnabled = false
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
            recognitionProgressText.text = "Jogador real: acompanhar mao do jogador da vez"
        }

        modeSwitch.isEnabled = isHost
    }

    private fun updateUiFromGameState(state: GameStatusResponse) {
        updateTableFromGameState(state)

        val phase = state.phase

        if (phase == "trump_selection") {
            showTrumpSelectionPhase(state)
            return
        }

        trumpSelectionControls.visibility = View.GONE

        if (isHost && state.phase == "playing" && !dealResetRequested) {
            lifecycleScope.launch {
                resetDealForHost()
            }
        }

        if (phase != "playing") {
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
            handAdapter.isEnabled = false
            handAdapter.updateCards(emptyList())
            recognitionProgressText.text = when (phase) {
                "deck_cutting" -> "Corte ignorado no hibrido. A preparar selecao de trunfo"
                else -> "Aguardar inicio da partida"
            }
            return
        }

        if (!isHost) {
            return
        }

        maybeHostAutoCapture(state)
    }

    private fun showTrumpSelectionPhase(state: GameStatusResponse) {
        trumpSelectionControls.visibility = View.VISIBLE
        recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
        handAdapter.isEnabled = false
        handAdapter.updateCards(emptyList())

        val selectorId = state.trumpSelectorPlayerId ?: state.westPlayerId
        val selectorName = state.trumpSelectorPlayer ?: state.westPlayer ?: "jogador do trunfo"
        val isSelector = !selectorId.isNullOrBlank() && selectorId == playerId

        btnTrumpTop.isEnabled = isSelector
        btnTrumpBottom.isEnabled = isSelector

        // Host should keep camera mode in trump selection to allow physical capture.
        if (isHost) {
            modeSwitch.isEnabled = true
            modeSwitch.isChecked = false
        }

        recognitionProgressText.text = if (isSelector) {
            "E a tua vez de escolher o trunfo (topo/fundo)"
        } else {
            "Aguardar $selectorName escolher o trunfo"
        }
    }

    private fun submitTrumpChoice(choice: String) {
        if (playerId.isBlank()) {
            recognitionProgressText.text = "Nao foi possivel identificar o teu jogador"
            return
        }

        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api.selectTrump(
                    SelectTrumpRequest(
                        playerId = playerId,
                        choice = choice,
                        gameId = roomId
                    )
                )

                if (!response.success) {
                    recognitionProgressText.text = response.message ?: "Falha ao selecionar trunfo"
                }
            } catch (e: Exception) {
                recognitionProgressText.text = "Erro ao selecionar trunfo"
                Log.w("HybridActivity", "submitTrumpChoice failed: ${e.message}")
            }
        }
    }

    private fun maybeHostAutoCapture(state: GameStatusResponse) {
        if (!isRunning || inFlightRecognition) {
            return
        }
        val currentPlayerId = state.currentPlayerId ?: return

        val now = SystemClock.elapsedRealtime()
        if (now - lastFrameSentAt < minFrameIntervalMs) {
            return
        }

        // Decision is executed by analyzer thread; this method only updates intent.
    }

    private fun onVirtualCardTap(card: Card) {
        if (!isVirtualPlayer) {
            return
        }

        val state = hybridState ?: return
        val isMyTurn = gameState?.currentPlayerId == playerId && state.pendingVirtualPlay == null
        if (!isMyTurn) {
            return
        }

        val cardId = card.id.toIntOrNull() ?: return

        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api.hybridSelectCard(
                    HybridSelectCardRequest(
                        gameId = roomId,
                        playerId = playerId,
                        card = cardId
                    )
                )
                hybridState = response.state
                updateUiFromHybridState(response.state)
            } catch (_: Exception) {
                // Keep UI stable; next poll refreshes state.
            }
        }
    }

    private fun buildRealCopyHand(
        state: HybridRuntimeState,
        currentPlayerId: String?,
        pending: com.example.Jogo_da_Sueca.models.HybridPendingPlay?
    ): List<Card> {
        if (currentPlayerId.isNullOrBlank()) {
            return emptyList()
        }

        val currentVirtual = state.virtualPlayers.firstOrNull { it.playerId == currentPlayerId }
        if (currentVirtual != null) {
            return currentVirtual.cards.map { cardId ->
                if (pending != null && pending.playerId == currentPlayerId && pending.cardId == cardId) {
                    cardIdToCard(cardId)
                } else {
                    Card(cardId.toString(), "hidden", "hidden")
                }
            }
        }

        val realCurrent = gameState?.players?.firstOrNull { it.id == currentPlayerId }
        val backCount = realCurrent?.cardsLeft?.coerceAtLeast(0) ?: 0
        return List(backCount) { idx -> Card(idx.toString(), "hidden", "hidden") }
    }

    private suspend fun syncPlayerIdFromStatus() {
        try {
            val state = RetrofitClient.api.getStatus(roomId)
            val me = state.players.firstOrNull { it.name == playerName }
            playerId = me?.id ?: playerId
        } catch (_: Exception) {
            // Will retry from next polling cycle.
        }
    }

    private fun ensureCameraPermissionsAndStart() {
        if (allPermissionsGranted()) {
            startCameraPipeline()
            return
        }

        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.CAMERA),
            cameraPermissionRequestCode
        )
    }

    private fun startCameraPipeline() {
        val providerFuture = ProcessCameraProvider.getInstance(this)
        frameExecutor = Executors.newSingleThreadExecutor()

        providerFuture.addListener({
            cameraProvider = providerFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }

            val analyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()

            analyzer.setAnalyzer(frameExecutor!!) { imageProxy ->
                analyzeFrameForHybrid(imageProxy)
            }

            try {
                cameraProvider?.unbindAll()
                camera = cameraProvider?.bindToLifecycle(
                    this,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview,
                    analyzer
                )
            } catch (e: Exception) {
                Log.e("HybridActivity", "Failed to bind camera pipeline", e)
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun analyzeFrameForHybrid(imageProxy: ImageProxy) {
        try {
            if (!isHost || !isRunning || inFlightRecognition) {
                return
            }

            val now = SystemClock.elapsedRealtime()
            if (now - lastFrameSentAt < minFrameIntervalMs) {
                return
            }

            val frameBase64 = imageProxyToBase64(imageProxy) ?: return
            lastFrameSentAt = now
            inFlightRecognition = true

            val localHybrid = hybridState
            val localGame = gameState

            lifecycleScope.launch {
                try {
                    if (localGame?.phase == "trump_selection") {
                        val response = RetrofitClient.api.hybridConfirmTrumpCapture(
                            HybridConfirmTrumpCaptureRequest(
                                gameId = roomId,
                                hostPlayerId = playerId,
                                frameBase64 = frameBase64
                            )
                        )
                        if (response.success) {
                            response.gameState?.let {
                                gameState = it
                                updateUiFromGameState(it)
                            }
                            response.state?.let {
                                hybridState = it
                            }
                            flashCheck("Trunfo captado")
                        }
                    } else if (localHybrid != null && !localHybrid.dealDone && localGame?.phase == "playing") {
                        val response = RetrofitClient.api.hybridDealRecognize(
                            HybridDealRecognizeRequest(
                                gameId = roomId,
                                playerId = playerId,
                                frameBase64 = frameBase64,
                                targetPlayerId = null
                            )
                        )
                        hybridState = response.state
                        updateUiFromHybridState(response.state)
                        if (response.confirmed) {
                            flashCheck("Carta distribuida")
                        }
                    } else if (localGame?.phase == "playing") {
                        val pending = localHybrid?.pendingVirtualPlay
                        val currentPlayerId = localGame.currentPlayerId

                        val capturePlayerId = when {
                            pending != null && pending.playerId == currentPlayerId -> pending.playerId
                            !currentPlayerId.isNullOrBlank() -> currentPlayerId
                            else -> null
                        }

                        if (!capturePlayerId.isNullOrBlank()) {
                            val response = RetrofitClient.api.hybridConfirmCapture(
                                HybridConfirmCaptureRequest(
                                    gameId = roomId,
                                    playerId = capturePlayerId,
                                    hostPlayerId = playerId,
                                    frameBase64 = frameBase64
                                )
                            )
                            if (response.success) {
                                response.state?.let {
                                    hybridState = it
                                    updateUiFromHybridState(it)
                                }
                                response.gameState?.let {
                                    gameState = it
                                }
                                flashCheck("Carta captada")
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.w("HybridActivity", "Frame processing failed: ${e.message}")
                } finally {
                    inFlightRecognition = false
                }
            }
        } finally {
            imageProxy.close()
        }
    }

    private fun flashCheck(text: String) {
        flashJob?.cancel()
        flashJob = lifecycleScope.launch {
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_check)
            recognitionProgressText.text = text
            delay(1200)
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
        }
    }

    private fun imageProxyToBase64(imageProxy: ImageProxy): String? {
        if (imageProxy.format != ImageFormat.YUV_420_888) {
            return null
        }

        val nv21 = yuv420ToNv21(imageProxy)
        val yuvImage = YuvImage(nv21, ImageFormat.NV21, imageProxy.width, imageProxy.height, null)
        val output = ByteArrayOutputStream()
        val ok = yuvImage.compressToJpeg(
            Rect(0, 0, imageProxy.width, imageProxy.height),
            70,
            output
        )

        if (!ok) {
            return null
        }

        return Base64.encodeToString(output.toByteArray(), Base64.NO_WRAP)
    }

    private fun yuv420ToNv21(image: ImageProxy): ByteArray {
        val yBuffer = image.planes[0].buffer
        val uBuffer = image.planes[1].buffer
        val vBuffer = image.planes[2].buffer

        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()

        val nv21 = ByteArray(ySize + uSize + vSize)
        yBuffer.get(nv21, 0, ySize)
        vBuffer.get(nv21, ySize, vSize)
        uBuffer.get(nv21, ySize + vSize, uSize)
        return nv21
    }

    private fun cardIdToCard(cardId: Int): Card {
        val suit = CardMapper.getCardSuitName(cardId)
        val rank = CardMapper.getCardRankName(cardId)
        return Card(cardId.toString(), suit, rank)
    }

    private fun setCardResource(viewId: Int, cardName: String) {
        val cardView = findViewById<ImageView>(viewId)
        val resourceId = resources.getIdentifier(cardName, "drawable", packageName)
        if (resourceId != 0) {
            cardView.setImageResource(resourceId)
        } else {
            cardView.setImageResource(R.drawable.card_back)
        }
    }

    private fun setCardBack(viewId: Int) {
        findViewById<ImageView>(viewId).setImageResource(R.drawable.card_back)
    }

    private fun clearTableCards() {
        setCardBack(R.id.card_north)
        setCardBack(R.id.card_west)
        setCardBack(R.id.card_east)
        setCardBack(R.id.card_south)
        setCardBack(R.id.trump_card)
    }

    private fun updateTableFromGameState(state: GameStatusResponse) {
        clearTableCards()

        val trumpId = state.trump?.toIntOrNull()
        if (trumpId != null) {
            setCardResource(R.id.trump_card, CardMapper.getDrawableName(trumpId))
        }

        for (play in state.roundPlays) {
            val cardId = play.card.toIntOrNull() ?: continue
            val slotViewId = when (normalizePosition(play.position)) {
                "NORTH" -> R.id.card_north
                "EAST" -> R.id.card_east
                "SOUTH" -> R.id.card_south
                "WEST" -> R.id.card_west
                else -> null
            } ?: continue

            setCardResource(slotViewId, CardMapper.getDrawableName(cardId))
        }
    }

    private fun normalizePosition(pos: String?): String {
        if (pos.isNullOrBlank()) return ""
        val p = pos.uppercase()
        return when {
            p.contains("NORTH") -> "NORTH"
            p.contains("SOUTH") -> "SOUTH"
            p.contains("EAST") -> "EAST"
            p.contains("WEST") -> "WEST"
            else -> p
        }
    }

    private fun allPermissionsGranted(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
    }

    override fun onDestroy() {
        isRunning = false
        pollHybridJob?.cancel()
        pollGameJob?.cancel()
        flashJob?.cancel()
        frameExecutor?.shutdown()
        cameraProvider?.unbindAll()
        super.onDestroy()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == cameraPermissionRequestCode && grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) {
            startCameraPipeline()
        }
    }
}
