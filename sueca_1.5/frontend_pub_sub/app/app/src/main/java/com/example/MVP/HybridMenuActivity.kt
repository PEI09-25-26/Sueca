package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.text.InputFilter
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.network.GatewayClient
import com.example.MVP.utils.LogUtils
import kotlinx.coroutines.launch

class HybridMenuActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_hybrid_menu)

        val backButton = findViewById<ImageView>(R.id.backButton)
        val inputName = findViewById<EditText>(R.id.inputName)
        val inputRoomId = findViewById<EditText>(R.id.inputRoomId)
        val btnCreateRoom = findViewById<Button>(R.id.btnCreateRoom)
        val btnJoinRoom = findViewById<Button>(R.id.btnJoinRoom)

        backButton.setOnClickListener { finish() }

        val noWhitespaceFilter = InputFilter { source, start, end, _, _, _ ->
            val filtered = StringBuilder()
            for (i in start until end) {
                val c = source[i]
                if (!c.isWhitespace()) {
                    filtered.append(c)
                }
            }
            if (filtered.length == end - start) null else filtered.toString()
        }

        inputName.filters = arrayOf(noWhitespaceFilter)
        inputRoomId.filters = arrayOf(noWhitespaceFilter, InputFilter.AllCaps())

        btnCreateRoom.setOnClickListener {
            val name = inputName.text.toString().ifBlank { randomName() }
            lifecycleScope.launch {
                try {
                    val response = GatewayClient.createRoom(name, mode = "hybrid")
                    if (!response.success) {
                        LogUtils.e(response.message ?: "Falha ao criar sala hibrida.")
                        return@launch
                    }

                    val roomId = response.gameId ?: response.roomId
                    if (roomId.isNullOrBlank()) {
                        LogUtils.e("Resposta invalida do servidor ao criar sala hibrida.")
                        return@launch
                    }

                    LogUtils.i("Sala hibrida criada: $roomId")
                    openHybridRoom(
                        roomId = roomId,
                        playerName = name,
                        isHost = true,
                        playerId = response.playerId.orEmpty()
                    )
                } catch (e: Exception) {
                    LogUtils.e("Nao foi possivel criar sala hibrida. Verifica o servidor.", e)
                }
            }
        }

        btnJoinRoom.setOnClickListener {
            val name = inputName.text.toString().ifBlank { randomName() }
            val roomId = inputRoomId.text.toString().trim().uppercase()

            if (roomId.isBlank()) {
                LogUtils.w("Tentativa de entrar em sala hibrida sem ID.")
                return@setOnClickListener
            }

            lifecycleScope.launch {
                try {
                    val status = GatewayClient.getStatus(roomId)
                    if (status == null) {
                        LogUtils.e("Sala hibrida nao encontrada: $roomId")
                        return@launch
                    }
                    LogUtils.i("Entraste na sala hibrida: $roomId")
                    openHybridRoom(roomId = roomId, playerName = name, isHost = false)
                } catch (e: Exception) {
                    LogUtils.e("Erro ao procurar sala hibrida: $roomId", e)
                }
            }
        }
    }

    private fun openHybridRoom(
        roomId: String,
        playerName: String,
        isHost: Boolean,
        playerId: String = ""
    ) {
        val intent = Intent(this, RoomHybridActivity::class.java)
        intent.putExtra("roomId", roomId)
        intent.putExtra("playerName", playerName)
        intent.putExtra("isHost", isHost)
        intent.putExtra("playerId", playerId)
        startActivity(intent)
    }

    private fun randomName(): String {
        return "Player${(1000..9999).random()}"
    }

}
