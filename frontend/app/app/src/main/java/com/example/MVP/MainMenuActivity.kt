package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.CreateRoomRequest
import com.example.MVP.models.JoinRoomRequest
import com.example.MVP.models.StartGameRequest
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.launch

class MainMenuActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main_menu_mvp)

        val inputName = findViewById<EditText>(R.id.inputName)
        val inputRoom = findViewById<EditText>(R.id.inputRoom)
        val btnJoin = findViewById<Button>(R.id.btnJoin)
        val btnVision = findViewById<Button>(R.id.btnVision)

        // Direct join to game server (like client.py)
        btnJoin.setOnClickListener {
            val name = inputName.text.toString().ifBlank { "Player${(1000..9999).random()}" }
            
            lifecycleScope.launch {
                try {
                    // Join game directly via middleware -> server
                    val response = RetrofitClient.api.joinGame(mapOf("name" to name))
                    
                    if (response.success) {
                        Toast.makeText(this@MainMenuActivity, response.message ?: "Joined!", Toast.LENGTH_SHORT).show()
                        goToGame(name)
                    } else {
                        Toast.makeText(this@MainMenuActivity, "Error: ${response.message}", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                    Toast.makeText(
                        this@MainMenuActivity,
                        "Connection error. Check if server is running.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }

        btnVision.setOnClickListener {
            val name = inputName.text.toString().ifBlank { "Player${(1000..9999).random()}" }
            val roomId = inputRoom.text.toString().ifBlank { null }

            lifecycleScope.launch {
                try {
                    // Call middleware to start the game with CV
                    val response = RetrofitClient.api.startGame(
                        StartGameRequest(playerName = name, roomId = roomId)
                    )

                    if (response.success) {
                        Toast.makeText(
                            this@MainMenuActivity,
                            "Vision AI Started!",
                            Toast.LENGTH_SHORT
                        ).show()

                        // Open VisionActivity
                        val intent = Intent(this@MainMenuActivity, VisionActivity::class.java)
                        intent.putExtra("playerName", name)
                        intent.putExtra("roomId", response.gameId)
                        startActivity(intent)
                    } else {
                        Toast.makeText(
                            this@MainMenuActivity,
                            "Failed to start: ${response.message}",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                } catch (e: retrofit2.HttpException) {
                    e.printStackTrace()
                    Toast.makeText(
                        this@MainMenuActivity,
                        "HTTP Error: ${e.code()} - ${e.message()}",
                        Toast.LENGTH_LONG
                    ).show()
                } catch (e: java.net.ConnectException) {
                    e.printStackTrace()
                    Toast.makeText(
                        this@MainMenuActivity,
                        "Cannot connect to server. Make sure middleware is running.",
                        Toast.LENGTH_LONG
                    ).show()
                } catch (e: Exception) {
                    e.printStackTrace()
                    Toast.makeText(
                        this@MainMenuActivity,
                        "Error: ${e.javaClass.simpleName} - ${e.message}",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }

    private fun goToGame(playerName: String) {
        val intent = Intent(this, GameActivity::class.java)
        intent.putExtra("playerName", playerName)
        startActivity(intent)
    }

    private fun goToRoom(roomId: String, playerId: String) {
        val intent = Intent(this, RoomActivity::class.java)
        intent.putExtra("roomId", roomId)
        intent.putExtra("playerId", playerId)
        startActivity(intent)
    }

    private fun handleNetworkError(message: String?) {
        Toast.makeText(this, "Server Offline. Entering Mock mode...", Toast.LENGTH_LONG).show()
        val intent = Intent(this, RoomActivity::class.java)
        intent.putExtra("roomId", "SALA_LOCAL")
        intent.putExtra("playerId", "ID_LOCAL")
        startActivity(intent)
    }
}