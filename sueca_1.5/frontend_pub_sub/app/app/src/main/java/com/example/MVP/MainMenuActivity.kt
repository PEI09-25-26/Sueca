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
import com.example.MVP.models.*
import com.example.MVP.network.RetrofitClient
import com.example.MVP.network.GatewayClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainMenuActivity : AppCompatActivity() {

    private lateinit var friendRequestsBadge: TextView
    private lateinit var profileIcon: ImageView
    private lateinit var btnPlay: Button
    private lateinit var playOptionsContainer: View
    private var lastBadgeRefreshAt: Long = 0L
    private var lastProfileRefreshAt: Long = 0L
    private var invitePollingJob: Job? = null
    private var fallbackDisplayName: String? = null

    companion object {
        private const val BADGE_REFRESH_INTERVAL_MS = 10_000L
        private const val PROFILE_REFRESH_INTERVAL_MS = 10_000L
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_main_menu_mvp)

        btnPlay = findViewById(R.id.btnPlay)
        playOptionsContainer = findViewById(R.id.playOptionsContainer)

        val btnVirtual = findViewById<Button>(R.id.btnVirtual)
        val btnPresential = findViewById<Button>(R.id.btnPresential)
        val btnHybrid = findViewById<Button>(R.id.btnHybrid)
        val friendsIcon = findViewById<ImageView>(R.id.image_friends)
        profileIcon = findViewById(R.id.image_profile2)
        friendRequestsBadge = findViewById(R.id.friend_requests_badge)

        btnPlay.setOnClickListener {
            togglePlayOptions(show = true)
        }

        btnVirtual.setOnClickListener {
            openOnlineMenu()
        }

        btnPresential.setOnClickListener {
            launchPresentialVisionGame()
        }

        btnHybrid.setOnClickListener {
            openHybridMenu()
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

    override fun onBackPressed() {
        if (playOptionsContainer.visibility == View.VISIBLE) {
            togglePlayOptions(show = false)
            return
        }
        super.onBackPressed()
    }

    override fun onResume() {
        super.onResume()
        maybeRefreshFriendRequestsBadge()
        maybeRefreshProfileIcon()
        startInvitePolling()
    }

    override fun onPause() {
        super.onPause()
        stopInvitePolling()
    }

    private fun startInvitePolling() {
        if (!AuthManager.isLoggedIn()) return
        if (invitePollingJob != null) return

        invitePollingJob = lifecycleScope.launch {
            while (true) {
                try {
                    val token = AuthManager.getToken()
                    if (token != null) {
                        val authHeader = "Bearer $token"
                        val response = RetrofitClient.api.getInvites(authHeader)
                        if (response.success && response.invites.isNotEmpty()) {
                            for (invite in response.invites) {
                                showInviteNotification(invite)
                            }
                        }
                    }
                } catch (e: Exception) {
                    // Fail silently for background polling
                }
                delay(3000) // Poll every 3 seconds
            }
        }
    }

    private fun stopInvitePolling() {
        invitePollingJob?.cancel()
        invitePollingJob = null
    }

    private fun showInviteNotification(invite: GameInvite) {
        AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle("Convite de Jogo")
            .setMessage("${invite.inviterName} convidou-te para um jogo na posição ${invite.position}!")
            .setPositiveButton("Aceitar") { _, _ ->
                acceptInvite(invite)
            }
            .setNegativeButton("Recusar") { _, _ ->
                declineInvite(invite)
            }
            .show()
    }

    private fun acceptInvite(invite: GameInvite) {
        val name = AuthManager.getUsername() ?: randomName()
        lifecycleScope.launch {
            try {
                val authHeader = AuthManager.getAuthHeader()
                val response = GatewayClient.joinGame(
                    JoinGameRequest(
                        name = name,
                        gameId = invite.gameId,
                        position = com.example.MVP.models.Position.valueOf(invite.position.uppercase())
                    ),
                    authHeader = authHeader
                )

                if (response.success) {
                    val intent = Intent(this@MainMenuActivity, RoomActivity::class.java)
                    intent.putExtra("roomId", invite.gameId)
                    intent.putExtra("playerId", response.playerId)
                    intent.putExtra("playerName", name)
                    startActivity(intent)
                } else {
                    Toast.makeText(this@MainMenuActivity, "Erro ao aceitar convite: ${response.message}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@MainMenuActivity, "Erro de rede ao aceitar convite.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun declineInvite(invite: GameInvite) {
        lifecycleScope.launch {
            try {
                GatewayClient.declineInvite(invite.gameId, invite.position)
            } catch (_: Exception) {
            }
        }
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

    private fun togglePlayOptions(show: Boolean) {
        btnPlay.visibility = if (show) View.GONE else View.VISIBLE
        playOptionsContainer.visibility = if (show) View.VISIBLE else View.GONE
    }

    private fun launchPresentialVisionGame() {
        val name = AuthManager.getPlayerDisplayName() ?: randomName()
        val roomId: String? = null
        val authHeader = AuthManager.getAuthHeader()

        lifecycleScope.launch {
            try {
                // In physical mode, North (1) is usually the first dealer by default
                val response = RetrofitClient.api.startPhysicalGame(
                    StartGameRequest(playerName = name, roomId = roomId, dealerId = 1),
                    authHeader
                )

                if (response.success) {
                    val actualGameId = response.gameId ?: "default"
                    if (!response.token.isNullOrBlank()) {
                        GameSessionManager.saveToken(actualGameId, response.token)
                    }

                    Toast.makeText(
                        this@MainMenuActivity,
                        "Vision AI Started!",
                        Toast.LENGTH_SHORT
                    ).show()

                    val intent = Intent(this@MainMenuActivity, VisionActivity::class.java)
                    intent.putExtra("playerName", name)
                    intent.putExtra("roomId", actualGameId)
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

    private fun openHybridMenu() {
        val intent = Intent(this, HybridMenuActivity::class.java)
        startActivity(intent)
    }

    private fun openOnlineMenu() {
        val intent = Intent(this, OnlineMenuActivity::class.java)
        startActivity(intent)
    }

    private fun randomName(): String {
        return "Player${(1000..9999).random()}"
    }

    private fun resolveDisplayedName(): String {
        val authName = AuthManager.getPlayerDisplayName()
        if (!authName.isNullOrBlank()) {
            return authName
        }

        val existingFallback = fallbackDisplayName
        if (!existingFallback.isNullOrBlank()) {
            return existingFallback!!
        }

        val newFallback = randomName()
        fallbackDisplayName = newFallback
        return newFallback
    }

    private fun showCreateAccountPrompt(message: String) {
        AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
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
