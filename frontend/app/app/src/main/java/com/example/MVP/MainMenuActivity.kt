package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.StartGameRequest
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.launch

class MainMenuActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main_menu_mvp)

        val btnJoin = findViewById<Button>(R.id.btnJoin)
        val btnVision = findViewById<Button>(R.id.btnVision)

        btnJoin.setOnClickListener {
            showModeDialog()
        }

        btnVision.setOnClickListener {
            val name = randomName()
            val roomId: String? = null

            lifecycleScope.launch {
                try {
                    // Calling the middleware
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

    private fun showModeDialog() {
        // Use explicit dialog buttons so mode choices are always visible.
        AlertDialog.Builder(this)
            .setTitle("Escolher modo")
            .setItems(arrayOf("Local", "Online")) { _, which ->
                when (which) {
                    0 -> joinLocalGame()
                    1 -> openOnlineMenu()
                }
            }
            .show()
    }

    private fun joinLocalGame() {
        // Local mode should not depend on backend endpoints.
        val intent = Intent(this, RoomActivity::class.java)
        intent.putExtra("roomId", "SALA_LOCAL")
        intent.putExtra("playerId", "ID_LOCAL")
        startActivity(intent)
    }

    private fun openOnlineMenu() {
        val intent = Intent(this, OnlineMenuActivity::class.java)
        startActivity(intent)
    }

    private fun randomName(): String {
        return "Player${(1000..9999).random()}"
    }
}