package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.StartGameRequest
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.launch

class MainMenuActivity : AppCompatActivity() {

    private lateinit var friendRequestsBadge: TextView
    private lateinit var profileIcon: ImageView
    private var lastBadgeRefreshAt: Long = 0L
    private var lastProfileRefreshAt: Long = 0L

    companion object {
        private const val BADGE_REFRESH_INTERVAL_MS = 10_000L
        private const val PROFILE_REFRESH_INTERVAL_MS = 10_000L
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_main_menu_mvp)

        val btnJoin = findViewById<Button>(R.id.btnJoin)
        val btnVision = findViewById<Button>(R.id.btnVision)
        val btnHybrid = findViewById<Button>(R.id.btnHybrid)
        val friendsIcon = findViewById<ImageView>(R.id.image_friends)
        profileIcon = findViewById(R.id.image_profile2)
        friendRequestsBadge = findViewById(R.id.friend_requests_badge)

        btnJoin.setOnClickListener {
            showModeDialog()
        }

        btnVision.setOnClickListener {
            val name = AuthManager.getPlayerDisplayName() ?: randomName()
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

        btnHybrid.setOnClickListener {
            val intent = Intent(this, HybridMenuActivity::class.java)
            startActivity(intent)
        }

        friendsIcon.setOnClickListener {
            if (!AuthManager.isLoggedIn()) {
                showCreateAccountPrompt("Para usar Amigos precisas de criar/iniciar conta.")
                return@setOnClickListener
            }
            val intent = Intent(this, FriendsActivity::class.java)
            startActivity(intent)
        }

        profileIcon.setOnClickListener {
            if (!AuthManager.isLoggedIn()) {
                showCreateAccountPrompt("Para aceder ao Perfil precisas de criar/iniciar conta.")
                return@setOnClickListener
            }
            val intent = Intent(this, ProfileActivity::class.java)
            startActivity(intent)
        }

    }

    override fun onResume() {
        super.onResume()
        maybeRefreshFriendRequestsBadge()
        maybeRefreshProfileIcon()
    }

    private fun maybeRefreshProfileIcon() {
        val now = System.currentTimeMillis()
        if ((now - lastProfileRefreshAt) < PROFILE_REFRESH_INTERVAL_MS) {
            return
        }
        lastProfileRefreshAt = now
        refreshProfileIcon()
    }

    private fun maybeRefreshFriendRequestsBadge() {
        val now = System.currentTimeMillis()
        if ((now - lastBadgeRefreshAt) < BADGE_REFRESH_INTERVAL_MS) {
            return
        }
        lastBadgeRefreshAt = now
        refreshFriendRequestsBadge()
    }

    private fun refreshProfileIcon() {
        if (!AuthManager.isLoggedIn()) {
            profileIcon.setImageResource(R.drawable.profile_pic1)
            return
        }

        val uid = AuthManager.getUid() ?: run {
            profileIcon.setImageResource(R.drawable.profile_pic1)
            return
        }

        lifecycleScope.launch {
            AuthManager.getUser(uid)
                .onSuccess { user ->
                    applyProfileIcon(user.photoURL)
                }
                .onFailure {
                    profileIcon.setImageResource(R.drawable.profile_pic1)
                }
        }
    }

    private fun applyProfileIcon(photoKey: String?) {
        when (photoKey) {
            "profile_pic1" -> profileIcon.setImageResource(R.drawable.profile_pic1)
            "profile_pic2" -> profileIcon.setImageResource(R.drawable.profile_pic2)
            "profile_pic3" -> profileIcon.setImageResource(R.drawable.profile_pic3)
            "profile_pic4" -> profileIcon.setImageResource(R.drawable.profile_pic4)
            "profile_pic5" -> profileIcon.setImageResource(R.drawable.profile_pic5)
            else -> profileIcon.setImageResource(R.drawable.profile_pic1)
        }
    }

    private fun refreshFriendRequestsBadge() {
        if (!AuthManager.isLoggedIn()) {
            friendRequestsBadge.visibility = View.GONE
            return
        }

        val uid = AuthManager.getUid() ?: run {
            friendRequestsBadge.visibility = View.GONE
            return
        }

        lifecycleScope.launch {
            FriendsManager.listIncomingFriendRequests(uid)
                .onSuccess { requests ->
                    val count = requests.size
                    if (count > 0) {
                        friendRequestsBadge.visibility = View.VISIBLE
                        friendRequestsBadge.text = if (count > 99) "99+" else count.toString()
                    } else {
                        friendRequestsBadge.visibility = View.GONE
                    }
                }
                .onFailure {
                    friendRequestsBadge.visibility = View.GONE
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

    private fun showCreateAccountPrompt(message: String) {
        AlertDialog.Builder(this)
            .setTitle("Criar conta")
            .setMessage(message)
            .setPositiveButton("Registar") { _, _ ->
                startActivity(Intent(this, RegisterActivity::class.java))
            }
            .setNegativeButton("Login") { _, _ ->
                startActivity(Intent(this, LoginActivity::class.java))
                finish()
            }
            .setNeutralButton("Cancelar", null)
            .show()
    }
}