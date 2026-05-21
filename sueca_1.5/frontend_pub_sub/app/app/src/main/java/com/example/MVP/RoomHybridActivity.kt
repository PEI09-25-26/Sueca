package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.GameStatusResponse
import com.example.MVP.models.JoinGameRequest
import com.example.MVP.models.Position
import com.example.MVP.network.GameMqttSubscriber
import com.example.MVP.network.GatewayClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Atividade que gere o lobby (sala) antes de iniciar uma partida em modo Híbrido.
 * Aqui os jogadores escolhem os seus lugares e decidem se querem ser jogadores Virtuais ou Reais.
 */
class RoomHybridActivity : AppCompatActivity() {

    private lateinit var roomId: String
    private lateinit var playerName: String
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

    private var mqttSubscriber: GameMqttSubscriber? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_room_hybrid)

        roomId = intent.getStringExtra("roomId")?.trim().orEmpty()
        playerName = intent.getStringExtra("playerName") ?: "Player${(1000..9999).random()}"
        isHost = intent.getBooleanExtra("isHost", false)

        if (roomId.isBlank()) {
            Toast.makeText(this, "Sala invalida para modo hibrido.", Toast.LENGTH_SHORT).show()
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

        txtRoom.text = "Sala hibrida: $roomId"

        if (isHost) {
            switchVirtualRole.isChecked = false
            switchVirtualRole.isEnabled = false
            switchVirtualRole.text = "Host (jogador real)"
        }

        btnBack.setOnClickListener { finish() }
        wireSeatSelection()

        btnStartHybridGame.setOnClickListener {
            if (selectedSeat.isBlank()) {
                Toast.makeText(this, "Escolhe um lugar primeiro.", Toast.LENGTH_SHORT).show()
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

    /**
     * Inicia a receção de atualizações em tempo real via MQTT.
     * Isto é crucial para que todos os jogadores vejam quem já escolheu lugar sem precisar de fazer refresh manual.
     */
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
            onConnectionError = { error ->
                // Optional: Fallback to polling if needed, but let's stick to MQTT for now.
            }
        )
        
        mqttSubscriber = subscriber
    }

    private fun wireSeatSelection() {
        btnSeatNorth.setOnClickListener { joinWithPosition("north") }
        btnSeatEast.setOnClickListener { joinWithPosition("east") }
        btnSeatSouth.setOnClickListener { joinWithPosition("south") }
        btnSeatWest.setOnClickListener { joinWithPosition("west") }
    }

    /**
     * Faz a chamada ao servidor para ocupar um lugar específico (Norte, Sul, Este ou Oeste).
     * @param position A posição escolhida pelo utilizador.
     */
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
                    )
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
                selectedSeat = position.uppercase()
                btnStartHybridGame.visibility = View.VISIBLE
                hideAllSeatButtons()
                renderSeatHint()
            } catch (_: Exception) {
                Toast.makeText(this@RoomHybridActivity, "Erro a ligar ao servidor.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    /**
     * Atualiza a interface gráfica com base no estado atual da sala recebido do servidor.
     * Mostra quem está em cada lugar e quais os lugares ainda disponíveis.
     */
    private fun updateUI(state: GameStatusResponse) {
        val occupied = state.players.associate { it.position.uppercase() to it.name }
        val available = state.availableSlots?.map { it.position.uppercase() }?.toSet() ?: emptySet()

        txtSeatNorthPlayer.text = occupied["NORTH"] ?: "Livre"
        txtSeatEastPlayer.text = occupied["EAST"] ?: "Livre"
        txtSeatSouthPlayer.text = occupied["SOUTH"] ?: "Livre"
        txtSeatWestPlayer.text = occupied["WEST"] ?: "Livre"

        val me = if (playerId.isNotBlank()) {
            state.players.firstOrNull { it.id == playerId }
        } else {
            state.players.firstOrNull { it.name == playerName }
        }

        if (me != null) {
            selectedSeat = me.position.uppercase()
            playerId = me.id ?: playerId
            hideAllSeatButtons()
            btnStartHybridGame.visibility = View.VISIBLE
        } else {
            renderSeatButton(btnSeatNorth, "NORTH" in available)
            renderSeatButton(btnSeatEast, "EAST" in available)
            renderSeatButton(btnSeatSouth, "SOUTH" in available)
            renderSeatButton(btnSeatWest, "WEST" in available)
            btnStartHybridGame.visibility = View.GONE
        }

        renderSeatHint()
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

    private fun renderSeatHint() {
        txtSeatHint.text = if (selectedSeat.isBlank()) {
            "Escolhe o teu lugar (+)"
        } else {
            "Lugar escolhido: $selectedSeat"
        }
    }

    /**
     * Transição para a atividade principal do jogo híbrido (HybridActivity).
     * Passa as configurações escolhidas (lugar, se é host, se é virtual) via Intent.
     */
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
