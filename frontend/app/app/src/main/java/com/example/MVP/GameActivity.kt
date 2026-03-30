package com.example.MVP

import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.animation.AnimatorSet
import android.animation.ObjectAnimator
import android.os.Bundle
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.view.LayoutInflater
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.MVP.models.*
import com.example.MVP.network.RetrofitClient
import com.example.MVP.utils.CardMapper
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class GameActivity : AppCompatActivity() {

    private lateinit var cardsAdapter: CardsAdapter

    // Card slots on the table
    private lateinit var slotPlayer: FrameLayout
    private lateinit var slotPartner: FrameLayout
    private lateinit var slotLeft: FrameLayout
    private lateinit var slotRight: FrameLayout
    private lateinit var slotTrump: FrameLayout

    // Player name labels
    private lateinit var slotPartnerName: TextView
    private lateinit var slotLeftName: TextView
    private lateinit var slotRightName: TextView

    // UI
    private lateinit var txtStatus: TextView
    private lateinit var txtPhase: TextView
    private lateinit var txtTrump: TextView
    private lateinit var txtRound: TextView
    private lateinit var txtCurrentPlayer: TextView
    private lateinit var txtTeamScores: TextView
    private lateinit var txtEndBanner: TextView
    private lateinit var actionsLayout: LinearLayout
    private lateinit var rvHand: RecyclerView

    private var playerName: String = ""
    private var playerId: String = ""
    private var gameId: String = ""
    private var pollingJob: Job? = null

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
        startPolling()
    }

    override fun onDestroy() {
        super.onDestroy()
        pollingJob?.cancel()
    }

    private fun setupUI() {

        findViewById<ImageView>(R.id.backButton).setOnClickListener { finish() }

        slotPlayer = findViewById(R.id.slotPlayer)
        slotPartner = findViewById(R.id.slotPartner)
        slotLeft = findViewById(R.id.slotLeft)
        slotRight = findViewById(R.id.slotRight)
        slotTrump = findViewById(R.id.slotTrump)

        slotPartnerName = findViewById(R.id.slotPartnerName)
        slotLeftName = findViewById(R.id.slotLeftName)
        slotRightName = findViewById(R.id.slotRightName)

        txtStatus = findViewById(R.id.txtStatus)
        txtPhase = findViewById(R.id.txtPhase)
        txtTrump = findViewById(R.id.txtTrump)
        txtRound = findViewById(R.id.txtRound)
        txtCurrentPlayer = findViewById(R.id.txtCurrentPlayer)
        txtTeamScores = findViewById(R.id.txtTeamScores)
        txtEndBanner = findViewById(R.id.txtEndBanner)

        actionsLayout = findViewById(R.id.layoutActions)

        rvHand = findViewById(R.id.playerHandRecyclerView)
        rvHand.layoutManager = GridLayoutManager(this, 5)

        // Adapter for player's hand
        cardsAdapter = CardsAdapter(emptyList()) { card ->
            if (isMyTurn && currentState?.phase == "playing") {
                playCard(card)
            } else {
                Toast.makeText(this, "Not your turn", Toast.LENGTH_SHORT).show()
            }
        }

        rvHand.adapter = cardsAdapter
    }

    // Poll the server every few seconds
    private fun startPolling() {
        pollingJob = lifecycleScope.launch {
            while (true) {
                try {
                    fetchGameState()
                    fetchHand()
                } catch (e: Exception) {
                    txtStatus.text = "Connection error: ${e.message}"
                }

                delay(2000)
            }
        }
    }

    private suspend fun fetchGameState() {
        try {
            val state = RetrofitClient.api.getStatus(gameId.ifBlank { null })
            currentState = state
            updateUI(state)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private suspend fun fetchHand() {
        try {
            val handOwner = if (playerId.isNotBlank()) playerId else playerName
            val response = RetrofitClient.api.getHand(handOwner, gameId.ifBlank { null })

            if (response.success) {
                myHand = response.hand
                updateHandUI()
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

        // Show trump card
        if (state.trump != null) {
            val trumpId = state.trump.toIntOrNull()
            if (trumpId != null && slotTrump.childCount == 0) {
                val trumpCard = Card(
                    state.trump,
                    CardMapper.getCardSuitName(trumpId),
                    CardMapper.getCardRankName(trumpId)
                )
                addTrumpCardToSlot(trumpCard)
            }
            slotTrump.visibility = View.VISIBLE
        } else {
            slotTrump.removeAllViews()
            slotTrump.visibility = View.GONE
        }

        txtRound.text = "Round: ${state.currentRound}/10"
        txtRound.visibility = if (state.phase == "playing") View.VISIBLE else View.GONE

        isMyTurn = when {
            playerId.isNotBlank() -> state.currentPlayerId == playerId
            else -> state.currentPlayer == playerName
        }

        if (state.phase == "playing" && state.currentPlayer != null) {

            txtCurrentPlayer.text =
                if (isMyTurn) "YOUR TURN!"
                else "Turn: ${state.currentPlayer}"

            txtCurrentPlayer.setTextColor(
                if (isMyTurn)
                    getColor(android.R.color.holo_green_light)
                else
                    getColor(android.R.color.white)
            )

            txtCurrentPlayer.visibility = View.VISIBLE
        } else {
            txtCurrentPlayer.visibility = View.GONE
        }

        val scores = state.teamScores

        if (scores != null) {
            val team1Label = "Team N/S: ${scores.team1}"
            val separator = "  |  "
            val team2Label = "Team E/W: ${scores.team2}"
            val scoreText = team1Label + separator + team2Label

            txtTeamScores.text = SpannableStringBuilder(scoreText).apply {
                setSpan(
                    ForegroundColorSpan(getColor(android.R.color.holo_green_light)),
                    0,
                    team1Label.length,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                setSpan(
                    ForegroundColorSpan(getColor(android.R.color.holo_blue_light)),
                    team1Label.length + separator.length,
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

        txtStatus.text = when (state.phase) {

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
                    "Your turn! Play a card"
                else
                    "Waiting for ${state.currentPlayer}"
            }

            "finished" -> "Game Over"

            else -> ""
        }
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
                val res = RetrofitClient.api.requestRematch(gameId)
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
                val response = RetrofitClient.api.getMatchPoints(gameId)
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

                AlertDialog.Builder(this@GameActivity)
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

        AlertDialog.Builder(this)
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
                val res = RetrofitClient.api.cutDeck(
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

                val res = RetrofitClient.api.selectTrump(
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

                val res = RetrofitClient.api.playCard(
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

                fetchGameState()
                fetchHand()

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

    private fun addTrumpCardToSlot(card: Card) {
        val view = LayoutInflater.from(this)
            .inflate(R.layout.item_card_mvp, slotTrump, false)

        val img = view.findViewById<ImageView>(R.id.cardImage)
        img.setImageResource(getCardResource(card))

        // Scale down the trump card slightly to differentiate
        view.scaleX = 0.9f
        view.scaleY = 0.9f
        view.alpha = 0.85f

        slotTrump.removeAllViews()
        slotTrump.addView(view)
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