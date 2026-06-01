package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.ImageView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.AddBotRequest
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.JoinGameRequest
import com.example.MVP.models.Position
import com.example.MVP.network.GameMqttSubscriber
import com.example.MVP.network.GatewayClient
import com.example.MVP.utils.LogUtils
import kotlinx.coroutines.launch
import java.util.Locale

/**
 * Lobby híbrido: escolha de lugar, papel virtual/real e colocação de bots (host).
 */
class RoomHybridActivity : AppCompatActivity() {

    private lateinit var roomId: String
    private lateinit var playerName: String
    /** Criador da sala (intent); não é alterado por updates MQTT. */
    private var isRoomCreator: Boolean = false
    private var isHost: Boolean = false
    private var selectedSeat: String = ""
    private var playerId: String = ""

    private lateinit var btnSeatNorth: Button
    private lateinit var btnSeatEast: Button
    private lateinit var btnSeatSouth: Button
    private lateinit var btnSeatWest: Button

    private lateinit var txtSeatNorthPlayer: TextView
    private lateinit var txtSeatEastPlayer: TextView
    private lateinit var txtSeatSouthPlayer: TextView
    private lateinit var txtSeatWestPlayer: TextView

    private lateinit var txtSeatHint: TextView
    private lateinit var btnStartHybridGame: Button
    private lateinit var switchVirtualRole: Switch

    private lateinit var botPlacementOverlay: View
    private lateinit var txtBotPlacementHint: TextView

    private var mqttSubscriber: GameMqttSubscriber? = null
    private var latestRoomState: GameStatusResponse? = null
    private var cachedAvailablePositions: Set<String> = emptySet()

