package com.example.MVP

import android.content.Intent
import android.text.InputFilter
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.launch

class OnlineMenuActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_online_menu_mvp)

        val inputName = findViewById<EditText>(R.id.inputName)
        val inputRoomId = findViewById<EditText>(R.id.inputRoomId)
        val btnCreateRoom = findViewById<Button>(R.id.btnCreateRoom)
        val btnJoinRoom = findViewById<Button>(R.id.btnJoinRoom)

        // Block spaces/newlines in both inputs.
        val noWhitespaceFilter = InputFilter { source, start, end, _, _, _ ->
            val filtered = StringBuilder()
            for (i in start until end) {
                val c = source[i]
                if (!c.isWhitespace()) {
                    filtered.append(c)
                }
            }
            if (filtered.length == end - start) {
                null
            } else {
                filtered.toString()
            }
        }

        inputName.filters = arrayOf(noWhitespaceFilter)
        inputRoomId.filters = arrayOf(noWhitespaceFilter, InputFilter.AllCaps())

        AuthManager.getPlayerDisplayName()?.let { inputName.setText(it) }

        btnCreateRoom.setOnClickListener {
            val name = inputName.text.toString().ifBlank { randomName() }

            lifecycleScope.launch {
                try {
                    val response = RetrofitClient.api.createRoomV2()
                    if (response.success) {
                        val roomId = response.gameId ?: response.roomId
                        if (roomId.isNullOrBlank()) {
                            Toast.makeText(this@OnlineMenuActivity, "Resposta invalida ao criar sala.", Toast.LENGTH_SHORT).show()
                        } else {
                            goToRoom(roomId = roomId, playerName = name, playerId = "")
                        }
                    } else {
                        Toast.makeText(this@OnlineMenuActivity, "Erro ao criar sala: ${response.message}", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                    Toast.makeText(this@OnlineMenuActivity, "Connection error. Check if server is running.", Toast.LENGTH_LONG).show()
                }
            }
        }

        btnJoinRoom.setOnClickListener {
            val name = inputName.text.toString().ifBlank { randomName() }
            val roomId = inputRoomId.text.toString().trim()

            if (roomId.isBlank()) {
                Toast.makeText(this@OnlineMenuActivity, "Insere o ID da sala.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch {
                try {
                    // Validate room existence before entering lobby.
                    RetrofitClient.api.getStatus(roomId)
                    goToRoom(roomId = roomId, playerName = name, playerId = "")
                } catch (e: Exception) {
                    e.printStackTrace()
                    Toast.makeText(this@OnlineMenuActivity, "Sala nao encontrada ou servidor offline.", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun goToRoom(roomId: String, playerName: String, playerId: String) {
        val intent = Intent(this, RoomActivity::class.java)
        intent.putExtra("roomId", roomId)
        intent.putExtra("playerName", playerName)
        intent.putExtra("playerId", playerId)
        startActivity(intent)
    }

    private fun randomName(): String {
        return "Player${(1000..9999).random()}"
    }
}
