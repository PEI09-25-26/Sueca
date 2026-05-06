package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.JoinGameRequest
import com.example.MVP.models.AddBotRequest
import com.example.MVP.models.RemoveParticipantRequest
import com.example.MVP.network.GameMqttSubscriber
import com.example.MVP.network.GatewayClient
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Locale

class RoomActivity : AppCompatActivity() {
    private val logTag = "SuecaRoomUI"
    private val initialRealtimeGraceMs = 4500L
    private val stableRealtimeWindowMs = 1200L

    private var pollingJob: Job? = null
    private var stabilizationJob: Job? = null
    private var mqttSubscriber: GameMqttSubscriber? = null
    private var lastRealtimeUpdateMs: Long = 0L
    private var roomEnteredAtMs: Long = 0L
    private var hasRealtimeState: Boolean = false
    private var hasBrokerRoundTrip: Boolean = false
    private var usingPollingFallback: Boolean = false
    private var latestRoomState: GameStatusResponse? = null
    private lateinit var roomId: String
    private lateinit var playerId: String
    private lateinit var playerName: String

    private lateinit var btnSeatNorth: Button
    private lateinit var btnSeatEast: Button
    private lateinit var btnSeatSouth: Button
    private lateinit var btnSeatWest: Button

    private lateinit var txtSeatNorthPlayer: TextView
    private lateinit var txtSeatEastPlayer: TextView
    private lateinit var txtSeatSouthPlayer: TextView
    private lateinit var txtSeatWestPlayer: TextView

    private lateinit var txtSeatHint: TextView
    private lateinit var btnAddRandomBot: Button
    private lateinit var btnAddAgent1Bot: Button
    private lateinit var btnAddAgent2Bot: Button
    private lateinit var botActionsContainer: View
    private lateinit var botPlacementOverlay: View
    private lateinit var mqttConnectingOverlay: View
    private lateinit var txtBotPlacementHint: TextView
    private lateinit var btnRemoveNorth: Button
    private lateinit var btnRemoveEast: Button
    private lateinit var btnRemoveSouth: Button
    private lateinit var btnRemoveWest: Button
    private lateinit var roomVisibilityContainer: View
    private lateinit var imgRoomVisibilityLock: ImageButton
    private lateinit var txtRoomVisibilityHint: TextView

