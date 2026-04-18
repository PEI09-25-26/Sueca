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
import kotlinx.coroutines.launch

class HybridMenuActivity : AppCompatActivity() {

    companion object {
        private const val BADGE_REFRESH_INTERVAL_MS = 10_000L
        private const val PROFILE_REFRESH_INTERVAL_MS = 10_000L
        private val guestNameRegex = Regex("^Guest\\s+\\d+$")
        private val mockRoomRegistry = linkedSetOf<String>()
        private val mockRoomPlayers = linkedMapOf<String, MutableSet<String>>()

        fun registerMockRoomPlayer(roomId: String, playerName: String) {
            val normalizedRoomId = roomId.trim().uppercase()
            val normalizedPlayerName = playerName.trim()
            if (normalizedRoomId.isBlank() || normalizedPlayerName.isBlank()) {
                return
            }

            mockRoomRegistry.add(normalizedRoomId)
            mockRoomPlayers.getOrPut(normalizedRoomId) { linkedSetOf() }.add(normalizedPlayerName)
        }

        fun unregisterMockRoomPlayer(roomId: String, playerName: String) {
            val normalizedRoomId = roomId.trim().uppercase()
            val normalizedPlayerName = playerName.trim()
            if (normalizedRoomId.isBlank() || normalizedPlayerName.isBlank()) {
                return
            }

            val players = mockRoomPlayers[normalizedRoomId] ?: return
            players.remove(normalizedPlayerName)

            if (players.isEmpty()) {
                mockRoomPlayers.remove(normalizedRoomId)
            }
        }

        fun getRegisteredMockRoomPlayers(roomId: String): List<String> {
            val normalizedRoomId = roomId.trim().uppercase()
            return mockRoomPlayers[normalizedRoomId]?.toList().orEmpty()
        }
    }

    private lateinit var friendRequestsBadge: TextView
    private lateinit var profileIcon: ImageView
    private lateinit var inputRoomId: EditText
    private lateinit var roomsListContainer: LinearLayout
    private lateinit var txtHybridRoomsEmpty: TextView
    private var displayedPlayerName: String = ""
    private var lastBadgeRefreshAt: Long = 0L
    private var lastProfileRefreshAt: Long = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_hybrid_menu)

        val backButton = findViewById<ImageView>(R.id.backButton)
        val txtDisplayedName = findViewById<TextView>(R.id.txtDisplayedName)
        inputRoomId = findViewById(R.id.inputRoomId)
        val btnCreateRoom = findViewById<Button>(R.id.btnCreateRoom)
        val btnJoinRoom = findViewById<Button>(R.id.btnJoinRoom)
        val friendsIcon = findViewById<ImageView>(R.id.image_friends)
        friendRequestsBadge = findViewById(R.id.friend_requests_badge)
        profileIcon = findViewById(R.id.image_profile2)
        roomsListContainer = findViewById(R.id.hybridRoomsListContainer)
        txtHybridRoomsEmpty = findViewById(R.id.txtHybridRoomsEmpty)

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

        inputRoomId.filters = arrayOf(noWhitespaceFilter, InputFilter.AllCaps())

        displayedPlayerName = resolveDisplayedPlayerName()
        txtDisplayedName.text = "Nome exibido: $displayedPlayerName"

        friendsIcon.setOnClickListener {
            if (!AuthManager.isLoggedIn()) {
                showCreateAccountPrompt("Para usar Amigos precisas de criar/iniciar conta.")
                return@setOnClickListener
            }
            startActivity(Intent(this, FriendsActivity::class.java))
        }

        profileIcon.setOnClickListener {
            if (!AuthManager.isLoggedIn()) {
                showCreateAccountPrompt("Para aceder ao Perfil precisas de criar/iniciar conta.")
                return@setOnClickListener
            }
            startActivity(Intent(this, ProfileActivity::class.java))
        }

        btnCreateRoom.setOnClickListener {
            val name = displayedPlayerName
            val roomId = generateMockRoomId()
            mockRoomRegistry.add(roomId)
            renderMockRooms(inputRoomId)
            Toast.makeText(this, "Sala hibrida criada: $roomId", Toast.LENGTH_SHORT).show()
            openHybridRoom(roomId = roomId, playerName = name, isHost = true)
        }

        btnJoinRoom.setOnClickListener {
            val name = displayedPlayerName
            val roomId = inputRoomId.text.toString().trim().uppercase()

            if (roomId.isBlank()) {
                Toast.makeText(this, "Insere o ID da sala.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (!mockRoomRegistry.contains(roomId)) {
                Toast.makeText(this, "Sala mock nao encontrada.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            renderMockRooms(inputRoomId)
            Toast.makeText(this, "Entraste na sala mock: $roomId", Toast.LENGTH_SHORT).show()
            openHybridRoom(roomId = roomId, playerName = name, isHost = false)
        }

        renderMockRooms(inputRoomId)
    }

    override fun onResume() {
        super.onResume()
        renderMockRooms(inputRoomId)
        maybeRefreshFriendRequestsBadge()
        maybeRefreshProfileIcon()
    }

    private fun renderMockRooms(inputRoomId: EditText) {
        roomsListContainer.removeAllViews()

        if (mockRoomRegistry.isEmpty()) {
            txtHybridRoomsEmpty.visibility = View.VISIBLE
            return
        }

        txtHybridRoomsEmpty.visibility = View.GONE

        mockRoomRegistry.forEach { roomId ->
            val players = getRegisteredMockRoomPlayers(roomId)

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
                    inputRoomId.setText(roomId)
                    inputRoomId.setSelection(roomId.length)
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
                text = "Mesa Nº $roomId"
                setTextColor(Color.WHITE)
                setTypeface(typeface, Typeface.BOLD)
                textSize = 17f
            }

            val roomCount = TextView(this).apply {
                text = "${players.size}/4"
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

    private fun openHybridRoom(roomId: String, playerName: String, isHost: Boolean) {
        val intent = Intent(this, RoomHybridActivity::class.java)
        intent.putExtra("roomId", roomId)
        intent.putExtra("playerName", playerName)
        intent.putExtra("isHost", isHost)
        startActivity(intent)
    }

    private fun resolveDisplayedPlayerName(): String {
        if (AuthManager.isLoggedIn()) {
            return AuthManager.getUsername()?.takeIf { it.isNotBlank() } ?: "Conta"
        }

        val anonymousName = AuthManager.getAnonymousName()?.trim()
        val guestName = if (!anonymousName.isNullOrBlank() && guestNameRegex.matches(anonymousName)) {
            anonymousName
        } else {
            randomGuestName()
        }

        AuthManager.startAnonymousSession(guestName)
        return guestName
    }

    private fun randomGuestName(): String {
        return "Guest ${(1000..9999).random()}"
    }

    private fun generateMockRoomId(): String {
        val pool = ('A'..'Z') + ('0'..'9')
        return "HB" + (1..4).map { pool.random() }.joinToString("")
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }
}
