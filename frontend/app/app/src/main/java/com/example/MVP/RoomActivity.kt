package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.JoinGameRequest
import com.example.MVP.models.AddBotRequest
import com.example.MVP.models.RemoveParticipantRequest
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Locale

class RoomActivity : AppCompatActivity() {

    private var pollingJob: Job? = null
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
    private lateinit var txtBotPlacementHint: TextView
    private lateinit var btnRemoveNorth: Button
    private lateinit var btnRemoveEast: Button
    private lateinit var btnRemoveSouth: Button
    private lateinit var btnRemoveWest: Button

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
        txtBotPlacementHint = findViewById(R.id.txtBotPlacementHint)
        btnRemoveNorth = findViewById(R.id.btnRemoveNorth)
        btnRemoveEast = findViewById(R.id.btnRemoveEast)
        btnRemoveSouth = findViewById(R.id.btnRemoveSouth)
        btnRemoveWest = findViewById(R.id.btnRemoveWest)

        txtRoom.text = "Sala: $roomId"

        btnBack.setOnClickListener { finish() }

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
        }

    }

    override fun onResume() {
        super.onResume()
        if (roomId != "SALA_LOCAL") {
            startPolling()
        }
    }

    override fun onPause() {
        super.onPause()
        pollingJob?.cancel()
    }

    private fun startPolling() {
        pollingJob = lifecycleScope.launch {
            while (true) {
                try {
                    val state = RetrofitClient.api.getStatus(roomId)
                    // Keep local player id in sync even after activity recreation.
                    if (playerId.isBlank()) {
                        playerId = state.players.firstOrNull { it.name == playerName }?.id ?: ""
                    }
                    updateUI(state)

                    // Move to game as soon as lobby is complete (deck_cutting and beyond).
                    val playerSeated = state.players.any { it.name == playerName || (playerId.isNotBlank() && it.id == playerId) }
                    val gameProgressed = state.phase != "waiting"
                    if (state.gameStarted || (gameProgressed && playerSeated)) {
                        goToGame(state)
                        break
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                }
                delay(1000)
            }
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

        isHost = state.players.firstOrNull()?.id?.let { it == playerId } == true ||
            state.players.firstOrNull()?.name == playerName

        val canUseBotActions = state.phase == "waiting" && isHost && available.isNotEmpty()
        val canRemovePlayers = state.phase == "waiting" && isHost && !botPlacementMode
        botActionsContainer.visibility = if (canUseBotActions) View.VISIBLE else View.GONE
        btnAddRandomBot.isEnabled = canUseBotActions
        btnAddAgent2Bot.isEnabled = canUseBotActions
        btnAddAgent1Bot.isEnabled = canUseBotActions

        if (!canUseBotActions && botPlacementMode) {
            exitBotPlacementMode()
        }

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

        if (hasSelectedSeat && !seatButtonsForBotPlacement) {
            hideAllSeatButtons()
            txtSeatHint.text = "Lugar escolhido: $mySeat"
        } else if (seatButtonsForBotPlacement) {
            txtSeatHint.text = "Escolhe onde colocar o bot"
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

    private fun onSeatActionClick(position: String) {
        if (botPlacementMode) {
            addBotAtPosition(position)
            return
        }
        joinWithPosition(position)
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
        updateBotPlacementVisualState()
        Toast.makeText(this, "Escolhe onde colocar o bot.", Toast.LENGTH_SHORT).show()
    }

    private fun exitBotPlacementMode() {
        botPlacementMode = false
        pendingBotDifficulty = null
        pendingBotNamePrefix = null
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
                val response = RetrofitClient.api.addBot(
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
                    val state = RetrofitClient.api.getStatus(roomId)
                    updateUI(state)
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
                val response = RetrofitClient.api.joinGameWithPosition(
                    JoinGameRequest(
                        name = playerName,
                        gameId = roomId,
                        position = position
                    )
                )

                if (response.success) {
                    playerId = response.playerId ?: playerId
                    Toast.makeText(this@RoomActivity, response.message ?: "Entraste na sala.", Toast.LENGTH_SHORT).show()
                    val state = RetrofitClient.api.getStatus(roomId)
                    updateUI(state)
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
        val showButton = isAvailable && (playerId.isBlank() || forceShowAction)
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
        btnAddAgent1Bot.alpha = if (pendingBotDifficulty == "agent1" && modeActive) 1f else 0.85f
        btnAddAgent2Bot.alpha = if (pendingBotDifficulty == "agent2" && modeActive) 1f else 0.85f

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
                val response = RetrofitClient.api.removeParticipant(
                    RemoveParticipantRequest(
                        actorId = playerId,
                        targetId = targetId,
                        gameId = roomId
                    )
                )

                if (response.success) {
                    Toast.makeText(this@RoomActivity, response.message ?: "$displayName removido.", Toast.LENGTH_SHORT).show()
                    val state = RetrofitClient.api.getStatus(roomId)
                    updateUI(state)
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