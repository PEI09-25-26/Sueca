package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.text.InputFilter
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.launch

class OnlineMenuActivity : AppCompatActivity() {

    private data class RoomPreviewConfig(
        val roomId: String,
        val itemViewId: Int,
        val countViewId: Int,
        val playersViewId: Int
    )

    private lateinit var txtDisplayedName: TextView
    private lateinit var friendRequestsBadge: TextView
    private lateinit var profileIcon: ImageView
    private var fallbackDisplayName: String? = null
    private var lastBadgeRefreshAt: Long = 0L
    private var lastProfileRefreshAt: Long = 0L

    companion object {
        private const val BADGE_REFRESH_INTERVAL_MS = 10_000L
        private const val PROFILE_REFRESH_INTERVAL_MS = 10_000L
    }

    private val roomPreviews = listOf(
        RoomPreviewConfig("129837", R.id.roomItem129837, R.id.txtRoomCount129837, R.id.txtRoomPlayers129837),
        RoomPreviewConfig("138373", R.id.roomItem138373, R.id.txtRoomCount138373, R.id.txtRoomPlayers138373),
        RoomPreviewConfig("671319", R.id.roomItem671319, R.id.txtRoomCount671319, R.id.txtRoomPlayers671319),
        RoomPreviewConfig("180080", R.id.roomItem180080, R.id.txtRoomCount180080, R.id.txtRoomPlayers180080),
        RoomPreviewConfig("142069", R.id.roomItem142069, R.id.txtRoomCount142069, R.id.txtRoomPlayers142069)
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_online_menu_mvp)

        val backButton = findViewById<ImageView>(R.id.backButton)
        val inputRoomId = findViewById<EditText>(R.id.inputRoomId)
        val btnCreateRoom = findViewById<Button>(R.id.btnCreateRoom)
        val btnJoinRoom = findViewById<Button>(R.id.btnJoinRoom)
        val friendsIcon = findViewById<ImageView>(R.id.image_friends)
        txtDisplayedName = findViewById(R.id.txtDisplayedName)
        profileIcon = findViewById(R.id.image_profile2)
        friendRequestsBadge = findViewById(R.id.friend_requests_badge)
        txtDisplayedName.text = "Nome exibido: ${resolveDisplayedName()}"

        backButton.setOnClickListener { finish() }

        // Block spaces/newlines in room input.
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

        inputRoomId.filters = arrayOf(noWhitespaceFilter, InputFilter.AllCaps())

        setupRoomQuickPick(inputRoomId)
        refreshRoomPreviews()

        btnCreateRoom.setOnClickListener {
            val name = resolveDisplayedName()

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
            val roomId = inputRoomId.text.toString().trim().uppercase()

            if (roomId.isBlank()) {
                Toast.makeText(this@OnlineMenuActivity, "Insere o ID da sala.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            joinRoomById(roomId)
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
        txtDisplayedName.text = "Nome exibido: ${resolveDisplayedName()}"
        refreshRoomPreviews()
        maybeRefreshFriendRequestsBadge()
        maybeRefreshProfileIcon()
    }

    private fun setupRoomQuickPick(inputRoomId: EditText) {
        roomPreviews.forEach { preview ->
            findViewById<View>(preview.itemViewId).setOnClickListener {
                inputRoomId.setText(preview.roomId)
                inputRoomId.setSelection(preview.roomId.length)
                joinRoomById(preview.roomId)
            }
        }
    }

    private fun refreshRoomPreviews() {
        lifecycleScope.launch {
            roomPreviews.forEach { preview ->
                val countView = findViewById<TextView>(preview.countViewId)
                val playersView = findViewById<TextView>(preview.playersViewId)

                try {
                    val state = RetrofitClient.api.getStatus(preview.roomId)
                    val players = state.players
                        .map { it.name }
                        .filter { it.isNotBlank() }

                    countView.text = "${players.size}/4"
                    playersView.text = if (players.isEmpty()) {
                        "Sem jogadores na sala"
                    } else {
                        players.joinToString(", ")
                    }
                } catch (e: Exception) {
                    countView.text = "--/4"
                    playersView.text = "Sem dados de jogadores"
                }
            }
        }
    }

    private fun joinRoomById(roomId: String) {
        val normalizedRoomId = roomId.trim().uppercase()
        val playerName = resolveDisplayedName()

        lifecycleScope.launch {
            try {
                // Validate room existence before entering lobby.
                RetrofitClient.api.getStatus(normalizedRoomId)
                goToRoom(roomId = normalizedRoomId, playerName = playerName, playerId = "")
            } catch (e: Exception) {
                e.printStackTrace()
                Toast.makeText(this@OnlineMenuActivity, "Sala nao encontrada ou servidor offline.", Toast.LENGTH_LONG).show()
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

    private fun resolveDisplayedName(): String {
        val authName = AuthManager.getPlayerDisplayName()?.takeIf { it.isNotBlank() }
        if (!authName.isNullOrBlank()) {
            return authName
        }

        val existingFallback = fallbackDisplayName
        if (!existingFallback.isNullOrBlank()) {
            return existingFallback
        }

        val newFallback = randomName()
        fallbackDisplayName = newFallback
        return newFallback
    }
}
