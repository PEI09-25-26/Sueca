package com.example.MVP

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.AnimatorSet
import android.animation.ObjectAnimator
import android.os.Bundle
import android.util.Log
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import androidx.core.graphics.toColorInt
import android.view.LayoutInflater
import android.view.View
import android.widget.*
import android.view.Gravity
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.MVP.models.*
import com.example.MVP.network.GameMqttSubscriber
import com.example.MVP.network.GatewayClient
import com.example.MVP.network.RetrofitClient
import com.example.MVP.utils.CardMapper
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.Normalizer

class GameActivity : AppCompatActivity() {
    private val logTag = "SuecaGameUI"

    private lateinit var cardsAdapter: CardsAdapter

    // Card slots on the table
    private lateinit var slotPlayer: FrameLayout
    private lateinit var slotPartner: FrameLayout
    private lateinit var slotLeft: FrameLayout
    private lateinit var slotRight: FrameLayout
    private lateinit var slotTrump: FrameLayout
    private lateinit var slotTrumpPartner: FrameLayout
    private lateinit var slotTrumpLeft: FrameLayout
    private lateinit var slotTrumpRight: FrameLayout

    private lateinit var slotTrumpPlayerLabel: TextView
    private lateinit var slotTrumpPartnerLabel: TextView
    private lateinit var slotTrumpLeftLabel: TextView
    private lateinit var slotTrumpRightLabel: TextView

    // Player name labels
    private lateinit var slotPartnerName: TextView
    private lateinit var slotLeftName: TextView
    private lateinit var slotRightName: TextView

    // UI
    private lateinit var txtStatus: TextView
    private lateinit var txtPhase: TextView
    private lateinit var txtTrump: TextView
    private lateinit var txtCurrentPlayer: TextView
    private lateinit var txtTeamScores: TextView
    private lateinit var txtEndBanner: TextView
    private lateinit var actionsLayout: LinearLayout
    private lateinit var rvHand: RecyclerView

    private var playerName: String = ""
    private var playerId: String = ""
    private var gameId: String = ""
    private var pollingJob: Job? = null
    private var mqttSubscriber: GameMqttSubscriber? = null
    private var lastRealtimeUpdateMs: Long = 0L
    private var usingPollingFallback: Boolean = false

    private var myHand: List<String> = emptyList()
    private var currentState: GameStatusResponse? = null

    private var isMyTurn = false

