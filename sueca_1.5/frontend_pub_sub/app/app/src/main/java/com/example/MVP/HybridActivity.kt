package com.example.MVP

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
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
import android.widget.LinearLayout
import android.widget.FrameLayout
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
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
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.MVP.models.Card
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.HybridConfirmCaptureRequest
import com.example.MVP.models.HybridConfirmTrumpCaptureRequest
import com.example.MVP.models.HybridDealRecognizeRequest
import com.example.MVP.models.HybridDealResetRequest
import com.example.MVP.models.HybridRegisterPlayerRequest
import com.example.MVP.models.HybridRuntimeState
import com.example.MVP.models.HybridSelectCardRequest
import com.example.MVP.models.SelectTrumpRequest
import com.example.MVP.models.Choice
import com.example.MVP.network.GameMqttSubscriber
import com.example.MVP.network.HybridWebSocketClient
import com.example.MVP.network.GatewayClient
import com.example.MVP.utils.CardMapper
import com.google.gson.Gson
import com.google.gson.JsonObject
import java.io.ByteArrayOutputStream
import java.text.Normalizer
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Atividade principal do Modo Híbrido. 
 * Gere a câmara (se for Host), a sincronização via MQTT e a interação entre o mundo físico e virtual.
 */
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
    private lateinit var btnUndoMove: Button
    private lateinit var hostCameraPreview: ImageView

    private lateinit var layoutFinishedBanner: LinearLayout
    private lateinit var txtEndBanner: TextView
    private lateinit var layoutActions: LinearLayout
    private lateinit var handLabel: TextView

    private lateinit var handAdapter: CardsAdapter

    private lateinit var roomId: String
    private lateinit var playerName: String
    private lateinit var playerId: String
    private var isHost: Boolean = false
    private var isVirtualPlayer: Boolean = false

    private var gameState: GameStatusResponse? = null
    private var hybridState: HybridRuntimeState? = null

    private var isRunning = false
    private var hybridWsClient: HybridWebSocketClient? = null
    private var hybridMqttSubscriber: GameMqttSubscriber? = null
    private var flashJob: Job? = null
    private var trickResolutionSyncJob: Job? = null
    private val gson = Gson()

    private var inFlightRecognition = false
    private var lastFrameSentAt = 0L
    private var lastStreamFrameSentAt = 0L
    private var dealResetRequested = false
    private var hybridRoleRegistered = false
    private var cvRecognitionPaused = false
    private var trumpPauseShown = false
    private var dealPauseShown = false
    private var lastDealDone = false
    private var cvPauseDialog: AlertDialog? = null

    private var cameraProvider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var frameExecutor: ExecutorService? = null

    private val cardsPerVirtual = 10
    private val minFrameIntervalMs = 700L
    private val streamIntervalMs = 200L
    private val cameraPermissionRequestCode = 11

    private enum class CvPauseReason {
        AFTER_TRUMP,
        AFTER_DEAL,
    }

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
        btnUndoMove = findViewById(R.id.btnUndoMove)
        hostCameraPreview = findViewById(R.id.hostCameraPreview)
        layoutFinishedBanner = findViewById<LinearLayout>(R.id.layoutFinishedBanner)
        txtEndBanner = findViewById(R.id.txtEndBanner)
        layoutActions = findViewById<LinearLayout>(R.id.layoutActions)
        handLabel = findViewById(R.id.handLabel)

        clearTableCards()
        setupHand()
        setupSwitch()
        setupTrumpControls()
        setupUndoControl()

        if (isHost) {
            ensureCameraPermissionsAndStart()
        } else {
            previewView.visibility = View.GONE
            hostCameraPreview.visibility = View.GONE
            // Permitimos que o jogador virtual alterne entre mesa e câmara do host
            modeSwitch.isEnabled = true 
            modeSwitch.isChecked = true // Começa na mesa (virtual) como solicitado
            // Garantir que a visibilidade é aplicada quando alteramos o estado programaticamente
            applyModeVisibility(modeSwitch.isChecked)
        }

        lifecycleScope.launch {
            connectHybridWebSocket()
            startHybridMqtt()
            hybridRoleRegistered = registerHybridRole()
        }
    }

    override fun onResume() {
        super.onResume()
        if (isRunning) {
            startHybridMqtt()
            requestSyncState()
        }
    }

    override fun onPause() {
        super.onPause()
        hybridMqttSubscriber?.disconnect()
    }

    private fun setupTrumpControls() {
        btnTrumpTop.setOnClickListener { submitTrumpChoice("top") }
        btnTrumpBottom.setOnClickListener { submitTrumpChoice("bottom") }
    }

    private fun setupUndoControl() {
        btnUndoMove.setOnClickListener { requestUndoMove() }
        btnUndoMove.visibility = View.GONE
    }

    private fun setupHand() {
        handAdapter = CardsAdapter(emptyList()) { card ->
            onVirtualCardTap(card)
        }
        handRecyclerView.layoutManager = object : LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false) {
            override fun canScrollHorizontally(): Boolean = false
        }
        handRecyclerView.setHasFixedSize(true)
        handRecyclerView.itemAnimator = null
        handRecyclerView.overScrollMode = View.OVER_SCROLL_NEVER
        handRecyclerView.setPadding(4, 0, 4, 0)
        handRecyclerView.clipToPadding = false
        handRecyclerView.clipChildren = false
        (handRecyclerView.parent as? android.view.ViewGroup)?.clipChildren = false
        (handRecyclerView.parent as? android.view.ViewGroup)?.clipToPadding = false
        handRecyclerView.adapter = handAdapter
        handRecyclerView.post {
            handAdapter.setAvailableWidth(handRecyclerView.width - handRecyclerView.paddingStart - handRecyclerView.paddingEnd)
        }
        handRecyclerView.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ ->
            handAdapter.setAvailableWidth(handRecyclerView.width - handRecyclerView.paddingStart - handRecyclerView.paddingEnd)
        }
        handAdapter.isEnabled = false
    }

    private fun setupSwitch() {
        modeSwitch.setOnCheckedChangeListener { _, isChecked ->
            applyModeVisibility(isChecked)
        }

        // Ensure a clean initial state so camera and table never overlap.
        applyModeVisibility(modeSwitch.isChecked)
    }

    private fun applyModeVisibility(isTableMode: Boolean) {
        if (isTableMode) {
            modeSwitch.text = "Mesa ativa"
            modeText.text = "Modo atual: mesa"
            previewView.visibility = View.GONE
            hostCameraPreview.visibility = View.GONE
            recognitionOverlay.visibility = View.GONE
            mesaContainer.visibility = View.VISIBLE
            handLabel.visibility = View.VISIBLE
            handRecyclerView.visibility = View.VISIBLE
            mesaContainer.bringToFront()
            mesaContainer.invalidate()
            return
        }

        modeSwitch.text = "Camera ativa"
        modeText.text = "Modo atual: camera"
        mesaContainer.visibility = View.GONE
        handLabel.visibility = View.GONE
        handRecyclerView.visibility = View.GONE

        if (isHost) {
            previewView.visibility = View.VISIBLE
            hostCameraPreview.visibility = View.GONE
            previewView.bringToFront()
            previewView.invalidate()
            recognitionOverlay.visibility = if (isRunning) View.VISIBLE else View.GONE
            recognitionOverlay.bringToFront()
        } else {
            previewView.visibility = View.GONE
            hostCameraPreview.visibility = View.VISIBLE
            hostCameraPreview.bringToFront()
            hostCameraPreview.invalidate()
            recognitionOverlay.visibility = View.GONE
        }
            // Always show the player's hand under the camera so virtual players
            // can see and interact with their cards while viewing the host feed.
            handLabel.visibility = View.VISIBLE
            handRecyclerView.visibility = View.VISIBLE
    }

    /**
     * Regista o papel do jogador no servidor (Real ou Virtual).
     * Essencial para que o servidor saiba quem precisa de "ver" as cartas no telemóvel.
     */
    private suspend fun registerHybridRole(): Boolean {
        if (playerId.isBlank()) {
            syncPlayerIdFromStatus()
        }

        if (playerId.isBlank()) {
            recognitionProgressText.text = "Nao foi possivel identificar o jogador nesta sala"
            return false
        }

        hybridWsClient?.sendAction(
            "register_player",
            HybridRegisterPlayerRequest(
                gameId = roomId,
                playerId = playerId,
                role = if (isVirtualPlayer) "virtual" else "real",
                isHost = isHost
            )
        )

        // Ask server for a fresh state snapshot right after registering.
        hybridWsClient?.sendAction("sync_state", mapOf("game_id" to roomId))
        return true
    }

    /**
     * Reinicia o estado de distribuição de cartas para o Host.
     * Prepara o sistema de reconhecimento de imagem para começar a "dar" cartas aos jogadores virtuais.
     */
    private suspend fun resetDealForHost() {
        if (playerId.isBlank()) {
            return
        }
        hybridWsClient?.sendAction(
            "deal_reset",
            HybridDealResetRequest(
                gameId = roomId,
                playerId = playerId,
                cardsPerVirtual = cardsPerVirtual
            )
        )
        dealResetRequested = true
        dealPauseShown = false
    }

    /**
     * Bots publish hybrid state over MQTT (HTTP select_card). WS alone can miss updates
     * when the gateway bridge drops or the app was backgrounded.
     */
    private fun startHybridMqtt() {
        if (roomId.isBlank()) return

        hybridMqttSubscriber?.disconnect()
        val subscriber = GameMqttSubscriber(
            brokerHost = "mqtt.suecadaojogo.com",
            brokerPort = 443,
            protocol = "wss"
        )
        subscriber.connectAndSubscribe(
            gameId = roomId,
            onEnvelope = { envelope ->
                runOnUiThread {
                    envelope.hybridState?.let { hybrid ->
                        hybridState = hybrid
                        updateUiFromHybridState(hybrid)
                    }
                    envelope.state?.let { game ->
                        gameState = game
                        updateUiFromGameState(game)
                    }
                }
            },
            onConnectionError = { reason ->
                Log.w("HybridActivity", "Hybrid MQTT disconnected: $reason")
            }
        )
        hybridMqttSubscriber = subscriber
    }

    private fun connectHybridWebSocket() {
        if (isRunning) return

        hybridWsClient = HybridWebSocketClient(
            roomId = roomId,
            onStateUpdate = { hybrid, game ->
                runOnUiThread {
                    if (game != null) {
                        gameState = game
                        updateUiFromGameState(game)
                    }
                    if (hybrid != null) {
                        hybridState = hybrid
                        updateUiFromHybridState(hybrid)
                    }
                }
            },
            onFrameReceived = { bytes ->
                if (!isHost && !modeSwitch.isChecked) {
                    val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    if (bitmap != null) {
                        runOnUiThread {
                            hostCameraPreview.setImageBitmap(bitmap)
                        }
                    }
                }
            },
            onActionResponse = { action, response ->
                handleWebSocketActionResponse(action, response)
            },
            onConnectionLost = { reason ->
                Log.w("HybridActivity", "Hybrid WS connection lost: $reason")
            },
            onConnected = { requestSyncState() }
        )

        hybridWsClient?.connect()
        isRunning = true
    }

    private fun requestSyncState() {
        if (roomId.isBlank()) return
        hybridWsClient?.sendAction("sync_state", mapOf("game_id" to roomId))
    }

    /** Fallback when round_end MQTT/WS update was missed (e.g. reconnect during trick). */
    private fun scheduleTrickResolutionSync() {
        trickResolutionSyncJob?.cancel()
        trickResolutionSyncJob = lifecycleScope.launch {
            delay(2000)
            if (!isActive) return@launch
            val gs = gameState ?: return@launch
            if (gs.roundPlays.size >= 4 && gs.currentPlayerId.isNullOrBlank()) {
                requestSyncState()
            }
        }
    }

    private fun handleWebSocketActionResponse(action: String, response: JsonObject) {
        runOnUiThread {
            response.getAsJsonObject("state")?.let {
                val stateObj = gson.fromJson(it, HybridRuntimeState::class.java)
                hybridState = stateObj
                updateUiFromHybridState(stateObj)
            }

            response.getAsJsonObject("game_state")?.let {
                val gameObj = gson.fromJson(it, GameStatusResponse::class.java)
                gameState = gameObj
                updateUiFromGameState(gameObj)
            }

            when (action) {
                "trump_confirm_capture" -> {
                    if (response.get("success")?.asBoolean == true) {
                        flashCheck("Trunfo captado")
                        if (!trumpPauseShown) {
                            trumpPauseShown = true
                            showCvPauseDialog(CvPauseReason.AFTER_TRUMP)
                        }
                    }
                    inFlightRecognition = false
                }
                "deal_recognize" -> {
                    if (response.get("confirmed")?.asBoolean == true) {
                        flashCheck("Carta distribuida")
                        if (response.getAsJsonObject("state")?.get("deal_done")?.asBoolean == true && !dealPauseShown) {
                            dealPauseShown = true
                            showCvPauseDialog(CvPauseReason.AFTER_DEAL)
                        }
                    }
                    inFlightRecognition = false
                }
                "play_confirm_capture" -> {
                    if (response.get("is_renuncia_warning")?.asBoolean == true) {
                        val capturedCard = response.get("captured_card_id")?.asInt
                        val capturedDisplay = response.get("captured_display")?.asString
                        val currentPlayerId = gameState?.currentPlayerId
                        if (!currentPlayerId.isNullOrBlank()) {
                            showRenunciaDialog(currentPlayerId, capturedCard, capturedDisplay)
                        }
                    } else if (response.get("success")?.asBoolean == true) {
                        flashCheck("Carta captada")
                        val trickDone = response.get("trick_completed")?.asBoolean == true
                        val playsStillOnTable = gameState?.roundPlays?.size ?: 0
                        if (!trickDone && playsStillOnTable >= 4) {
                            scheduleTrickResolutionSync()
                        }
                    }
                    inFlightRecognition = false
                }
                "select_trump" -> {
                    if (response.get("success")?.asBoolean == false) {
                        recognitionProgressText.text = response.get("message")?.asString ?: "Falha ao selecionar trunfo"
                    }
                }
                "play_undo", "virtual_select_card", "register_player", "deal_reset", "sync_state", "deal_finalize", "play_force_renuncia" -> {
                    // State is handled above when present.
                }
            }
        }
    }

    /**
     * Decide se a UI deve mostrar a fase de Distribuição ou a fase de Jogo.
     */
    private fun updateUiFromHybridState(state: HybridRuntimeState) {
        if (gameState?.phase != "playing") {
            handAdapter.isEnabled = false
            return
        }

        val isReallyDone = isDistributionReallyDone(state)
        
        if (isHost && isReallyDone && !lastDealDone && !dealPauseShown) {
            dealPauseShown = true
            showCvPauseDialog(CvPauseReason.AFTER_DEAL)
        }
        lastDealDone = isReallyDone

        if (!isReallyDone) {
            showDealPhase(state)
            return
        }

        showPlayPhase(state)
    }

    private fun showCvPauseDialog(reason: CvPauseReason) {
        if (!isHost) {
            return
        }

        runOnUiThread {
            if (isFinishing || isDestroyed) {
                return@runOnUiThread
            }

            cvPauseDialog?.dismiss()
            cvRecognitionPaused = false

            val titleRes = when (reason) {
                CvPauseReason.AFTER_TRUMP -> R.string.hybrid_cv_pause_trump_title
                CvPauseReason.AFTER_DEAL -> R.string.hybrid_cv_pause_deal_title
            }
            val messageRes = when (reason) {
                CvPauseReason.AFTER_TRUMP -> R.string.hybrid_cv_pause_trump_message
                CvPauseReason.AFTER_DEAL -> R.string.hybrid_cv_pause_deal_message
            }

            cvPauseDialog = AlertDialog.Builder(this, R.style.CustomDialogTheme)
                .setTitle(titleRes)
                .setMessage(messageRes)
                .setCancelable(false)
                .setPositiveButton(R.string.hybrid_cv_pause_continue) { dialog, _ ->
                    if (reason == CvPauseReason.AFTER_DEAL) {
                        lifecycleScope.launch {
                            try {
                                hybridWsClient?.sendAction(
                                    "deal_finalize",
                                    com.example.MVP.models.HybridDealFinalizeRequest(
                                        gameId = roomId,
                                        playerId = playerId
                                    )
                                )
                            } catch (_: Exception) {
                                // Keep UI stable; websocket updates will refresh state.
                            } finally {
                                dialog.dismiss()
                                cvPauseDialog = null
                            }
                        }
                    } else {
                        dialog.dismiss()
                        cvPauseDialog = null
                    }
                }
                .create()

            cvPauseDialog?.show()
        }
    }

    private fun showRenunciaDialog(playerId: String, cardId: Int?, cardDisplay: String?) {
        runOnUiThread {
            if (isFinishing || isDestroyed) {
                return@runOnUiThread
            }

            cvPauseDialog?.dismiss()
            cvRecognitionPaused = true

            cvPauseDialog = AlertDialog.Builder(this, R.style.CustomDialogTheme)
                .setTitle("⚠️ Possível Renúncia")
                .setMessage("A câmara detetou um [$cardDisplay], o que constitui uma renúncia. A câmara leu a carta corretamente?")
                .setCancelable(false)
                .setPositiveButton("Sim (Aplicar Renúncia)") { dialog, _ ->
                    dialog.dismiss()
                    cvPauseDialog = null
                    if (cardId != null) {
                        applyForceRenuncia(playerId, cardId)
                    } else {
                        cvRecognitionPaused = false
                    }
                }
                .setNegativeButton("Não (Tentar Novamente)") { dialog, _ ->
                    cvRecognitionPaused = false
                    dialog.dismiss()
                    cvPauseDialog = null
                }
                .create()

            cvPauseDialog?.show()
        }
    }

    private fun applyForceRenuncia(playerId: String, cardId: Int) {
        hybridWsClient?.sendAction(
            "play_force_renuncia",
            com.example.MVP.models.HybridForceRenunciaRequest(
                gameId = roomId,
                playerId = playerId,
                cardId = cardId
            )
        )
        cvRecognitionPaused = false
    }

    /**
     * Gere a UI durante a distribuição de cartas. 
     * Se for Host, indica qual o próximo jogador virtual que deve receber uma carta da câmara.
     * Se for Virtual, mostra as cartas que o Host já leu para nós.
     */
    private fun showDealPhase(state: HybridRuntimeState) {
        if (isHost) recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
        btnUndoMove.visibility = View.GONE

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
            val me = resolveVirtualPlayer(state)
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

    /**
     * Gere a UI durante as jogadas.
     * O Host vê o que a câmara capta. Os Virtuais veem as suas cartas para poderem escolher uma.
     */
    private fun showPlayPhase(state: HybridRuntimeState) {
        val pending = state.pendingVirtualPlay
        val currentPlayerId = gameState?.currentPlayerId
        btnUndoMove.visibility = View.VISIBLE
        btnUndoMove.isEnabled = pending != null || (gameState?.roundPlays?.isNotEmpty() == true)

        if (isHost) {
            if (pending != null) {
                recognitionProgressText.text =
                    "Carta escolhida por ${pending.playerName}. Joga-a na mesa para confirmar"
                handAdapter.updateCards(buildRealCopyHand(state, currentPlayerId, pending))
            } else {
                recognitionProgressText.text = hostPlayPhaseStatusText()
                handAdapter.updateCards(buildRealCopyHand(state, currentPlayerId, pending))
            }
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
            handAdapter.isEnabled = false
            return
        }

        if (isVirtualPlayer) {
            val me = resolveVirtualPlayer(state)
            val cards = me?.cards?.map { id ->
                if (pending != null && pending.playerId == (playerId.ifBlank { me?.playerId.orEmpty() })) {
                    if (pending.cardId == id) cardIdToCard(id) else Card(id.toString(), "hidden", "hidden")
                } else {
                    cardIdToCard(id)
                }
            }.orEmpty()
            handAdapter.updateCards(cards)

            val resolvedCurrentPlayerId = resolveCurrentPlayerId(gameState)
            val isMyTurn = resolvedCurrentPlayerId == (playerId.ifBlank { me?.playerId.orEmpty() }) && pending == null
            handAdapter.isEnabled = isMyTurn

            recognitionProgressText.text = if (isMyTurn) {
                "Escolhe a carta para o host jogar"
            } else if (pending?.playerId == playerId) {
                "Host a confirmar a tua carta na mesa"
            } else {
                "A aguardar a tua vez"
            }
            if (isHost) {
                recognitionStateImage.setImageResource(
                    if (pending?.playerId == playerId) R.drawable.ic_hybrid_check else R.drawable.ic_hybrid_eye
                )
            }
        } else {
            handAdapter.updateCards(buildRealCopyHand(state, currentPlayerId, pending))
            handAdapter.isEnabled = false
            recognitionProgressText.text = "Jogador real: acompanhar mao do jogador da vez"
        }

        modeSwitch.isEnabled = true
    }

    private fun requestUndoMove() {
        if (roomId.isBlank()) {
            return
        }

        hybridWsClient?.sendAction(
            "play_undo",
            com.example.MVP.models.UndoMoveRequest(
                gameId = roomId
            )
        )
    }

    private fun updateUiFromGameState(state: GameStatusResponse) {
        updateTableFromGameState(state)

        val phase = state.phase

        if (phase == "finished") {
            showFinishedBanner(state)
            return
        } else {
            layoutFinishedBanner.visibility = View.GONE
            findViewById<FrameLayout>(R.id.hybridContentContainer).visibility = View.VISIBLE
        }

        if (phase == "trump_selection") {
            showTrumpSelectionPhase(state)
            return
        }

        trumpSelectionControls.visibility = View.GONE
        if (phase != "playing") {
            btnUndoMove.visibility = View.GONE
        }

        if (isHost && state.phase == "playing" && !dealResetRequested) {
            lifecycleScope.launch {
                resetDealForHost()
            }
        }

        if (phase != "playing") {
            if (isHost) recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
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

        // MQTT round_end / card_played updates only carry game_state; refresh play UI labels.
        hybridState?.let { updateUiFromHybridState(it) }
    }

    /** Host camera overlay: who should play next, or trick resolution in progress. */
    private fun hostPlayPhaseStatusText(): String {
        val gs = gameState
        if (gs == null) {
            return "Aguardar jogada captada"
        }
        val playsOnTable = gs.roundPlays.size
        if (playsOnTable >= 4 && gs.currentPlayerId.isNullOrBlank()) {
            scheduleTrickResolutionSync()
            return "A resolver a volta..."
        }
        val name = gs.currentPlayer
            ?: gs.players.firstOrNull { it.id == gs.currentPlayerId }?.name
        if (name.isNullOrBlank()) {
            return "Aguardar jogada captada"
        }
        return "Aguardar jogada captada. Vez: $name"
    }

    private fun showTrumpSelectionPhase(state: GameStatusResponse) {
        trumpSelectionControls.visibility = View.VISIBLE
        btnUndoMove.visibility = View.GONE
        if (isHost) recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
        handAdapter.isEnabled = false
        handAdapter.updateCards(emptyList())

        val selectorId = state.trumpSelectorPlayerId ?: state.westPlayerId ?: resolveCurrentPlayerId(state)
        val selectorName = state.trumpSelectorPlayer ?: state.westPlayer ?: "jogador do trunfo"
        val isSelector = matchesCurrentPlayer(selectorId, selectorName, state)

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

    private fun showFinishedBanner(state: GameStatusResponse) {
        trumpSelectionControls.visibility = View.GONE
        btnUndoMove.visibility = View.GONE
        handAdapter.isEnabled = false
        handAdapter.updateCards(emptyList())

        // Dim camera/table container (don't fully hide, constraints can collapse if set GONE)
        val hybridContainer = findViewById<FrameLayout>(R.id.hybridContentContainer)
        hybridContainer.alpha = 0.25f
        hybridContainer.isClickable = false
        
        // Hide hand and label to avoid visual conflict
        findViewById<androidx.recyclerview.widget.RecyclerView>(R.id.playerHandRecyclerView).visibility = View.GONE
        findViewById<TextView>(R.id.handLabel).visibility = View.GONE
        
        // Show banner
        layoutFinishedBanner.visibility = View.VISIBLE
        layoutFinishedBanner.bringToFront()
        layoutFinishedBanner.invalidate()
        layoutFinishedBanner.requestLayout()

        val team1 = state.teamScores?.team1 ?: 0
        val team2 = state.teamScores?.team2 ?: 0
        val winnerText = when {
            team1 > team2 -> "TEAM 1 (N/S) VENCE"
            team2 > team1 -> "TEAM 2 (E/W) VENCE"
            else -> "EMPATE"
        }

        val match = state.matchPoints
        val matchLine = if (match != null) {
            "\nJogos ganhos: ${match.team1} - ${match.team2}"
        } else {
            ""
        }

        // Team members (if available)
        val team1Members = state.teams?.team1 ?: emptyList()
        val team2Members = state.teams?.team2 ?: emptyList()

        // Teams may contain player names or ids. Normalize to names using `state.players` when possible.
        val idToName = state.players.associateBy({ it.id }, { it.name })
        val team1MembersNames = team1Members.map { idToName[it] ?: it }
        val team2MembersNames = team2Members.map { idToName[it] ?: it }

        val team1Names = if (team1MembersNames.isNotEmpty()) team1MembersNames.joinToString(", ") else "-"
        val team2Names = if (team2MembersNames.isNotEmpty()) team2MembersNames.joinToString(", ") else "-"

        val details = "\n\nEquipe N/S: $team1Names\nEquipe E/W: $team2Names"

        txtEndBanner.text = "$winnerText\nPontuação final: $team1 - $team2$matchLine$details"

        layoutActions.removeAllViews()

        val rematch = Button(this)
        rematch.text = "Desforra"
        rematch.setOnClickListener { requestRematch() }

        val score = Button(this)
        score.text = "Pontos do Jogo"
        score.setOnClickListener { showMatchScoreDialog() }

        val params = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ).apply { marginEnd = 16 }
        rematch.layoutParams = params

        layoutActions.addView(rematch)
        layoutActions.addView(score)
    }

    private fun requestRematch() {
        if (roomId.isBlank()) return

        lifecycleScope.launch {
            try {
                val res = GatewayClient.requestRematch(roomId)
                Toast.makeText(
                    this@HybridActivity,
                    res.message ?: if (res.success) "Pedido de desforra enviado" else "Erro na desforra",
                    Toast.LENGTH_SHORT
                ).show()
            } catch (e: Exception) {
                Toast.makeText(this@HybridActivity, "Erro na desforra: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showMatchScoreDialog() {
        if (roomId.isBlank()) return

        lifecycleScope.launch {
            try {
                val response = GatewayClient.getMatchPoints(roomId)
                if (!response.success) {
                    Toast.makeText(
                        this@HybridActivity,
                        response.message ?: "Nao foi possivel obter a pontuacao",
                        Toast.LENGTH_SHORT
                    ).show()
                    return@launch
                }

                val points = response.points
                val team1 = points?.team1 ?: 0
                val team2 = points?.team2 ?: 0
                val matchesPlayed = response.matchesPlayed ?: 0

                AlertDialog.Builder(this@HybridActivity, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
                    .setTitle("Placar do Jogo")
                    .setMessage(
                        "Equipa 1 (N/S): $team1\n" +
                        "Equipa 2 (E/W): $team2\n\n" +
                        "Jogos concluídos: $matchesPlayed"
                    )
                    .setPositiveButton("OK", null)
                    .show()
            } catch (e: Exception) {
                Toast.makeText(this@HybridActivity, "Erro ao obter pontuacao: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun submitTrumpChoice(choice: String) {
        val resolvedPlayerId = gameState?.trumpSelectorPlayerId
            ?: gameState?.westPlayerId
            ?: resolveCurrentPlayerId(gameState)
        if (resolvedPlayerId.isNullOrBlank()) {
            recognitionProgressText.text = "Nao foi possivel identificar o teu jogador"
            return
        }

        val choiceEnum = when (choice.lowercase()) {
            "top" -> Choice.TOP
            else -> Choice.BOTTOM
        }

        hybridWsClient?.sendAction(
            "select_trump",
            SelectTrumpRequest(
                playerId = resolvedPlayerId,
                choice = choiceEnum,
                gameId = roomId
            )
        )
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

    /**
     * Chamada quando um jogador virtual clica numa carta no ecrã.
     * A carta fica num estado "pendente" até o Host a confirmar fisicamente na mesa com a câmara.
     */
    private fun onVirtualCardTap(card: Card) {
        if (!isVirtualPlayer) {
            return
        }

        val state = hybridState ?: return
        val resolvedMyId = resolveVirtualPlayer(state)?.playerId ?: playerId
        val isMyTurn = gameState?.currentPlayerId == resolvedMyId && state.pendingVirtualPlay == null
        if (!isMyTurn) {
            return
        }

        val cardId = card.id.toIntOrNull() ?: return

        hybridWsClient?.sendAction(
            "virtual_select_card",
            HybridSelectCardRequest(
                gameId = roomId,
                playerId = resolvedMyId,
                card = cardId
            )
        )
    }

    private fun buildRealCopyHand(
        state: HybridRuntimeState,
        currentPlayerId: String?,
        pending: com.example.MVP.models.HybridPendingPlay?
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

    private fun resolveVirtualPlayer(state: HybridRuntimeState): com.example.MVP.models.HybridPlayerRuntime? {
        if (playerId.isNotBlank()) {
            state.virtualPlayers.firstOrNull { it.playerId == playerId }?.let { return it }
        }

        val authUsername = AuthManager.getUsername()
        state.virtualPlayers.firstOrNull { samePersonName(it.playerName, playerName) }?.let { return it }
        state.virtualPlayers.firstOrNull { samePersonName(it.playerName, authUsername) }?.let { return it }

        val normalizedName = playerName.trim().lowercase()
        return state.virtualPlayers.firstOrNull {
            it.playerName.trim().lowercase() == normalizedName
        } ?: state.virtualPlayers.firstOrNull()
    }

    private fun resolveCurrentPlayerId(state: GameStatusResponse?): String? {
        if (state == null) return playerId.ifBlank { null }

        if (playerId.isNotBlank()) return playerId

        return state.players.firstOrNull { samePersonName(it.name, playerName) }?.id
            ?: state.players.firstOrNull { samePersonName(it.name, AuthManager.getUsername()) }?.id
            ?: state.westPlayerId
            ?: state.players.firstOrNull { samePersonName(it.name, state.westPlayer) }?.id
            ?: state.currentPlayerId
    }

    private fun matchesCurrentPlayer(selectorId: String?, selectorName: String?, state: GameStatusResponse): Boolean {
        val currentId = resolveCurrentPlayerId(state)
        if (!selectorId.isNullOrBlank() && selectorId == currentId) return true

        return samePersonName(selectorName, playerName) || samePersonName(selectorName, AuthManager.getUsername())
    }
    
    private fun samePersonName(a: String?, b: String?): Boolean {
        if (a.isNullOrBlank() || b.isNullOrBlank()) return false

        fun normalizeName(value: String): String {
            val normalized = Normalizer.normalize(value, Normalizer.Form.NFD)
            return normalized
                .replace("\\p{Mn}+".toRegex(), "")
                .trim()
                .lowercase()
        }

        return normalizeName(a) == normalizeName(b)
    }

    private suspend fun syncPlayerIdFromStatus() {
        val state = gameState
        if (state != null) {
            val me = state.players.firstOrNull { samePersonName(it.name, playerName) }
            playerId = me?.id ?: playerId
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

    /**
     * Configura o pipeline da câmara usando CameraX.
     * Define um 'analyzer' que processa frames em tempo real para detetar cartas.
     */
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

    /**
     * Verifica se a distribuição de cartas realmente terminou.
     * Retorna true se:
     * - O servidor marca dealDone = true, OU
     * - Todos os virtual players têm >= cardsPerVirtual cartas
     */
    private fun isDistributionReallyDone(hybrid: HybridRuntimeState?): Boolean {
        if (hybrid == null) return true
        
        if (hybrid.dealDone) return true
        
        // Double-check: if all virtual players have enough cards, distribution is done
        return hybrid.virtualPlayers.all { it.cardsCount >= hybrid.cardsPerVirtual }
    }

    /**
     * A função mais importante para o Host:
     * 1. Captura o frame da câmara.
     * 2. Converte-o para Base64.
     * 3. Envia-o para o servidor dependendo da fase (Capturar Trunfo, Distribuir Cartas ou Confirmar Jogada).
     */
    private fun analyzeFrameForHybrid(imageProxy: ImageProxy) {
        try {
            if (!isHost || !isRunning || inFlightRecognition || cvRecognitionPaused) {
                return
            }

            val localHybrid = hybridState
            val localGame = gameState
            val currentPlayerId = localGame?.currentPlayerId
            val currentRole = localHybrid?.playerRoles?.get(currentPlayerId)
            val pending = localHybrid?.pendingVirtualPlay

            // Se for a vez de um virtual e ele ainda não escolheu, paramos de enviar frames (mas mantemos o preview)
            // IMPORTANTE: Só impedimos se a distribuição já estiver concluída.
            if (isDistributionReallyDone(localHybrid) && currentRole == "virtual" && pending == null) {
                return
            }

            val now = SystemClock.elapsedRealtime()
            if (now - lastFrameSentAt < minFrameIntervalMs) {
                return
            }

            val frameBytes = imageProxyToBytes(imageProxy) ?: return
            val frameBase64 = Base64.encodeToString(frameBytes, Base64.NO_WRAP)
            lastFrameSentAt = now
            inFlightRecognition = true

            if (now - lastStreamFrameSentAt >= streamIntervalMs) {
                lastStreamFrameSentAt = now
                hybridWsClient?.sendBinaryFrame(frameBytes)
            }

            if (localGame?.phase == "trump_selection") {
                hybridWsClient?.sendAction(
                    "trump_confirm_capture",
                    HybridConfirmTrumpCaptureRequest(
                        gameId = roomId,
                        hostPlayerId = playerId,
                        frameBase64 = frameBase64
                    )
                )
            } else if (localHybrid != null && !isDistributionReallyDone(localHybrid) && localGame?.phase == "playing") {
                hybridWsClient?.sendAction(
                    "deal_recognize",
                    HybridDealRecognizeRequest(
                        gameId = roomId,
                        playerId = playerId,
                        frameBase64 = frameBase64,
                        targetPlayerId = null
                    )
                )
            } else if (localGame?.phase == "playing") {
                val pendingPlay = localHybrid?.pendingVirtualPlay
                val currentPlayerIdNow = localGame.currentPlayerId

                val capturePlayerId = when {
                    pendingPlay != null && pendingPlay.playerId == currentPlayerIdNow -> pendingPlay.playerId
                    !currentPlayerIdNow.isNullOrBlank() -> currentPlayerIdNow
                    else -> null
                }

                if (!capturePlayerId.isNullOrBlank()) {
                    hybridWsClient?.sendAction(
                        "play_confirm_capture",
                        HybridConfirmCaptureRequest(
                            gameId = roomId,
                            playerId = capturePlayerId,
                            hostPlayerId = playerId,
                            frameBase64 = frameBase64
                        )
                    )
                } else {
                    inFlightRecognition = false
                }
            } else {
                inFlightRecognition = false
            }
        } finally {
            imageProxy.close()
        }
    }

    private fun flashCheck(text: String) {
        if (!isHost) return
        flashJob?.cancel()
        flashJob = lifecycleScope.launch {
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_check)
            recognitionStateImage.colorFilter = null
            recognitionProgressText.text = text
            delay(1200)
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
        }
    }

    private fun flashError(text: String) {
        if (!isHost) return
        flashJob?.cancel()
        flashJob = lifecycleScope.launch {
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_check) // Or a cross if available
            recognitionStateImage.setColorFilter(ContextCompat.getColor(this@HybridActivity, android.R.color.holo_red_dark))
            recognitionProgressText.text = text
            delay(2000)
            recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
            recognitionStateImage.colorFilter = null
        }
    }

    private fun imageProxyToBytes(imageProxy: ImageProxy): ByteArray? {
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

        return output.toByteArray()
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
        cvPauseDialog?.dismiss()
        cvPauseDialog = null
        hybridWsClient?.disconnect()
        hybridMqttSubscriber?.disconnect()
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