    private var isHost: Boolean = false
    private var botPlacementMode: Boolean = false
    private var pendingBotDifficulty: String? = null
    private var pendingBotNamePrefix: String? = null
    private var cachedAvailablePositions: Set<String> = emptySet()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_room_mvp)

        roomId = intent.getStringExtra("roomId") ?: "SALA_LOCAL"
        playerId = intent.getStringExtra("playerId") ?: ""
        playerName = intent.getStringExtra("playerName") ?: ""

        val txtRoom = findViewById<TextView>(R.id.txtRoom)
        val btnBack = findViewById<ImageView>(R.id.backButton)
        btnSeatNorth = findViewById(R.id.btnSeatNorth)
        btnSeatEast = findViewById(R.id.btnSeatEast)
        btnSeatSouth = findViewById(R.id.btnSeatSouth)
        btnSeatWest = findViewById(R.id.btnSeatWest)
        txtSeatNorthPlayer = findViewById(R.id.txtSeatNorthPlayer)
        txtSeatEastPlayer = findViewById(R.id.txtSeatEastPlayer)
        txtSeatSouthPlayer = findViewById(R.id.txtSeatSouthPlayer)
        txtSeatWestPlayer = findViewById(R.id.txtSeatWestPlayer)
        txtSeatHint = findViewById(R.id.txtSeatHint)
        btnAddRandomBot = findViewById(R.id.btnAddRandomBot)
        btnAddAgent1Bot = findViewById(R.id.btnAddAgent1Bot)
        btnAddAgent2Bot = findViewById(R.id.btnAddAgent2Bot)
        botActionsContainer = findViewById(R.id.botActionsContainer)
        botPlacementOverlay = findViewById(R.id.botPlacementOverlay)
        mqttConnectingOverlay = findViewById(R.id.mqttConnectingOverlay)
        txtBotPlacementHint = findViewById(R.id.txtBotPlacementHint)
        btnRemoveNorth = findViewById(R.id.btnRemoveNorth)
        btnRemoveEast = findViewById(R.id.btnRemoveEast)
        btnRemoveSouth = findViewById(R.id.btnRemoveSouth)
        btnRemoveWest = findViewById(R.id.btnRemoveWest)
        roomVisibilityContainer = findViewById(R.id.roomVisibilityContainer)
        imgRoomVisibilityLock = findViewById(R.id.imgRoomVisibilityLock)
        txtRoomVisibilityHint = findViewById(R.id.txtRoomVisibilityHint)

        txtRoom.text = "Sala: $roomId"

        btnBack.setOnClickListener { leaveRoomAndExit() }
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                leaveRoomAndExit()
            }
        })

        if (roomId == "SALA_LOCAL") {
            hideAllSeatButtons()
            botActionsContainer.visibility = View.GONE
            txtSeatNorthPlayer.text = "Parceiro Bot"
            txtSeatSouthPlayer.text = "Tu (Local)"
            txtSeatEastPlayer.text = "Adversario 1"
            txtSeatWestPlayer.text = "Adversario 2"
            txtSeatHint.text = "Modo local"
        } else {
            if (playerName.isBlank()) {
                playerName = "Player${(1000..9999).random()}"
            }
            wireSeatSelection()
            wireBotActions()
            wireVisibilityToggle()
        }

    }

    override fun onResume() {
        super.onResume()
        if (roomId != "SALA_LOCAL") {
            roomEnteredAtMs = System.currentTimeMillis()
            hasRealtimeState = false
            hasBrokerRoundTrip = false
            usingPollingFallback = false
            lastRealtimeUpdateMs = 0L
            showMqttConnectingOverlay()
            lifecycleScope.launch {
                GatewayClient.setRoomMode(roomId, "virtual")
            }
            startRealtimeUpdates()
            startPolling()
        }
    }

    override fun onPause() {
        super.onPause()
        pollingJob?.cancel()
        stabilizationJob?.cancel()
        mqttSubscriber?.disconnect()
        mqttSubscriber = null
        hideMqttConnectingOverlay()
    }

    private fun startRealtimeUpdates() {
        if (roomId.isBlank()) return

        Log.i(logTag, "Starting realtime updates roomId=$roomId broker=${RetrofitClient.MQTT_BROKER_HOST}:${RetrofitClient.MQTT_BROKER_PORT} (pls work)")

        val subscriber = GameMqttSubscriber(
            brokerHost = RetrofitClient.MQTT_BROKER_HOST,
            brokerPort = RetrofitClient.MQTT_BROKER_PORT
        )
        mqttSubscriber = subscriber

        subscriber.connectAndSubscribe(
            gameId = roomId,
            onEnvelope = { envelope ->
                runOnUiThread {
                    val state = envelope.state ?: return@runOnUiThread
                    applyState(state)
                    hasRealtimeState = true
                    usingPollingFallback = false
                    lastRealtimeUpdateMs = System.currentTimeMillis()
                    scheduleHideOverlayWhenStable("mqtt")
                    Log.i(logTag, "Realtime state received roomId=$roomId; waiting for stabilization window (don't panic)")
                }
            },
            onConnectionError = { error ->
                Log.e(logTag, "MQTT connection error roomId=$roomId: $error (well, I guess it's not working)")
                runOnUiThread {
                    // Keep loading visible. Better stuck than fake-ready.
                }
                lastRealtimeUpdateMs = 0L
                usingPollingFallback = true
            },
            onBrokerRoundTrip = {
                runOnUiThread {
                    hasBrokerRoundTrip = true
                    Log.i(logTag, "Broker round-trip confirmed roomId=$roomId (we are so back)")
                    if (hasRealtimeState) {
                        scheduleHideOverlayWhenStable("mqtt")
                    }
                }
            }
        )
    }

    private fun startPolling() {
        pollingJob = lifecycleScope.launch {
            while (true) {
                try {
                    val now = System.currentTimeMillis()

                    // Give MQTT a tiny head start before we start hammering fallback GETs.
                    val inInitialGrace = !hasRealtimeState && (now - roomEnteredAtMs) < initialRealtimeGraceMs
                    if (inInitialGrace) {
                        delay(500)
                        continue
                    }

                    // If MQTT handshake is healthy, don't spam REST just because lobby is chill.
                    if (hasRealtimeState && hasBrokerRoundTrip && !usingPollingFallback) {
                        delay(2000)
                        continue
                    }

                    val staleRealtime = (System.currentTimeMillis() - lastRealtimeUpdateMs) > 15000
                    if (staleRealtime) {
                        if (!usingPollingFallback) {
                            Log.w(logTag, "Switching to polling fallback roomId=$roomId staleMs=${System.currentTimeMillis() - lastRealtimeUpdateMs} (plan B time)")
                            usingPollingFallback = true
                        }
                        val state = GatewayClient.getStatus(roomId)
                        if (state != null) {
                            applyState(state)
                            lastRealtimeUpdateMs = System.currentTimeMillis()

                            // Still waiting for broker round-trip gate before we call it stable.
                            if (hasRealtimeState && hasBrokerRoundTrip) {
                                scheduleHideOverlayWhenStable("fallback")
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.e(logTag, "Polling error roomId=$roomId (this is fine)", e)
                    e.printStackTrace()
                }
                delay(5000)
            }
        }
    }

    private fun scheduleHideOverlayWhenStable(source: String) {
        stabilizationJob?.cancel()
        stabilizationJob = lifecycleScope.launch {
            delay(stableRealtimeWindowMs)

            val staleRealtime = (System.currentTimeMillis() - lastRealtimeUpdateMs) > 3000
            if (hasRealtimeState && hasBrokerRoundTrip && !staleRealtime && !usingPollingFallback) {
                hideMqttConnectingOverlay()
                Log.i(logTag, "Room stabilized via $source roomId=$roomId; loading hidden (finally)")
            }
        }
    }

    private fun showMqttConnectingOverlay() {
        mqttConnectingOverlay.visibility = View.VISIBLE
    }

    private fun hideMqttConnectingOverlay() {
        mqttConnectingOverlay.visibility = View.GONE
    }

    private fun applyState(state: GameStatusResponse) {
        latestRoomState = state

        // Keep local player id in sync even after activity recreation.
        if (playerId.isBlank()) {
            playerId = state.players.firstOrNull { it.name == playerName }?.id ?: ""
        }
        updateUI(state)

        val isHost = state.creatorId == playerId && playerId.isNotBlank()
        if (state.players.size == 4 && !state.gameStarted && isHost) {
            lifecycleScope.launch { GatewayClient.startGame(roomId) }
        }

        // Move to game as soon as lobby is complete (deck_cutting and beyond).
        val playerSeated = state.players.any { it.name == playerName || (playerId.isNotBlank() && it.id == playerId) }
        val gameProgressed = state.phase != "waiting"
        if (state.gameStarted || (gameProgressed && playerSeated)) {
            goToGame(state)
        }
    }

    private fun updateUI(state: GameStatusResponse) {
        val available = state.availableSlots
            ?.map { it.position.uppercase() }
            ?.toSet()
            ?: emptySet()
        cachedAvailablePositions = available

        val occupied = state.players.associate {
            normalizePosition(it.position) to it.name
        }
        val occupiedPlayers = state.players.associateBy { normalizePosition(it.position) }

        val meById = if (playerId.isNotBlank()) state.players.firstOrNull { it.id == playerId } else null
        val meByName = state.players.firstOrNull { it.name == playerName }
        val me = meById ?: meByName
        val mySeat = normalizePosition(me?.position)
        val hasSelectedSeat = mySeat.isNotBlank()

        if (playerId.isNotBlank() && meById == null && meByName == null) {
            playerId = ""
        }

        val isHost = state.players.firstOrNull()?.id?.let { it == playerId } == true ||
            state.players.firstOrNull()?.name == playerName
        this.isHost = isHost

        val canUseBotActions = state.phase == "waiting" && isHost && available.isNotEmpty()
        val canRemovePlayers = state.phase == "waiting" && isHost && !botPlacementMode

        // Keep the old bot actions hidden; seat management now happens from the seat popup.
        botActionsContainer.visibility = View.GONE

        roomVisibilityContainer.visibility = if (isHost) View.VISIBLE else View.GONE
        if (isHost) {
            val isPublic = state.isPublic ?: true
            imgRoomVisibilityLock.setImageResource(if (isPublic) R.drawable.ic_lock_open else R.drawable.ic_lock_closed)
            imgRoomVisibilityLock.alpha = if (isPublic) 1.0f else 0.7f
            txtRoomVisibilityHint.text = if (isPublic) "Qualquer pessoa pode entrar" else "Necessario codigo para entrar"
        }

        if (!canUseBotActions && botPlacementMode) {
            exitBotPlacementMode()
        }

        val hostCanManageSeats = isHost && state.phase == "waiting"
        val seatButtonsForBotPlacement = botPlacementMode && canUseBotActions

        renderSeat(
            position = "NORTH",
            occupantName = occupied["NORTH"],
            isAvailable = "NORTH" in available,
            isMine = mySeat == "NORTH",
            forceShowAction = seatButtonsForBotPlacement,
            occupantId = occupiedPlayers["NORTH"]?.id,
            canRemove = canRemovePlayers,
            removeButton = btnRemoveNorth,
            button = btnSeatNorth,
            playerLabel = txtSeatNorthPlayer
        )
        renderSeat(
            position = "EAST",
            occupantName = occupied["EAST"],
            isAvailable = "EAST" in available,
            isMine = mySeat == "EAST",
            forceShowAction = seatButtonsForBotPlacement,
            occupantId = occupiedPlayers["EAST"]?.id,
            canRemove = canRemovePlayers,
            removeButton = btnRemoveEast,
            button = btnSeatEast,
            playerLabel = txtSeatEastPlayer
        )
        renderSeat(
            position = "SOUTH",
            occupantName = occupied["SOUTH"],
            isAvailable = "SOUTH" in available,
            isMine = mySeat == "SOUTH",
            forceShowAction = seatButtonsForBotPlacement,
            occupantId = occupiedPlayers["SOUTH"]?.id,
            canRemove = canRemovePlayers,
            removeButton = btnRemoveSouth,
            button = btnSeatSouth,
            playerLabel = txtSeatSouthPlayer
        )
        renderSeat(
            position = "WEST",
            occupantName = occupied["WEST"],
            isAvailable = "WEST" in available,
            isMine = mySeat == "WEST",
            forceShowAction = seatButtonsForBotPlacement,
            occupantId = occupiedPlayers["WEST"]?.id,
            canRemove = canRemovePlayers,
            removeButton = btnRemoveWest,
            button = btnSeatWest,
            playerLabel = txtSeatWestPlayer
        )

        if (seatButtonsForBotPlacement) {
            txtSeatHint.text = "Escolhe onde colocar o bot"
        } else if (hasSelectedSeat) {
            txtSeatHint.text = "Lugar escolhido: $mySeat"
        } else {
            txtSeatHint.text = "Escolhe o teu lugar (+)"
        }

        updateBotPlacementVisualState()
    }

    private fun goToGame(state: GameStatusResponse) {
        val intent = Intent(this, GameActivity::class.java)
        intent.putExtra("roomId", state.gameId ?: roomId)
        intent.putExtra("playerId", playerId)
        intent.putExtra("playerName", playerName)
        startActivity(intent)
        finish()
    }

    private fun goToGameMock() {
        val intent = Intent(this, GameActivity::class.java)
        intent.putExtra("roomId", "SALA_LOCAL")
        intent.putExtra("playerId", "ID_LOCAL")
        intent.putExtra("playerName", "Local")
        startActivity(intent)
        finish()
    }

    private fun wireSeatSelection() {
        btnSeatNorth.setOnClickListener { onSeatActionClick("north") }
        btnSeatEast.setOnClickListener { onSeatActionClick("east") }
        btnSeatSouth.setOnClickListener { onSeatActionClick("south") }
        btnSeatWest.setOnClickListener { onSeatActionClick("west") }
    }

    private fun wireBotActions() {
        btnAddRandomBot.setOnClickListener {
            toggleBotPlacementMode("random", "RandomBot")
        }

        btnAddAgent1Bot.setOnClickListener {
            toggleBotPlacementMode("weak", "WeakBot")
        }

        btnAddAgent2Bot.setOnClickListener {
            toggleBotPlacementMode("Average", "AverageBot")
        }

        botPlacementOverlay.setOnClickListener {
            // Keep overlay clickable to dim the UI but avoid accidental action underneath.
        }
    }

    private fun wireVisibilityToggle() {
        imgRoomVisibilityLock.setOnClickListener {
            if (!isHost) return@setOnClickListener

            val currentIsPublic = latestRoomState?.isPublic ?: true
            val nextIsPublic = !currentIsPublic

            lifecycleScope.launch {
                try {
                    val response = GatewayClient.updateRoomVisibility(
                        playerId = playerId,
                        gameId = roomId,
                        isPublic = nextIsPublic
                    )

                    if (response.success) {
                        Toast.makeText(
                            this@RoomActivity,
                            if (nextIsPublic) "Sala agora é pública" else "Sala agora é privada",
                            Toast.LENGTH_SHORT
                        ).show()

                        // Update UI immediately
                        imgRoomVisibilityLock.setImageResource(if (nextIsPublic) R.drawable.ic_lock_open else R.drawable.ic_lock_closed)
                        imgRoomVisibilityLock.alpha = if (nextIsPublic) 1.0f else 0.7f
                        txtRoomVisibilityHint.text = if (nextIsPublic) "Qualquer pessoa pode entrar" else "Necessario codigo para entrar"

                    } else {
                        Toast.makeText(
                            this@RoomActivity,
                            "Erro ao mudar visibilidade: ${response.message}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@RoomActivity, "Erro de ligação.", Toast.LENGTH_SHORT).show()
                }
            }
        }

        // Also allow tapping the whole container
        roomVisibilityContainer.setOnClickListener { imgRoomVisibilityLock.performClick() }
    }

    private fun onSeatActionClick(position: String) {
        if (botPlacementMode) {
            addBotAtPosition(position)
            return
        }

        if (playerId.isNotBlank()) {
            showSeatManagementDialog(position)
            return
        }

        joinWithPosition(position)
    }

    private fun showSeatManagementDialog(position: String) {
        val options = if (isHost) {
            arrayOf("Convidar Amigo", "Adicionar Agente", "Mudar Lugar")
        } else {
            arrayOf("Mudar Lugar")
        }
        val adapter = ArrayAdapter(this, R.layout.dialog_custom_item, options)
        
        val titleView = layoutInflater.inflate(R.layout.dialog_custom_title, null) as TextView
        titleView.text = "Lugar ${position.replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.ROOT) else it.toString() }}"

        AlertDialog.Builder(this, R.style.CustomDialogTheme)
            .setCustomTitle(titleView)
            .setAdapter(adapter) { _, which ->
                if (isHost) {
                    when (which) {
                        0 -> showInviteFriendDialog(position)
                        1 -> showAgentLevelDialog(position)
                        2 -> changeSeatTo(position)
                    }
                } else {
                    changeSeatTo(position)
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun leaveRoomAndExit() {
        if (roomId == "SALA_LOCAL") {
            finish()
            return
        }

        if (playerId.isBlank()) {
            finish()
            return
        }

        lifecycleScope.launch {
            try {
                runCatching {
                    GatewayClient.leaveRoom(roomId, playerId)
                }
            } finally {
                finish()
            }
        }
    }

    private fun changeSeatTo(position: String) {
        if (playerId.isBlank()) {
            Toast.makeText(this, "Ainda sem player_id. Aguarda um instante.", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                val response = GatewayClient.changePosition(
                    playerId = playerId,
                    gameId = roomId,
                    position = position.lowercase(Locale.ROOT)
                )

                if (response.success) {
                    Toast.makeText(this@RoomActivity, response.message ?: "Lugar alterado.", Toast.LENGTH_SHORT).show()
                    val state = GatewayClient.getStatus(roomId)
                    if (state != null) {
                        applyState(state)
                    }
                } else {
                    Toast.makeText(this@RoomActivity, response.message ?: "Nao foi possivel alterar lugar.", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RoomActivity, "Erro ao alterar lugar.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showInviteFriendDialog(position: String) {
        val uid = AuthManager.getUid() ?: return
        lifecycleScope.launch {
            FriendsManager.listFriends(uid).onSuccess { friends ->
                if (friends.isEmpty()) {
                    Toast.makeText(this@RoomActivity, "Ainda não tens amigos.", Toast.LENGTH_SHORT).show()
                    return@onSuccess
                }

                val names = friends.map { it.username }.toTypedArray()
                val adapter = ArrayAdapter(this@RoomActivity, R.layout.dialog_custom_item, names)

                val titleView = layoutInflater.inflate(R.layout.dialog_custom_title, null) as TextView
                titleView.text = "Convidar para Mesa ${position.replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.ROOT) else it.toString() }}"

                AlertDialog.Builder(this@RoomActivity, R.style.CustomDialogTheme)
                    .setCustomTitle(titleView)
                    .setAdapter(adapter) { _, which ->
                        val friend = friends[which]
                        Toast.makeText(this@RoomActivity, "Convite enviado para ${friend.username}", Toast.LENGTH_SHORT).show()
                    }
                    .setNegativeButton("Voltar", null)
                    .show()
            }.onFailure {
                Toast.makeText(this@RoomActivity, "Erro ao carregar amigos.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showAgentLevelDialog(position: String) {
        val levels = arrayOf(
            "Nível 1",
            "Nível 2",
            "Nível 3",
            "Nível 4"
        )
        val adapter = ArrayAdapter(this, R.layout.dialog_custom_item, levels)
        
        val titleView = layoutInflater.inflate(R.layout.dialog_custom_title, null) as TextView
        titleView.text = "Escolher nível do agente"

        AlertDialog.Builder(this, R.style.CustomDialogTheme)
            .setCustomTitle(titleView)
            .setAdapter(adapter) { _, which ->
                val (difficulty, namePrefix) = when (which) {
                    0 -> "random" to "BOT_LV1"
                    1 -> "weak" to "BOT_LV2"
                    2 -> "Average" to "BOT_LV3"
                    3 -> "smart" to "BOT_LV4"
                    else -> "random" to "Bot"
                }
                
                pendingBotDifficulty = difficulty
                pendingBotNamePrefix = namePrefix
                addBotAtPosition(position)
            }
            .setNegativeButton("Voltar", null)
            .show()
    }

    private fun toggleBotPlacementMode(difficulty: String, namePrefix: String) {
        if (!isHost) {
            Toast.makeText(this, "So o host pode adicionar bots.", Toast.LENGTH_SHORT).show()
            return
        }

        if (botPlacementMode && pendingBotDifficulty == difficulty) {
            exitBotPlacementMode()
            return
        }

        pendingBotDifficulty = difficulty
        pendingBotNamePrefix = namePrefix
        botPlacementMode = true
        latestRoomState?.let { updateUI(it) }
        updateBotPlacementVisualState()
        Toast.makeText(this, "Escolhe onde colocar o bot.", Toast.LENGTH_SHORT).show()
    }

    private fun exitBotPlacementMode() {
        botPlacementMode = false
        pendingBotDifficulty = null
        pendingBotNamePrefix = null
        latestRoomState?.let { updateUI(it) }
        updateBotPlacementVisualState()
    }

    private fun addBotAtPosition(position: String) {
        val normalizedPosition = position.uppercase(Locale.ROOT)
        if (normalizedPosition !in cachedAvailablePositions) {
            Toast.makeText(this, "Esse lugar nao esta livre.", Toast.LENGTH_SHORT).show()
            return
        }

        val difficulty = pendingBotDifficulty ?: return
        if (playerId.isBlank()) {
            Toast.makeText(this, "Ainda sem player_id do host. Aguarda 1s.", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                val botName = "${pendingBotNamePrefix ?: "Bot"}_${normalizedPosition}_${(100..999).random()}"
                val response = GatewayClient.addBot(
                    AddBotRequest(
                        playerId = playerId,
                        gameId = roomId,
                        position = position.lowercase(Locale.ROOT),
                        difficulty = difficulty,
                        name = botName
                    )
                )

                if (response.success) {
                    Toast.makeText(this@RoomActivity, response.message ?: "Bot adicionado.", Toast.LENGTH_SHORT).show()
                    exitBotPlacementMode()
                } else {
                    Toast.makeText(this@RoomActivity, response.message ?: "Nao foi possivel adicionar bot.", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RoomActivity, "Erro ao adicionar bot.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun joinWithPosition(position: String) {
        if (playerId.isNotBlank()) {
            Toast.makeText(this, "Ja escolheste um lugar.", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                val response = GatewayClient.joinGame(
                    JoinGameRequest(
                        name = playerName,
                        gameId = roomId,
                        position = position
                    )
                )

                if (response.success) {
                    playerId = response.playerId ?: playerId
                    Toast.makeText(this@RoomActivity, response.message ?: "Entraste na sala.", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@RoomActivity, response.message ?: "Nao foi possivel escolher esse lugar.", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RoomActivity, "Erro ao escolher lugar.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun renderSeat(
        position: String,
        occupantName: String?,
        isAvailable: Boolean,
        isMine: Boolean,
        forceShowAction: Boolean,
        occupantId: String?,
        canRemove: Boolean,
        removeButton: Button,
        button: Button,
        playerLabel: TextView
    ) {
        val showButton = isAvailable
        button.visibility = if (showButton) View.VISIBLE else View.GONE
        button.isEnabled = showButton

        val showRemove = canRemove && !occupantId.isNullOrBlank() && occupantId != playerId
        removeButton.visibility = if (showRemove) View.VISIBLE else View.GONE
        removeButton.isEnabled = showRemove
        if (showRemove) {
            removeButton.setOnClickListener {
                removeParticipant(occupantId!!, occupantName ?: position)
            }
        } else {
            removeButton.setOnClickListener(null)
        }

        playerLabel.text = when {
            isMine -> "Tu"
            !occupantName.isNullOrBlank() -> occupantName
            isAvailable -> "Livre"
            else -> "Ocupado"
        }

        playerLabel.alpha = if (isMine) 1f else 0.85f
    }

    private fun updateBotPlacementVisualState() {
        val modeActive = botPlacementMode
        botPlacementOverlay.visibility = if (modeActive) View.VISIBLE else View.GONE
        txtBotPlacementHint.visibility = if (modeActive) View.VISIBLE else View.GONE

        btnAddRandomBot.alpha = if (pendingBotDifficulty == "random" && modeActive) 1f else 0.85f
        btnAddAgent1Bot.alpha = if (pendingBotDifficulty == "weak" && modeActive) 1f else 0.85f
        btnAddAgent2Bot.alpha = if (pendingBotDifficulty == "Average" && modeActive) 1f else 0.85f

        if (modeActive) {
            btnSeatNorth.bringToFront()
            btnSeatEast.bringToFront()
            btnSeatSouth.bringToFront()
            btnSeatWest.bringToFront()
            btnRemoveNorth.bringToFront()
            btnRemoveEast.bringToFront()
            btnRemoveSouth.bringToFront()
            btnRemoveWest.bringToFront()
            txtBotPlacementHint.bringToFront()
        }
    }

    private fun removeParticipant(targetId: String, displayName: String) {
        if (!isHost) {
            Toast.makeText(this, "So o host pode remover jogadores.", Toast.LENGTH_SHORT).show()
            return
        }
        if (playerId.isBlank()) {
            Toast.makeText(this, "Host sem player_id. Aguarda 1s.", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                val response = GatewayClient.removeParticipant(
                    RemoveParticipantRequest(
                        actorId = playerId,
                        targetId = targetId,
                        gameId = roomId
                    )
                )

                if (response.success) {
                    Toast.makeText(this@RoomActivity, response.message ?: "$displayName removido.", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@RoomActivity, response.message ?: "Nao foi possivel remover.", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@RoomActivity, "Erro ao remover participante.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun hideAllSeatButtons() {
        btnSeatNorth.visibility = View.GONE
        btnSeatEast.visibility = View.GONE
        btnSeatSouth.visibility = View.GONE
        btnSeatWest.visibility = View.GONE
    }

    private fun normalizePosition(position: String?): String {
        if (position.isNullOrBlank()) return ""
        val p = position.uppercase()
        return when {
            p.contains("NORTH") -> "NORTH"
            p.contains("SOUTH") -> "SOUTH"
            p.contains("EAST") -> "EAST"
            p.contains("WEST") -> "WEST"
            else -> p
        }
    }
}