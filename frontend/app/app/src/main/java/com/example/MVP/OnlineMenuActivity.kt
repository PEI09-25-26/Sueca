package com.example.MVP

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.InputFilter
import android.text.TextUtils
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.RoomSummary
import com.example.MVP.network.RetrofitClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class OnlineMenuActivity : AppCompatActivity() {

    private lateinit var txtDisplayedName: TextView
    private lateinit var friendRequestsBadge: TextView
    private lateinit var profileIcon: ImageView
    private lateinit var inputRoomId: EditText
    private lateinit var roomsListContainer: LinearLayout
    private lateinit var txtOnlineRoomsEmpty: TextView
    private var fallbackDisplayName: String? = null
    private var roomsPollingJob: Job? = null
    private var lastBadgeRefreshAt: Long = 0L
    private var lastProfileRefreshAt: Long = 0L

    companion object {
        private const val BADGE_REFRESH_INTERVAL_MS = 10_000L
        private const val PROFILE_REFRESH_INTERVAL_MS = 10_000L
        private const val ROOM_LIST_REFRESH_INTERVAL_MS = 2_000L
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_online_menu_mvp)

        val backButton = findViewById<ImageView>(R.id.backButton)
        inputRoomId = findViewById(R.id.inputRoomId)
        val btnCreateRoom = findViewById<Button>(R.id.btnCreateRoom)
        val btnJoinRoom = findViewById<Button>(R.id.btnJoinRoom)
        val friendsIcon = findViewById<ImageView>(R.id.image_friends)
        txtDisplayedName = findViewById(R.id.txtDisplayedName)
        profileIcon = findViewById(R.id.image_profile2)
        friendRequestsBadge = findViewById(R.id.friend_requests_badge)
        roomsListContainer = findViewById(R.id.onlineRoomsListContainer)
        txtOnlineRoomsEmpty = findViewById(R.id.txtOnlineRoomsEmpty)
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
                            refreshRoomsOnce()
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
        startRoomsPolling()
        maybeRefreshFriendRequestsBadge()
        maybeRefreshProfileIcon()
    }

    override fun onPause() {
        roomsPollingJob?.cancel()
        super.onPause()
    }

    private fun startRoomsPolling() {
        roomsPollingJob?.cancel()
        roomsPollingJob = lifecycleScope.launch {
            while (true) {
                refreshRoomsOnce()
                delay(ROOM_LIST_REFRESH_INTERVAL_MS)
            }
        }
    }

    private suspend fun refreshRoomsOnce() {
        try {
            val response = RetrofitClient.api.getRooms()
            if (!response.success) {
                if (roomsListContainer.childCount == 0) {
                    txtOnlineRoomsEmpty.visibility = View.VISIBLE
                    txtOnlineRoomsEmpty.text = response.message ?: "Nao foi possivel obter salas."
                }
                return
            }

            renderOnlineRooms(response.rooms.orEmpty())
        } catch (_: Exception) {
            if (roomsListContainer.childCount == 0) {
                txtOnlineRoomsEmpty.visibility = View.VISIBLE
                txtOnlineRoomsEmpty.text = "Nao foi possivel atualizar salas."
            }
        }
    }

    private fun renderOnlineRooms(rooms: List<RoomSummary>) {
        roomsListContainer.removeAllViews()

        val normalizedRooms = rooms
            .mapNotNull { room ->
                val normalizedId = room.gameId.trim().uppercase()
                if (normalizedId.isBlank()) {
                    null
                } else {
                    room.copy(gameId = normalizedId)
                }
            }
            .distinctBy { it.gameId }
            .sortedBy { it.gameId }

        val publicRooms = normalizedRooms.filter { room ->
            val players = room.players.filter { it.isNotBlank() }
            val count = room.playerCount.coerceAtLeast(players.size)
            val maxPlayers = room.maxPlayers.coerceAtLeast(1)
            count in 1 until maxPlayers
        }

        if (publicRooms.isEmpty()) {
            txtOnlineRoomsEmpty.visibility = View.VISIBLE
            txtOnlineRoomsEmpty.text = "Sem salas publicas disponiveis."
            return
        }

        txtOnlineRoomsEmpty.visibility = View.GONE

        publicRooms.forEach { room ->
            val players = room.players.filter { it.isNotBlank() }
            val count = room.playerCount.coerceAtLeast(players.size)
            val maxPlayers = room.maxPlayers.coerceAtLeast(1)

            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setBackgroundResource(R.drawable.room_item_bg)
                setPadding(dp(12), dp(10), dp(12), dp(10))
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    bottomMargin = dp(10)
                }
                isClickable = true
                isFocusable = true
                setOnClickListener {
                    inputRoomId.setText(room.gameId)
                    inputRoomId.setSelection(room.gameId.length)
                    joinRoomById(room.gameId)
                }
            }

            val topRow = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                )
            }

            val roomTitle = TextView(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    0,
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    1f
                )
                text = "Mesa Nº ${room.gameId}"
                setTextColor(Color.WHITE)
                setTypeface(typeface, Typeface.BOLD)
                textSize = 17f
            }

            val roomCount = TextView(this).apply {
                text = "$count/$maxPlayers"
                setTextColor(Color.parseColor("#CCE7F4FF"))
                textSize = 13f
            }

            val playersText = TextView(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    topMargin = dp(4)
                }
                text = if (players.isEmpty()) "Sem jogadores na sala" else players.joinToString(", ")
                setTextColor(Color.parseColor("#D5E2EC"))
                textSize = 12f
                maxLines = 2
                ellipsize = TextUtils.TruncateAt.END
            }

            topRow.addView(roomTitle)
            topRow.addView(roomCount)
            card.addView(topRow)
            card.addView(playersText)
            roomsListContainer.addView(card)
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

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }
}
