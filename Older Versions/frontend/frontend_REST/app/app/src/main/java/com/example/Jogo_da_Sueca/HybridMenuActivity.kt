package com.example.Jogo_da_Sueca

import android.content.Intent
import android.os.Bundle
import android.text.InputFilter
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.Jogo_da_Sueca.network.RetrofitClient
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
                    val response = RetrofitClient.api.createRoomV2()
                    if (!response.success) {
                        Toast.makeText(
                            this@HybridMenuActivity,
                            response.message ?: "Falha ao criar sala hibrida.",
                            Toast.LENGTH_SHORT
                        ).show()
                        return@launch
                    }

                    val roomId = response.gameId ?: response.roomId
                    if (roomId.isNullOrBlank()) {
                        Toast.makeText(this@HybridMenuActivity, "Resposta invalida do servidor.", Toast.LENGTH_SHORT).show()
                        return@launch
                    }

                    Toast.makeText(this@HybridMenuActivity, "Sala hibrida criada: $roomId", Toast.LENGTH_SHORT).show()
                    openHybridRoom(roomId = roomId, playerName = name, isHost = true)
                } catch (e: Exception) {
                    Toast.makeText(
                        this@HybridMenuActivity,
                        "Nao foi possivel criar sala. Verifica o servidor.",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }

        btnJoinRoom.setOnClickListener {
            val name = inputName.text.toString().ifBlank { randomName() }
            val roomId = inputRoomId.text.toString().trim().uppercase()

            if (roomId.isBlank()) {
                Toast.makeText(this, "Insere o ID da sala.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch {
                try {
                    RetrofitClient.api.getStatus(roomId)
                    Toast.makeText(this@HybridMenuActivity, "Entraste na sala: $roomId", Toast.LENGTH_SHORT).show()
                    openHybridRoom(roomId = roomId, playerName = name, isHost = false)
                } catch (e: Exception) {
                    Toast.makeText(this@HybridMenuActivity, "Sala nao encontrada.", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun openHybridRoom(roomId: String, playerName: String, isHost: Boolean) {
        val intent = Intent(this, RoomHybridActivity::class.java)
        intent.putExtra("roomId", roomId)
        intent.putExtra("playerName", playerName)
        intent.putExtra("isHost", isHost)
        startActivity(intent)
    }

    private fun randomName(): String {
        return "Player${(1000..9999).random()}"
    }

}
