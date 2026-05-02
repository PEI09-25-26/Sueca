package com.example.MVP

import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.InputFilter
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
        private const val MOCK_HYBRID_BASE_OCCUPANCY = 3
        private const val MOCK_HYBRID_MAX_OCCUPANCY = 4
        private const val MOCK_HYBRID_REMOTE_SLOTS = 1
        private val guestNameRegex = Regex("^Guest\\s+\\d+$")

        private data class MockHybridRoomState(
            var isPublic: Boolean = true,
            var creatorName: String = ""
        )

        private val mockRoomRegistry = linkedSetOf<String>()
        private val mockRoomPlayers = linkedMapOf<String, MutableSet<String>>()
        private val mockRoomStates = linkedMapOf<String, MockHybridRoomState>()

        fun createMockRoom(roomId: String, creatorName: String) {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            if (normalizedRoomId.isBlank()) {
                return
            }

            val normalizedCreatorName = creatorName.trim().ifBlank { "Criador" }
            mockRoomRegistry.add(normalizedRoomId)
            mockRoomStates[normalizedRoomId] = MockHybridRoomState(
                isPublic = true,
                creatorName = normalizedCreatorName
            )
        }

        fun hasMockRoom(roomId: String): Boolean {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            return normalizedRoomId.isNotBlank() && mockRoomRegistry.contains(normalizedRoomId)
        }

        fun canMockRoomAcceptPlayer(roomId: String, playerName: String): Boolean {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            val normalizedPlayerName = playerName.trim()

            if (normalizedRoomId.isBlank() || normalizedPlayerName.isBlank()) {
                return false
            }

            if (!mockRoomRegistry.contains(normalizedRoomId)) {
                return false
            }

            val players = mockRoomPlayers[normalizedRoomId] ?: return true
            return players.contains(normalizedPlayerName) || players.size < MOCK_HYBRID_REMOTE_SLOTS
        }

        fun setMockRoomVisibility(roomId: String, isPublic: Boolean): Boolean {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            val roomState = mockRoomStates[normalizedRoomId] ?: return false
            roomState.isPublic = isPublic
            return true
        }

        fun isMockRoomPublic(roomId: String): Boolean {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            return mockRoomStates[normalizedRoomId]?.isPublic ?: true
        }

        fun getMockRoomCreatorName(roomId: String): String {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            val creatorName = mockRoomStates[normalizedRoomId]?.creatorName?.trim().orEmpty()
            return creatorName.ifBlank { "Criador" }
        }

        fun registerMockRoomPlayer(roomId: String, playerName: String) {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            val normalizedPlayerName = playerName.trim()
            if (normalizedRoomId.isBlank() || normalizedPlayerName.isBlank()) {
                return
            }

            mockRoomRegistry.add(normalizedRoomId)
            if (!mockRoomStates.containsKey(normalizedRoomId)) {
                mockRoomStates[normalizedRoomId] = MockHybridRoomState(isPublic = true)
            }

            val players = mockRoomPlayers.getOrPut(normalizedRoomId) { linkedSetOf() }
            if (players.contains(normalizedPlayerName) || players.size < MOCK_HYBRID_REMOTE_SLOTS) {
                players.add(normalizedPlayerName)
            }
        }

        fun unregisterMockRoomPlayer(roomId: String, playerName: String) {
            val normalizedRoomId = normalizeMockRoomId(roomId)
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
            val normalizedRoomId = normalizeMockRoomId(roomId)
            return mockRoomPlayers[normalizedRoomId]?.toList().orEmpty()
        }

        fun getMockRoomOccupancy(roomId: String): Int {
            val normalizedRoomId = normalizeMockRoomId(roomId)
            val remotePlayers = mockRoomPlayers[normalizedRoomId]
                ?.size
                ?.coerceAtMost(MOCK_HYBRID_REMOTE_SLOTS)
                ?: 0

            return (MOCK_HYBRID_BASE_OCCUPANCY + remotePlayers)
                .coerceAtMost(MOCK_HYBRID_MAX_OCCUPANCY)
        }

        fun getMockRoomDisplayPlayers(roomId: String): List<String> {
            val names = mutableListOf(
                "Jogador Mesa 1",
                "Jogador Mesa 2",
                "Jogador Mesa 3"
            )

            val remotePlayer = getRegisteredMockRoomPlayers(roomId).firstOrNull()
            names.add(remotePlayer ?: "Waiting for player...")
            return names
        }

        private fun normalizeMockRoomId(roomId: String): String {
            return roomId.trim().uppercase()
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
            createMockRoom(roomId, name)
            renderMockRooms(inputRoomId)
            Toast.makeText(this, "Sala hibrida criada: $roomId", Toast.LENGTH_SHORT).show()
            openHybridRoom(roomId = roomId, playerName = name, isHost = true)
        }

        btnJoinRoom.setOnClickListener {
            joinHybridRoomById(inputRoomId.text.toString())
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
        txtHybridRoomsEmpty.text = "Cria uma sala para aparecer aqui."

        if (mockRoomRegistry.isEmpty()) {
            txtHybridRoomsEmpty.visibility = View.VISIBLE
            return
        }

        val visibleRooms = mockRoomRegistry.filter { roomId ->
            val occupancy = getMockRoomOccupancy(roomId)
            isMockRoomPublic(roomId) && occupancy in 1 until MOCK_HYBRID_MAX_OCCUPANCY
        }

        if (visibleRooms.isEmpty()) {
            txtHybridRoomsEmpty.text = "Sem mesas publicas disponiveis."
            txtHybridRoomsEmpty.visibility = View.VISIBLE
            return
        }

        txtHybridRoomsEmpty.visibility = View.GONE

        visibleRooms.forEach { roomId ->
            val occupancy = getMockRoomOccupancy(roomId)
            val creatorName = getMockRoomCreatorName(roomId)

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
                    joinHybridRoomById(roomId)
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
                text = "$occupancy/4"
                setTextColor(Color.parseColor("#CCE7F4FF"))
                textSize = 13f
            }

            val roomCreator = TextView(this).apply {
                layoutParams = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    LinearLayout.LayoutParams.WRAP_CONTENT
                ).apply {
                    topMargin = dp(2)
                }
                text = "Mesa de $creatorName"
                setTextColor(Color.parseColor("#CCE7F4FF"))
                textSize = 12f
            }

            topRow.addView(roomTitle)
            topRow.addView(roomCount)
            card.addView(topRow)
            card.addView(roomCreator)
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

    private fun joinHybridRoomById(roomId: String) {
        val normalizedRoomId = roomId.trim().uppercase()
        val name = displayedPlayerName

        if (normalizedRoomId.isBlank()) {
            Toast.makeText(this, "Insere o ID da sala.", Toast.LENGTH_SHORT).show()
            return
        }

        if (!hasMockRoom(normalizedRoomId)) {
            Toast.makeText(this, "Sala mock nao encontrada.", Toast.LENGTH_SHORT).show()
            return
        }

        val isCreator = getMockRoomCreatorName(normalizedRoomId).equals(name, ignoreCase = false)
        if (!isCreator && !canMockRoomAcceptPlayer(normalizedRoomId, name)) {
            Toast.makeText(this, "Sala hibrida cheia (4/4).", Toast.LENGTH_SHORT).show()
            return
        }

        inputRoomId.setText(normalizedRoomId)
        inputRoomId.setSelection(normalizedRoomId.length)
        renderMockRooms(inputRoomId)

        Toast.makeText(this, "Entraste na sala mock: $normalizedRoomId", Toast.LENGTH_SHORT).show()
        openHybridRoom(roomId = normalizedRoomId, playerName = name, isHost = isCreator)
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
