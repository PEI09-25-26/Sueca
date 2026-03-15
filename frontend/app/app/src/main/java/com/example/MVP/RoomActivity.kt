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
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

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

        txtRoom.text = "Sala: $roomId"

        btnBack.setOnClickListener { finish() }

        if (roomId == "SALA_LOCAL") {
            hideAllSeatButtons()
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

        val occupied = state.players.associate {
            normalizePosition(it.position) to it.name
        }

        val meById = if (playerId.isNotBlank()) state.players.firstOrNull { it.id == playerId } else null
        val meByName = state.players.firstOrNull { it.name == playerName }
        val me = meById ?: meByName
        val mySeat = normalizePosition(me?.position)
        val hasSelectedSeat = mySeat.isNotBlank()

        renderSeat(
            position = "NORTH",
            occupantName = occupied["NORTH"],
            isAvailable = "NORTH" in available,
            isMine = mySeat == "NORTH",
            button = btnSeatNorth,
            playerLabel = txtSeatNorthPlayer
        )
        renderSeat(
            position = "EAST",
            occupantName = occupied["EAST"],
            isAvailable = "EAST" in available,
            isMine = mySeat == "EAST",
            button = btnSeatEast,
            playerLabel = txtSeatEastPlayer
        )
        renderSeat(
            position = "SOUTH",
            occupantName = occupied["SOUTH"],
            isAvailable = "SOUTH" in available,
            isMine = mySeat == "SOUTH",
            button = btnSeatSouth,
            playerLabel = txtSeatSouthPlayer
        )
        renderSeat(
            position = "WEST",
            occupantName = occupied["WEST"],
            isAvailable = "WEST" in available,
            isMine = mySeat == "WEST",
            button = btnSeatWest,
            playerLabel = txtSeatWestPlayer
        )

        if (hasSelectedSeat) {
            hideAllSeatButtons()
            txtSeatHint.text = "Lugar escolhido: $mySeat"
        } else {
            txtSeatHint.text = "Escolhe o teu lugar (+)"
        }
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
        btnSeatNorth.setOnClickListener { joinWithPosition("north") }
        btnSeatEast.setOnClickListener { joinWithPosition("east") }
        btnSeatSouth.setOnClickListener { joinWithPosition("south") }
        btnSeatWest.setOnClickListener { joinWithPosition("west") }
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
        button: Button,
        playerLabel: TextView
    ) {
        val showButton = isAvailable && playerId.isBlank()
        button.visibility = if (showButton) View.VISIBLE else View.GONE
        button.isEnabled = showButton

        playerLabel.text = when {
            isMine -> "Tu"
            !occupantName.isNullOrBlank() -> occupantName
            isAvailable -> "Livre"
            else -> "Ocupado"
        }

        playerLabel.alpha = if (isMine) 1f else 0.85f
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