    private var botPlacementMode: Boolean = false
    private var pendingBotDifficulty: String? = null
    private var pendingBotNamePrefix: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_room_hybrid)

        roomId = intent.getStringExtra("roomId")?.trim().orEmpty()
        playerName = intent.getStringExtra("playerName") ?: "Player${(1000..9999).random()}"
        isRoomCreator = intent.getBooleanExtra("isHost", false)
        isHost = isRoomCreator
        playerId = intent.getStringExtra("playerId").orEmpty()

        if (roomId.isBlank()) {
            LogUtils.e("Tentativa de abrir RoomHybrid com sala invalida")
            finish()
            return
        }

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
        btnStartHybridGame = findViewById(R.id.btnStartHybridGame)
        switchVirtualRole = findViewById(R.id.switchVirtualRole)

        botPlacementOverlay = findViewById(R.id.botPlacementOverlay)
        txtBotPlacementHint = findViewById(R.id.txtBotPlacementHint)

        txtRoom.text = "Sala hibrida: $roomId"

        if (isRoomCreator) {
            switchVirtualRole.isChecked = false
            switchVirtualRole.isEnabled = false
            switchVirtualRole.text = "Host (jogador real)"
        }

        btnBack.setOnClickListener { finish() }
        wireSeatSelection()

        btnStartHybridGame.setOnClickListener {
            if (selectedSeat.isBlank()) {
                LogUtils.w("Tentativa de iniciar jogo hibrido sem escolher lugar")
                return@setOnClickListener
            }
            goToHybridGame()
        }

        renderSeatHint()
        btnStartHybridGame.visibility = View.GONE
    }

    override fun onResume() {
        super.onResume()
        startMqttUpdates()
    }

    override fun onPause() {
        super.onPause()
        mqttSubscriber?.disconnect()
    }

    private fun startMqttUpdates() {
        mqttSubscriber?.disconnect()

        val subscriber = GameMqttSubscriber(
            brokerHost = "mqtt.suecadaojogo.com",
            brokerPort = 443,
            protocol = "wss"
        )

        subscriber.connectAndSubscribe(
            gameId = roomId,
            onEnvelope = { envelope ->
                runOnUiThread {
                    envelope.state?.let { state ->
                        updateUI(state)
                    }
                }
            },
            onConnectionError = { }
        )

        mqttSubscriber = subscriber
    }

    private fun wireSeatSelection() {
        btnSeatNorth.setOnClickListener { onSeatActionClick("north") }
        btnSeatEast.setOnClickListener { onSeatActionClick("east") }
        btnSeatSouth.setOnClickListener { onSeatActionClick("south") }
        btnSeatWest.setOnClickListener { onSeatActionClick("west") }
    }

    private fun onSeatActionClick(position: String) {
        if (botPlacementMode) {
            addBotAtPosition(position)
            return
        }

        // Check if player already has a seat
        val me = latestRoomState?.players?.firstOrNull { it.id == playerId || it.name == playerName }
        if (me != null && selectedSeat.isNotBlank()) {
            // Show management dialog
            showSeatManagementDialog(position)
            return
        }

        joinWithPosition(position)
    }

    private fun joinWithPosition(position: String) {
        lifecycleScope.launch {
            try {
                val posEnum: Position? = when (position.lowercase()) {
                    "north" -> Position.NORTH
                    "south" -> Position.SOUTH
                    "east" -> Position.EAST
                    "west" -> Position.WEST
                    else -> null
                }

                val response = GatewayClient.joinGame(
                    JoinGameRequest(
                        name = playerName,
                        gameId = roomId,
                        position = posEnum
                    ),
                    mode = "hybrid"
                )

                if (!response.success) {
                    Toast.makeText(
                        this@RoomHybridActivity,
                        response.message ?: "Nao foi possivel entrar no lugar.",
                        Toast.LENGTH_SHORT
                    ).show()
                    return@launch
                }

                playerId = response.playerId ?: playerId
                selectedSeat = position.uppercase(Locale.ROOT)
                btnStartHybridGame.visibility = View.VISIBLE
                latestRoomState?.let { updateUI(it) } ?: run {
                
                    renderSeatHint()
                }
            } catch (e: Exception) {
                LogUtils.e("Erro a ligar ao servidor para entrar em lugar hibrido.", e)
            }
        }
    }

    private fun updateUI(state: GameStatusResponse) {
        latestRoomState = state

        val players = state.players
        val occupiedPositions = players.mapNotNull {
            normalizePosition(it.position).takeIf { pos -> pos.isNotBlank() }
        }.toSet()
        val availableFromState = state.availableSlots
            ?.map { normalizePosition(it.position) }
            ?.filter { it.isNotBlank() }
            ?.toSet()
            ?: emptySet()
        val allSeatPositions = setOf("NORTH", "EAST", "SOUTH", "WEST")
        val available = when {
            availableFromState.isNotEmpty() -> availableFromState
            state.phase == "waiting" -> allSeatPositions - occupiedPositions
            else -> availableFromState
        }
        cachedAvailablePositions = available

        val occupied = players.associate {
            normalizePosition(it.position) to it.name
        }

        val me = if (playerId.isNotBlank()) {
            players.firstOrNull { it.id == playerId }
        } else {
            players.firstOrNull { it.name == playerName }
        }

        isHost = isRoomCreator ||
            (!state.creatorId.isNullOrBlank() && state.creatorId == playerId)

        if (me != null) {
            selectedSeat = normalizePosition(me.position)
            playerId = me.id ?: playerId
            btnStartHybridGame.visibility = View.VISIBLE
        } else {
            btnStartHybridGame.visibility = View.GONE
        }

        val canUseBotActions = state.phase == "waiting" && isRoomCreator && available.isNotEmpty()

        if (!canUseBotActions && botPlacementMode) {
            exitBotPlacementMode()
        }

        val seatButtonsForBotPlacement = botPlacementMode && canUseBotActions
        val mySeat = normalizePosition(me?.position)

        renderHybridSeat("NORTH", occupied["NORTH"], "NORTH" in available, mySeat == "NORTH", seatButtonsForBotPlacement)
        renderHybridSeat("EAST", occupied["EAST"], "EAST" in available, mySeat == "EAST", seatButtonsForBotPlacement)
        renderHybridSeat("SOUTH", occupied["SOUTH"], "SOUTH" in available, mySeat == "SOUTH", seatButtonsForBotPlacement)
        renderHybridSeat("WEST", occupied["WEST"], "WEST" in available, mySeat == "WEST", seatButtonsForBotPlacement)

        updateBotPlacementVisualState()
        renderSeatHint()
    }

    private fun renderHybridSeat(
        position: String,
        occupantName: String?,
        isAvailable: Boolean,
        isMine: Boolean,
        forceShowAction: Boolean
    ) {
        val (button, label) = when (position) {
            "NORTH" -> btnSeatNorth to txtSeatNorthPlayer
            "EAST" -> btnSeatEast to txtSeatEastPlayer
            "SOUTH" -> btnSeatSouth to txtSeatSouthPlayer
            else -> btnSeatWest to txtSeatWestPlayer
        }

        val showButton = forceShowAction || isAvailable
        button.visibility = if (showButton) View.VISIBLE else View.GONE
        button.isEnabled = showButton || forceShowAction

        label.text = when {
            isMine -> "Tu"
            !occupantName.isNullOrBlank() -> occupantName
            isAvailable -> "Livre"
            else -> "Ocupado"
        }
    }

    private fun hideAllSeatButtons() {
        btnSeatNorth.visibility = View.GONE
        btnSeatEast.visibility = View.GONE
        btnSeatSouth.visibility = View.GONE
        btnSeatWest.visibility = View.GONE
    }

    private fun renderSeatHint() {
        txtSeatHint.text = when {
            botPlacementMode -> "Escolhe o lugar para o bot"
            selectedSeat.isBlank() -> "Escolhe o teu lugar (+)"
            else -> "Lugar escolhido: $selectedSeat"
        }
    }

    private fun toggleBotPlacementMode(difficulty: String, namePrefix: String) {
        if (!isRoomCreator) {
            Toast.makeText(this, "So o criador da sala pode adicionar bots.", Toast.LENGTH_SHORT).show()
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
            Toast.makeText(this, "Lugar ja ocupado.", Toast.LENGTH_SHORT).show()
            return
        }

        val difficulty = pendingBotDifficulty ?: return
        val requesterId = playerId.ifBlank { latestRoomState?.creatorId.orEmpty() }
        if (requesterId.isBlank()) {
            Toast.makeText(this, "Escolhe um lugar primeiro.", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            try {
                if (GameSessionManager.getAuthHeader(roomId).isNullOrBlank()) {
                    Toast.makeText(this@RoomHybridActivity, "Sessao da sala indisponivel.", Toast.LENGTH_SHORT).show()
                    return@launch
                }

                val botName = "${pendingBotNamePrefix ?: "Bot"}_${normalizedPosition}_${(100..999).random()}"
                val response = GatewayClient.addBot(
                    AddBotRequest(
                        playerId = requesterId,
                        gameId = roomId,
                        position = Position.valueOf(normalizedPosition),
                        difficulty = difficulty,
                        name = botName
                    ),
                    mode = "hybrid"
                )

                if (response.success) {
                    exitBotPlacementMode()
                } else {
                    Toast.makeText(
                        this@RoomHybridActivity,
                        response.message ?: "Nao foi possivel adicionar o bot.",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            } catch (e: Exception) {
                LogUtils.e("Erro ao adicionar bot hibrido.", e)
                Toast.makeText(this@RoomHybridActivity, "Erro de rede ao adicionar bot.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun updateBotPlacementVisualState() {
        val modeActive = botPlacementMode
        botPlacementOverlay.visibility = if (modeActive) View.VISIBLE else View.GONE
        txtBotPlacementHint.visibility = if (modeActive) View.VISIBLE else View.GONE

        if (modeActive) {
            btnSeatNorth.bringToFront()
            btnSeatEast.bringToFront()
            btnSeatSouth.bringToFront()
            btnSeatWest.bringToFront()
            txtBotPlacementHint.bringToFront()
        }
    }

    private fun showSeatManagementDialog(position: String) {
        val options = if (isHost) {
            arrayOf("Adicionar Agente", "Mudar Lugar")
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
                        0 -> showAgentLevelDialog(position)
                        1 -> changeSeatTo(position)
                    }
                } else {
                    changeSeatTo(position)
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
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

    private fun changeSeatTo(position: String) {
        if (playerId.isBlank()) {
            Toast.makeText(this, "Aguardando identificação do jogador...", Toast.LENGTH_SHORT).show()
            LogUtils.w("Ainda sem player_id. Aguarda um instante.")
            return
        }

        val normalizedPosition = position.uppercase(Locale.ROOT)
        val myCurrentSeat = latestRoomState?.players
            ?.firstOrNull { it.id == playerId || it.name == playerName }
            ?.position
            ?.let { normalizePosition(it) }
            .orEmpty()

        if (normalizedPosition != myCurrentSeat && normalizedPosition !in cachedAvailablePositions) {
            Toast.makeText(this, "Esse lugar já não está livre.", Toast.LENGTH_SHORT).show()
            LogUtils.w("Esse lugar nao esta livre.")
            return
        }

        lifecycleScope.launch {
            try {
                if (GameSessionManager.getAuthHeader(roomId).isNullOrBlank()) {
                    Toast.makeText(this@RoomHybridActivity, "Sessão da sala ainda não disponível.", Toast.LENGTH_SHORT).show()
                    LogUtils.w("Ainda sem sessao da sala. Aguarda 1s.")
                    return@launch
                }

                val response = GatewayClient.changePosition(
                    playerId = playerId,
                    gameId = roomId,
                    position = normalizedPosition
                )

                if (response.success) {
                    val state = GatewayClient.getStatus(roomId)
                    if (state != null) {
                        updateUI(state)
                    }
                } else {
                    Toast.makeText(this@RoomHybridActivity, response.message ?: "Não foi possível alterar lugar.", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                LogUtils.e("Erro ao mudar lugar hibrido.", e)
                Toast.makeText(this@RoomHybridActivity, "Erro ao mudar lugar.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun normalizePosition(position: String?): String {
        return position?.trim()?.uppercase(Locale.ROOT).orEmpty()
    }

    private fun goToHybridGame() {
        val intent = Intent(this, HybridActivity::class.java)
        intent.putExtra("roomId", roomId)
        intent.putExtra("playerName", playerName)
        intent.putExtra("playerId", playerId)
        intent.putExtra("seat", selectedSeat)
        intent.putExtra("isHost", isHost)
        intent.putExtra("isVirtualPlayer", !isHost && switchVirtualRole.isChecked)
        startActivity(intent)
        finish()
    }
}
