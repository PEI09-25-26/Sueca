package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class RoomHybridActivity : AppCompatActivity() {

    private lateinit var roomId: String
    private lateinit var playerName: String
    private var isHost: Boolean = false
    private var selectedSeat: String = ""

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
    private var isRegisteredInRoom: Boolean = false
    private var gameStarted: Boolean = false

    private val occupiedByBots = mutableMapOf(
        "NORTH" to "Jogador Mesa 1",
        "EAST" to "Jogador Mesa 2",
        "WEST" to "Jogador Mesa 3"
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_room_hybrid)

        roomId = intent.getStringExtra("roomId") ?: "HBMOCK"
        playerName = intent.getStringExtra("playerName") ?: "Player"
        isHost = intent.getBooleanExtra("isHost", false)

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

        txtRoom.text = "Sala hibrida: $roomId"

        btnBack.setOnClickListener { finish() }
        wireSeatSelection()

        btnStartHybridGame.setOnClickListener {
            if (selectedSeat.isBlank()) {
                Toast.makeText(this, "Escolhe um lugar primeiro.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            goToHybridGame()
        }

        renderInitialState()
    }

    override fun onDestroy() {
        if (isFinishing && isRegisteredInRoom && !gameStarted) {
            HybridMenuActivity.unregisterMockRoomPlayer(roomId, playerName)
        }
        super.onDestroy()
    }

    private fun wireSeatSelection() {
        btnSeatNorth.setOnClickListener { selectSeat("NORTH") }
        btnSeatEast.setOnClickListener { selectSeat("EAST") }
        btnSeatSouth.setOnClickListener { selectSeat("SOUTH") }
        btnSeatWest.setOnClickListener { selectSeat("WEST") }
    }

    private fun selectSeat(seat: String) {
        val currentlyOccupiedByBot = occupiedByBots.containsKey(seat)

        if (currentlyOccupiedByBot) {
            Toast.makeText(this, "Lugar ocupado no mock.", Toast.LENGTH_SHORT).show()
            return
        }

        selectedSeat = seat
        if (!isRegisteredInRoom) {
            HybridMenuActivity.registerMockRoomPlayer(roomId, playerName)
            isRegisteredInRoom = true
        }
        txtSeatHint.text = "Lugar escolhido: $seat"
        txtSeatSouthPlayer.text = if (seat == "SOUTH") "Tu ($playerName)" else txtSeatSouthPlayer.text
        txtSeatNorthPlayer.text = if (seat == "NORTH") "Tu ($playerName)" else txtSeatNorthPlayer.text
        txtSeatEastPlayer.text = if (seat == "EAST") "Tu ($playerName)" else txtSeatEastPlayer.text
        txtSeatWestPlayer.text = if (seat == "WEST") "Tu ($playerName)" else txtSeatWestPlayer.text

        hideAllSeatButtons()
        btnStartHybridGame.visibility = View.VISIBLE
    }

    private fun renderInitialState() {
        txtSeatNorthPlayer.text = occupiedByBots["NORTH"] ?: "Livre"
        txtSeatEastPlayer.text = occupiedByBots["EAST"] ?: "Livre"
        txtSeatWestPlayer.text = occupiedByBots["WEST"] ?: "Livre"
        txtSeatSouthPlayer.text = if (occupiedByBots.containsKey("SOUTH")) occupiedByBots["SOUTH"] else "Livre"

        renderSeatButton(btnSeatNorth, !occupiedByBots.containsKey("NORTH"))
        renderSeatButton(btnSeatEast, !occupiedByBots.containsKey("EAST"))
        renderSeatButton(btnSeatSouth, !occupiedByBots.containsKey("SOUTH"))
        renderSeatButton(btnSeatWest, !occupiedByBots.containsKey("WEST"))

        btnStartHybridGame.visibility = View.GONE
    }

    private fun renderSeatButton(button: Button, available: Boolean) {
        button.visibility = if (available) View.VISIBLE else View.GONE
        button.isEnabled = available
    }

    private fun hideAllSeatButtons() {
        btnSeatNorth.visibility = View.GONE
        btnSeatEast.visibility = View.GONE
        btnSeatSouth.visibility = View.GONE
        btnSeatWest.visibility = View.GONE
    }

    private fun goToHybridGame() {
        gameStarted = true
        val intent = Intent(this, HybridActivity::class.java)
        intent.putExtra("roomId", roomId)
        intent.putExtra("playerName", playerName)
        intent.putExtra("seat", selectedSeat)
        intent.putExtra("isHost", isHost)
        // Mock value for now. Later this should come from room state/backend.
        intent.putExtra("virtualPhonePlayers", if (isHost) 1 else 0)
        startActivity(intent)
        finish()
    }
}