    private var previousRoundNumber = 0
    private var isAnimatingRoundEnd = false
    private var cachedRoundPlays: List<RoundPlay> = emptyList()
    private var cachedMyPos: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_game_mvp)

        playerName = intent.getStringExtra("playerName") ?: ""
        playerId = intent.getStringExtra("playerId") ?: ""
        gameId = intent.getStringExtra("roomId") ?: ""

        if (playerName.isEmpty()) {
            Toast.makeText(this, "Player name required!", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        setupUI()
        startRealtimeUpdates()
        startPolling()
    }

    override fun onDestroy() {
        super.onDestroy()
        pollingJob?.cancel()
        mqttSubscriber?.disconnect()
        mqttSubscriber = null
    }

    private fun setupUI() {

        findViewById<ImageView>(R.id.backButton).setOnClickListener {
            AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
                .setMessage("Desistir do jogo?")
                .setPositiveButton("Sim") { _, _ -> finish() }
                .setNegativeButton("Nao", null)
                .show()
        }

        slotPlayer = findViewById(R.id.slotPlayer)
        slotPartner = findViewById(R.id.slotPartner)
        slotLeft = findViewById(R.id.slotLeft)
        slotRight = findViewById(R.id.slotRight)
        slotTrump = findViewById(R.id.slotTrump)
        slotTrumpPartner = findViewById(R.id.slotTrumpPartner)
        slotTrumpLeft = findViewById(R.id.slotTrumpLeft)
        slotTrumpRight = findViewById(R.id.slotTrumpRight)

        slotTrumpPlayerLabel = findViewById(R.id.slotTrumpPlayerLabel)
        slotTrumpPartnerLabel = findViewById(R.id.slotTrumpPartnerLabel)
        slotTrumpLeftLabel = findViewById(R.id.slotTrumpLeftLabel)
        slotTrumpRightLabel = findViewById(R.id.slotTrumpRightLabel)

        slotPartnerName = findViewById(R.id.slotPartnerName)
        slotLeftName = findViewById(R.id.slotLeftName)
        slotRightName = findViewById(R.id.slotRightName)

        txtStatus = findViewById(R.id.txtStatus)
        txtPhase = findViewById(R.id.txtPhase)
        txtTrump = findViewById(R.id.txtTrump)
        txtCurrentPlayer = findViewById(R.id.txtCurrentPlayer)
        txtTeamScores = findViewById(R.id.txtTeamScores)
        txtEndBanner = findViewById(R.id.txtEndBanner)

        actionsLayout = findViewById(R.id.layoutActions)

        rvHand = findViewById(R.id.playerHandRecyclerView)
        rvHand.layoutManager = object : LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false) {
            override fun canScrollHorizontally(): Boolean = false
        }
        rvHand.setHasFixedSize(true)
        rvHand.itemAnimator = null
        rvHand.overScrollMode = View.OVER_SCROLL_NEVER
        rvHand.setPadding(4, 0, 4, 0)
        rvHand.clipToPadding = false
        rvHand.clipChildren = false
        (rvHand.parent as? android.view.ViewGroup)?.clipChildren = false
        (rvHand.parent as? android.view.ViewGroup)?.clipToPadding = false

        // Adapter for player's hand
        cardsAdapter = CardsAdapter(emptyList()) { card ->
            if (isMyTurn && currentState?.phase == "playing") {
                playCard(card)
            } else {
                Toast.makeText(this, "Not your turn", Toast.LENGTH_SHORT).show()
            }
        }

        rvHand.adapter = cardsAdapter
        rvHand.post {
            cardsAdapter.setAvailableWidth(rvHand.width - rvHand.paddingStart - rvHand.paddingEnd)
        }
        rvHand.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ ->
            cardsAdapter.setAvailableWidth(rvHand.width - rvHand.paddingStart - rvHand.paddingEnd)
        }
    }

    private fun startRealtimeUpdates() {
        if (gameId.isBlank()) return

        Log.i(logTag, "Starting realtime updates gameId=$gameId broker=${RetrofitClient.MQTT_BROKER_HOST}:${RetrofitClient.MQTT_BROKER_PORT} (pls work)")

        val subscriber = GameMqttSubscriber(
            brokerHost = RetrofitClient.MQTT_BROKER_HOST,
            brokerPort = RetrofitClient.MQTT_BROKER_PORT
        )
        mqttSubscriber = subscriber

        subscriber.connectAndSubscribe(
            gameId = gameId,
            onEnvelope = { envelope ->
                runOnUiThread {
                    envelope.state?.let { state ->
                        currentState = state
                        updateUI(state)
                        if (playerId.isBlank()) {
                            playerId = state.players.firstOrNull { samePersonName(it.name, playerName) }?.id ?: ""
                        }
                        lastRealtimeUpdateMs = System.currentTimeMillis()
                        if (usingPollingFallback) {
                            Log.i(logTag, "Realtime stream restored via MQTT (state) gameId=$gameId (nice)")
                        }
                        usingPollingFallback = false
                    }

                    val handOwner = when {
                        playerId.isNotBlank() -> playerId
                        else -> playerName
                    }
                    val hand = envelope.hands[handOwner]
                    if (hand != null) {
                        myHand = hand
                        updateHandUI()
                        lastRealtimeUpdateMs = System.currentTimeMillis()
                        if (usingPollingFallback) {
                            Log.i(logTag, "Realtime stream restored via MQTT (hand) gameId=$gameId (finally)")
                        }
                        usingPollingFallback = false
                    }
                }
            },
            onConnectionError = { error ->
                Log.e(logTag, "MQTT connection error gameId=$gameId: $error (well, not ideal)")
                runOnUiThread {
                    txtStatus.text = error
                }
                lastRealtimeUpdateMs = 0L
                usingPollingFallback = true
            }
        )
    }

    // Fallback polling in case MQTT is temporarily unavailable.
    private fun startPolling() {
        pollingJob = lifecycleScope.launch {
            while (true) {
                try {
                    val staleRealtime = (System.currentTimeMillis() - lastRealtimeUpdateMs) > 15000
                    if (staleRealtime) {
                        if (!usingPollingFallback) {
                            Log.w(logTag, "Switching to polling fallback gameId=$gameId staleMs=${System.currentTimeMillis() - lastRealtimeUpdateMs} (plan B)")
                            usingPollingFallback = true
                        }
                        fetchGameState()
                        fetchHand()
                    }
                } catch (e: Exception) {
                    Log.e(logTag, "Polling error gameId=$gameId (why now)", e)
                    txtStatus.text = "Connection error: ${e.message}"
                }

                delay(5000)
            }
        }
    }

    private suspend fun fetchGameState() {
        try {
            val state = GatewayClient.getStatus(gameId.ifBlank { null }) ?: return
            currentState = state
            updateUI(state)
            if (playerId.isBlank()) {
                playerId = state.players.firstOrNull { samePersonName(it.name, playerName) }?.id ?: ""
            }
            lastRealtimeUpdateMs = System.currentTimeMillis()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private suspend fun fetchHand() {
        try {
            val handOwner = if (playerId.isNotBlank()) playerId else playerName
            val response = GatewayClient.getHand(handOwner, gameId.ifBlank { null })

            if (response.success) {
                myHand = response.hand
                updateHandUI()
                lastRealtimeUpdateMs = System.currentTimeMillis()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // Normalize positions like "Positions.NORTH" -> "NORTH"
    private fun normalizePosition(pos: String?): String {

        if (pos == null) return ""

        val p = pos.uppercase()

        return when {
            p.contains("NORTH") -> "NORTH"
            p.contains("SOUTH") -> "SOUTH"
            p.contains("EAST") -> "EAST"
            p.contains("WEST") -> "WEST"
            else -> p
        }
    }

    // Main UI update
    private fun updateUI(state: GameStatusResponse) {

        val phaseText = when (state.phase) {
            "waiting" -> "Waiting for players (${state.playerCount}/4)"
            "deck_cutting" -> "Deck Cutting"
            "trump_selection" -> "Trump Selection"
            "playing" -> "Round ${state.currentRound}/10"
            "finished" -> "Match Finished"
            else -> state.phase
        }

        txtPhase.text = phaseText

        updateTrumpOwnerUi(state)

        isMyTurn = when {
            playerId.isNotBlank() -> state.currentPlayerId == playerId
            else -> state.currentPlayer == playerName
        }

        if (state.phase == "playing" && state.currentPlayer != null) {

            txtCurrentPlayer.text =
                if (isMyTurn) "Vez: Tu"
                else "Vez: ${state.currentPlayer}"

            txtCurrentPlayer.setTextColor(
                if (isMyTurn)
                    "#FFD166".toColorInt()
                else
                    getColor(android.R.color.white)
            )

            txtCurrentPlayer.visibility = View.GONE
        } else {
            txtCurrentPlayer.visibility = View.GONE
        }

        val scores = state.teamScores

        if (scores != null) {
            val label = "Pontuacao "
            val team1Label = "${scores.team1}"
            val separator = "  |  "
            val team2Label = "${scores.team2}"
            val scoreText = label + team1Label + separator + team2Label

            txtTeamScores.text = SpannableStringBuilder(scoreText).apply {
                setSpan(
                    ForegroundColorSpan("#FFFFFF".toColorInt()),
                    0,
                    label.length,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                setSpan(
                    ForegroundColorSpan("#FFD166".toColorInt()),
                    label.length,
                    label.length + team1Label.length,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                setSpan(
                    ForegroundColorSpan("#D7DCE3".toColorInt()),
                    label.length + team1Label.length + separator.length,
                    scoreText.length,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
            }
            txtTeamScores.visibility = View.VISIBLE
        } else {
            txtTeamScores.visibility = View.GONE
        }

        updatePlayerNames(state)
        updateTableCards(state.roundPlays)
        updateStatusText(state)
        updateActionButtons(state)
        updateFinishedBanner(state)

        cardsAdapter.isEnabled = isMyTurn && state.phase == "playing"
    }

    private fun updateFinishedBanner(state: GameStatusResponse) {
        if (state.phase != "finished") {
            txtEndBanner.visibility = View.GONE
            return
        }

        val team1 = state.teamScores?.team1 ?: 0
        val team2 = state.teamScores?.team2 ?: 0
        val winnerText = when {
            team1 > team2 -> "TEAM 1 (N/S) WINS"
            team2 > team1 -> "TEAM 2 (E/W) WINS"
            else -> "DRAW"
        }

        val match = state.matchPoints
        val matchLine = if (match != null) {
            "\nMatch points: ${match.team1} - ${match.team2}"
        } else {
            ""
        }

        txtEndBanner.text = "$winnerText\nFinal score: $team1 - $team2$matchLine"
        txtEndBanner.visibility = View.VISIBLE
    }

    // Status message shown to the player
    private fun updateStatusText(state: GameStatusResponse) {
        val statusText = when (state.phase) {

            "waiting" ->
                "Waiting for ${4 - state.playerCount} more player(s)..."

            "deck_cutting" -> {
                if ((playerId.isNotBlank() && state.northPlayerId == playerId) || state.northPlayer == playerName)
                    "You are NORTH. Cut the deck (1-40)"
                else
                    "Waiting for ${state.northPlayer}..."
            }

            "trump_selection" -> {
                if ((playerId.isNotBlank() && state.westPlayerId == playerId) || state.westPlayer == playerName)
                    "You are WEST. Choose trump"
                else
                    "Waiting for ${state.westPlayer}..."
            }

            "playing" -> {
                if (isMyTurn)
                    "Vez: Tu"
                else
                    "Vez: ${state.currentPlayer ?: "?"}"
            }

            "finished" -> "Game Over"

            else -> ""
        }

        txtStatus.text = statusText
        txtStatus.setTextColor(
            if (state.phase == "playing" && isMyTurn) "#FFD166".toColorInt()
            else getColor(android.R.color.white)
        )
    }

    // Buttons for special phases
    private fun updateActionButtons(state: GameStatusResponse) {

        actionsLayout.removeAllViews()

        if (state.phase == "deck_cutting" && ((playerId.isNotBlank() && state.northPlayerId == playerId) || state.northPlayer == playerName)) {

            val btn = Button(this)
            btn.text = "Cut Deck"
            btn.setOnClickListener { showCutDeckDialog() }

            actionsLayout.addView(btn)
        }

        if (state.phase == "trump_selection" && ((playerId.isNotBlank() && state.westPlayerId == playerId) || state.westPlayer == playerName)) {

            val top = Button(this)
            top.text = "TOP"
            top.setOnClickListener { selectTrump("top") }

            val bottom = Button(this)
            bottom.text = "BOTTOM"
            bottom.setOnClickListener { selectTrump("bottom") }

            actionsLayout.addView(top)
            actionsLayout.addView(bottom)
        }

        if (state.phase == "finished" && gameId.isNotBlank()) {
            val rematch = Button(this)
            rematch.text = "Rematch"
            rematch.setOnClickListener { requestRematch() }

            val score = Button(this)
            score.text = "Match Score"
            score.setOnClickListener { showMatchScoreDialog() }

            actionsLayout.addView(rematch)
            actionsLayout.addView(score)
        }
    }

    private fun requestRematch() {
        if (gameId.isBlank()) return

        lifecycleScope.launch {
            try {
                val res = GatewayClient.requestRematch(gameId)
                Toast.makeText(
                    this@GameActivity,
                    res.message ?: if (res.success) "Rematch requested" else "Rematch failed",
                    Toast.LENGTH_SHORT
                ).show()
            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, "Rematch error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showMatchScoreDialog() {
        if (gameId.isBlank()) return

        lifecycleScope.launch {
            try {
                val response = GatewayClient.getMatchPoints(gameId)
                if (!response.success) {
                    Toast.makeText(
                        this@GameActivity,
                        response.message ?: "Could not load match score",
                        Toast.LENGTH_SHORT
                    ).show()
                    return@launch
                }

                val points = response.points
                val team1 = points?.team1 ?: 0
                val team2 = points?.team2 ?: 0
                val matchesPlayed = response.matchesPlayed ?: 0

                AlertDialog.Builder(this@GameActivity, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
                    .setTitle("Match Scoreboard")
                    .setMessage(
                        "Team 1 (N/S): $team1\n" +
                            "Team 2 (E/W): $team2\n\n" +
                            "Matches played: $matchesPlayed"
                    )
                    .setPositiveButton("OK", null)
                    .show()
            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, "Score error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun showCutDeckDialog() {

        val input = EditText(this)
        input.hint = "1 - 40"
        input.inputType = android.text.InputType.TYPE_CLASS_NUMBER

        AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle("Cut deck")
            .setView(input)
            .setPositiveButton("Cut") { _, _ ->

                val index = input.text.toString().toIntOrNull()

                if (index != null && index in 1..40) {
                    cutDeck(index)
                } else {
                    Toast.makeText(this, "Invalid number", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun cutDeck(index: Int) {

        lifecycleScope.launch {
            try {
                val res = GatewayClient.cutDeck(
                    CutDeckRequest(
                        playerId = if (playerId.isNotBlank()) playerId else playerName,
                        index = index,
                        gameId = gameId.ifBlank { null }
                    )
                )

                Toast.makeText(
                    this@GameActivity,
                    res.message ?: "Deck cut",
                    Toast.LENGTH_SHORT
                ).show()

            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, e.message, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun selectTrump(choice: String) {

        lifecycleScope.launch {
            try {

                val res = GatewayClient.selectTrump(
                    SelectTrumpRequest(
                        playerId = if (playerId.isNotBlank()) playerId else playerName,
                        choice = choice,
                        gameId = gameId.ifBlank { null }
                    )
                )

                Toast.makeText(
                    this@GameActivity,
                    res.message ?: "Trump selected",
                    Toast.LENGTH_SHORT
                ).show()

            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, e.message, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun playCard(card: Card) {
        val myPos = currentState?.players
            ?.find { it.name == playerName }
            ?.position

        // Only add if not already in cache (avoid duplicates)
        if (cachedRoundPlays.none { it.playerName == playerName && it.card == card.id }) {
            val myPlay = RoundPlay(playerName = playerName, card = card.id, position = myPos)
            cachedRoundPlays = cachedRoundPlays + myPlay
            cachedMyPos = myPos
        }
        val slot = getSlotForPosition(myPos, myPos)
        addCardToSlot(slot, card)

        lifecycleScope.launch {
            try {

                val res = GatewayClient.playCard(
                    PlayRequest(
                        playerId = if (playerId.isNotBlank()) playerId else playerName,
                        card = card.id,
                        gameId = gameId.ifBlank { null }
                    )
                )

                Toast.makeText(
                    this@GameActivity,
                    res.message ?: "Card played",
                    Toast.LENGTH_SHORT
                ).show()

            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, e.message, Toast.LENGTH_SHORT).show()
            }
        }
    }

    // Update cards in player's hand
    private fun updateHandUI() {

        val cards = myHand.map { id ->

            val num = id.toIntOrNull() ?: 0

            Card(
                id,
                CardMapper.getCardSuitName(num),
                CardMapper.getCardRankName(num)
            )
        }

        cardsAdapter.updateCards(cards)
    }

    private fun updatePlayerNames(state: GameStatusResponse) {

        val myPos = state.players
            .find { it.name == playerName }
            ?.position ?: return

        for (p in state.players) {

            if (p.name == playerName) continue

            val slot = getNameSlotForPosition(p.position, myPos)
            slot?.text = p.name
        }
    }

    private fun getNameSlotForPosition(playerPosition: String, myPosition: String): TextView? {

        val positions = listOf("NORTH", "EAST", "SOUTH", "WEST")

        val myIndex = positions.indexOf(normalizePosition(myPosition))
        val otherIndex = positions.indexOf(normalizePosition(playerPosition))

        if (myIndex == -1 || otherIndex == -1) return null

        val relative = (otherIndex - myIndex + 4) % 4

        return when (relative) {
            1 -> slotLeftName
            2 -> slotPartnerName
            3 -> slotRightName
            else -> null
        }
    }

    private fun updateTableCards(roundPlays: List<RoundPlay>) {

        // Don't update while animating
        if (isAnimatingRoundEnd) return

        val currentRound = currentState?.currentRound ?: 1
        val myPos = currentState?.players
            ?.find { it.name == playerName }
            ?.position

        if (currentRound > previousRoundNumber && cachedRoundPlays.isNotEmpty()) {
            displayCachedCardsAndAnimate()
            previousRoundNumber = currentRound
            return
        }

        if (roundPlays.isNotEmpty()) {
            cachedRoundPlays = roundPlays.toList()
            cachedMyPos = myPos
        }

        previousRoundNumber = currentRound

        slotPlayer.removeAllViews()
        slotPartner.removeAllViews()
        slotLeft.removeAllViews()
        slotRight.removeAllViews()

        for (play in roundPlays) {

            val id = play.card.toIntOrNull() ?: continue

            val card = Card(
                play.card,
                CardMapper.getCardSuitName(id),
                CardMapper.getCardRankName(id)
            )

            val slot = getSlotForPosition(play.position, myPos)
            addCardToSlot(slot, card)
        }
    }

    private fun displayCachedCardsAndAnimate() {
        isAnimatingRoundEnd = true

        slotPlayer.removeAllViews()
        slotPartner.removeAllViews()
        slotLeft.removeAllViews()
        slotRight.removeAllViews()

        for (play in cachedRoundPlays) {
            val id = play.card.toIntOrNull() ?: continue
            val card = Card(
                play.card,
                CardMapper.getCardSuitName(id),
                CardMapper.getCardRankName(id)
            )
            val slot = getSlotForPosition(play.position, cachedMyPos)
            addCardToSlot(slot, card)
        }


        cachedRoundPlays = emptyList()

        slotPlayer.postDelayed({
            animateCardsToWinner()
        }, 500)  // Show cards for 0.5 second before animating
    }

    private fun animateCardsToWinner() {
        // Find winner's slot position (current player after round = winner)
        val winnerName = currentState?.currentPlayer
        val winnerPos = currentState?.players
            ?.find { it.name == winnerName }
            ?.position

        val myPos = currentState?.players
            ?.find { it.name == playerName }
            ?.position

        val targetSlot = getSlotForPosition(winnerPos, myPos)

        // Get target coordinates (center of winner's slot)
        val targetX = targetSlot.x + targetSlot.width / 2
        val targetY = targetSlot.y + targetSlot.height / 2

        val slots = listOf(slotPlayer, slotPartner, slotLeft, slotRight)
        val animators = mutableListOf<Animator>()

        for (slot in slots) {
            if (slot.childCount == 0) continue

            val cardView = slot.getChildAt(0)

            // Calculate movement delta
            val startX = slot.x + cardView.x
            val startY = slot.y + cardView.y
            val deltaX = targetX - startX - cardView.width / 2
            val deltaY = targetY - startY - cardView.height / 2

            val animX = ObjectAnimator.ofFloat(cardView, "translationX", 0f, deltaX)
            val animY = ObjectAnimator.ofFloat(cardView, "translationY", 0f, deltaY)
            val animAlpha = ObjectAnimator.ofFloat(cardView, "alpha", 1f, 0.3f)

            animators.add(animX)
            animators.add(animY)
            animators.add(animAlpha)
        }

        if (animators.isEmpty()) {
            isAnimatingRoundEnd = false
            return
        }

        val animatorSet = AnimatorSet()
        animatorSet.playTogether(animators)
        animatorSet.duration = 500  // 500ms animation

        animatorSet.addListener(object : AnimatorListenerAdapter() {
            override fun onAnimationEnd(animation: Animator) {
                // Clear table after animation
                slotPlayer.removeAllViews()
                slotPartner.removeAllViews()
                slotLeft.removeAllViews()
                slotRight.removeAllViews()
                isAnimatingRoundEnd = false
            }
        })

        animatorSet.start()
    }

    private fun getSlotForPosition(playPos: String?, myPos: String?): FrameLayout {

        if (playPos == null || myPos == null) return slotPlayer

        val positions = listOf("NORTH", "EAST", "SOUTH", "WEST")

        val myIndex = positions.indexOf(normalizePosition(myPos))
        val playIndex = positions.indexOf(normalizePosition(playPos))

        if (myIndex == -1 || playIndex == -1) return slotPlayer

        val relative = (playIndex - myIndex + 4) % 4

        return when (relative) {
            0 -> slotPlayer
            1 -> slotLeft
            2 -> slotPartner
            3 -> slotRight
            else -> slotPlayer
        }
    }

    private fun addCardToSlot(slot: FrameLayout, card: Card) {

        val view = LayoutInflater.from(this)
            .inflate(R.layout.item_card_mvp, slot, false)

        val img = view.findViewById<ImageView>(R.id.cardImage)
        img.setImageResource(getCardResource(card))

        slot.removeAllViews()
        slot.addView(view)
    }

    private fun updateTrumpOwnerUi(state: GameStatusResponse) {
        clearTrumpOwnerUi()

        val trumpId = state.trump?.toIntOrNull() ?: return
        val myPos = resolveMyPosition(state) ?: "SOUTH"

        val ownerAbsolutePos = resolveTrumpOwnerPosition(state) ?: "WEST"
        val ownerRelative = getRelativePosition(ownerAbsolutePos, myPos)
        if (ownerRelative !in 0..3) return

        val trumpCard = Card(
            trumpId.toString(),
            CardMapper.getCardSuitName(trumpId),
            CardMapper.getCardRankName(trumpId)
        )

        when (ownerRelative) {
            0 -> {
                addTrumpCardToSlot(slotTrump, trumpCard)
                slotTrumpPlayerLabel.visibility = View.VISIBLE
            }

            1 -> {
                addTrumpCardToSlot(slotTrumpLeft, trumpCard)
                slotTrumpLeftLabel.visibility = View.VISIBLE
            }

            2 -> {
                addTrumpCardToSlot(slotTrumpPartner, trumpCard)
                slotTrumpPartnerLabel.visibility = View.VISIBLE
            }

            3 -> {
                addTrumpCardToSlot(slotTrumpRight, trumpCard)
                slotTrumpRightLabel.visibility = View.VISIBLE
            }
        }
    }

    private fun clearTrumpOwnerUi() {
        slotTrump.removeAllViews()
        slotTrumpPartner.removeAllViews()
        slotTrumpLeft.removeAllViews()
        slotTrumpRight.removeAllViews()

        slotTrumpPlayerLabel.visibility = View.GONE
        slotTrumpPartnerLabel.visibility = View.GONE
        slotTrumpLeftLabel.visibility = View.GONE
        slotTrumpRightLabel.visibility = View.GONE
    }

    private fun resolveMyPosition(state: GameStatusResponse): String? {
        val byId = state.players.find { playerId.isNotBlank() && it.id == playerId }?.position
        if (!byId.isNullOrBlank()) return normalizePosition(byId)

        val byName = state.players.find { samePersonName(it.name, playerName) }?.position
        if (!byName.isNullOrBlank()) return normalizePosition(byName)

        return null
    }

    private fun resolveTrumpOwnerPosition(state: GameStatusResponse): String? {
        val selectorPosition = normalizePosition(state.trumpSelectorPosition)
        if (selectorPosition.isNotEmpty()) return selectorPosition

        val bySelectorId = state.players.find { it.id != null && it.id == state.trumpSelectorPlayerId }?.position
        if (!bySelectorId.isNullOrBlank()) return normalizePosition(bySelectorId)

        val bySelectorName = state.players.find { samePersonName(it.name, state.trumpSelectorPlayer) }?.position
        if (!bySelectorName.isNullOrBlank()) return normalizePosition(bySelectorName)

        val byWestId = state.players.find { it.id != null && it.id == state.westPlayerId }?.position
        if (!byWestId.isNullOrBlank()) return normalizePosition(byWestId)

        val byWestName = state.players.find { samePersonName(it.name, state.westPlayer) }?.position
        if (!byWestName.isNullOrBlank()) return normalizePosition(byWestName)

        return null
    }

    private fun samePersonName(a: String?, b: String?): Boolean {
        if (a.isNullOrBlank() || b.isNullOrBlank()) return false

        fun normalizeName(value: String): String {
            val normalized = Normalizer.normalize(value, Normalizer.Form.NFD)
            return normalized
                .replace("\\p{Mn}+".toRegex(), "")
                .trim()
                .lowercase()
        }

        return normalizeName(a) == normalizeName(b)
    }

    private fun getRelativePosition(playerPosition: String?, myPosition: String?): Int {
        if (playerPosition.isNullOrBlank() || myPosition.isNullOrBlank()) return -1

        val positions = listOf("NORTH", "EAST", "SOUTH", "WEST")
        val myIndex = positions.indexOf(normalizePosition(myPosition))
        val otherIndex = positions.indexOf(normalizePosition(playerPosition))

        if (myIndex == -1 || otherIndex == -1) return -1
        return (otherIndex - myIndex + 4) % 4
    }

    private fun addTrumpCardToSlot(targetSlot: FrameLayout, card: Card) {
        val resId = getCardResource(card)
        val image = ImageView(this)
        image.setImageResource(resId)
        image.scaleType = ImageView.ScaleType.FIT_XY

        val density = resources.displayMetrics.density
        val fallbackWidth = (35 * density).toInt()
        val fallbackHeight = (72 * density).toInt()
        val slotWidth = targetSlot.layoutParams?.width?.takeIf { it > 0 } ?: fallbackWidth
        val slotHeight = targetSlot.layoutParams?.height?.takeIf { it > 0 } ?: fallbackHeight

        // Keep slot size but zoom the card image inside, like the mockup corner style.
        val imageWidth = (slotWidth * 5f).toInt()
        val imageHeight = (slotHeight * 4f).toInt()
        image.layoutParams = FrameLayout.LayoutParams(imageWidth, imageHeight).apply {
            gravity = Gravity.TOP or Gravity.START
        }

        image.translationX = 0f
        image.translationY = 0f

        targetSlot.removeAllViews()
        targetSlot.setPadding(0, 0, 0, 0)
        targetSlot.clipToPadding = true
        targetSlot.clipChildren = true
        targetSlot.background = null
        targetSlot.addView(image)
    }

    private fun getCardResource(card: Card): Int {

        val suit = card.suit.lowercase()

        val value = when (card.value.lowercase()) {
            "k", "king" -> "king"
            "q", "queen" -> "queen"
            "j", "jack" -> "jack"
            "a", "ace" -> "ace"
            else -> card.value.lowercase()
        }

        val id = resources.getIdentifier("${suit}_$value", "drawable", packageName)

        return if (id != 0) id else R.drawable.card_back
    }
}