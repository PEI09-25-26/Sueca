package com.example.Jogo_da_Sueca

import android.content.Intent
import android.os.Bundle
import android.text.InputFilter
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class HybridMenuActivity : AppCompatActivity() {

    companion object {
        private val mockRoomRegistry = mutableSetOf<String>()
    }

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
            val roomId = generateMockRoomId()
            mockRoomRegistry.add(roomId)
            Toast.makeText(this, "Sala hibrida criada: $roomId", Toast.LENGTH_SHORT).show()
            openHybridRoom(roomId = roomId, playerName = name, isHost = true)
        }

        btnJoinRoom.setOnClickListener {
            val name = inputName.text.toString().ifBlank { randomName() }
            val roomId = inputRoomId.text.toString().trim().uppercase()

            if (roomId.isBlank()) {
                Toast.makeText(this, "Insere o ID da sala.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (!mockRoomRegistry.contains(roomId)) {
                Toast.makeText(this, "Sala mock nao encontrada.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            Toast.makeText(this, "Entraste na sala mock: $roomId", Toast.LENGTH_SHORT).show()
            openHybridRoom(roomId = roomId, playerName = name, isHost = false)
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

    private fun generateMockRoomId(): String {
        val pool = ('A'..'Z') + ('0'..'9')
        return "HB" + (1..4).map { pool.random() }.joinToString("")
    }
}
