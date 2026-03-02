package com.example.MVP

import android.os.Bundle
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
    
    private lateinit var slotPlayer: FrameLayout
    private lateinit var slotPartner: FrameLayout
    private lateinit var slotLeft: FrameLayout
    private lateinit var slotRight: FrameLayout
    
    private lateinit var txtStatus: TextView
    private lateinit var txtPhase: TextView
    private lateinit var txtTrump: TextView
    private lateinit var txtRound: TextView
    private lateinit var txtCurrentPlayer: TextView
    private lateinit var txtTeamScores: TextView
    private lateinit var layoutActions: LinearLayout
    private lateinit var rvHand: RecyclerView

    private var playerName: String = ""
    private var pollingJob: Job? = null
    private var myHand: List<String> = emptyList()
    private var currentState: GameStatusResponse? = null
    
    private var isMyTurn: Boolean = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_game_mvp)

        playerName = intent.getStringExtra("playerName") ?: ""
        
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
        
        txtStatus = findViewById(R.id.txtStatus)
        txtPhase = findViewById(R.id.txtPhase)
        txtTrump = findViewById(R.id.txtTrump)
        txtRound = findViewById(R.id.txtRound)
        txtCurrentPlayer = findViewById(R.id.txtCurrentPlayer)
        txtTeamScores = findViewById(R.id.txtTeamScores)
        layoutActions = findViewById(R.id.layoutActions)
        
        rvHand = findViewById(R.id.playerHandRecyclerView)
        rvHand.layoutManager = GridLayoutManager(this, 5)
        
        cardsAdapter = CardsAdapter(emptyList()) { card ->
            if (isMyTurn && currentState?.phase == "playing") {
                playCard(card)
            } else {
                Toast.makeText(this, "Not your turn!", Toast.LENGTH_SHORT).show()
            }
        }
        rvHand.adapter = cardsAdapter
    }

    private fun startPolling() {
        pollingJob = lifecycleScope.launch {
            while (true) {
                try {
                    fetchGameState()
                    fetchHand()
                } catch (e: Exception) {
                    txtStatus.text = "Connection error: ${e.message}"
                }
                delay(2000) // Poll every 2 seconds like client.py
            }
        }
    }

    private suspend fun fetchGameState() {
        try {
            val state = RetrofitClient.api.getStatus()
            currentState = state
            updateUI(state)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private suspend fun fetchHand() {
        try {
            val response = RetrofitClient.api.getHand(playerName)
            if (response.success) {
                myHand = response.hand
                updateHandUI()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun updateUI(state: GameStatusResponse) {
        // Update phase text
        txtPhase.text = when (state.phase) {
            "waiting" -> "Waiting for players (${state.playerCount}/4)"
            "deck_cutting" -> "Deck Cutting Phase"
            "trump_selection" -> "Trump Selection Phase"
            "playing" -> "Playing - Round ${state.currentRound}/10"
            "finished" -> "Game Finished!"
            else -> state.phase.uppercase()
        }

        // Update trump display
        if (state.trump != null) {
            val trumpId = state.trump.toIntOrNull()
            val trumpDisplay = if (trumpId != null) CardMapper.getCard(trumpId) else state.trump
            txtTrump.text = "Trump: $trumpDisplay"
            txtTrump.visibility = View.VISIBLE
        } else {
            txtTrump.visibility = View.GONE
        }

        // Update round info
        txtRound.text = "Round: ${state.currentRound}/10"
        txtRound.visibility = if (state.phase == "playing") View.VISIBLE else View.GONE

        // Update current player
        isMyTurn = state.currentPlayer == playerName
        if (state.phase == "playing" && state.currentPlayer != null) {
            val turnText = if (isMyTurn) "YOUR TURN!" else "Turn: ${state.currentPlayer}"
            txtCurrentPlayer.text = turnText
            txtCurrentPlayer.setTextColor(
                if (isMyTurn) getColor(android.R.color.holo_green_light) 
                else getColor(android.R.color.white)
            )
            txtCurrentPlayer.visibility = View.VISIBLE
        } else {
            txtCurrentPlayer.visibility = View.GONE
        }

        // Update team scores
        val scores = state.teamScores
        if (scores != null) {
            txtTeamScores.text = "Team 1: ${scores.team1} | Team 2: ${scores.team2}"
            txtTeamScores.visibility = View.VISIBLE
        } else {
            txtTeamScores.visibility = View.GONE
        }

        // Update cards on table
        updateTableCards(state.roundPlays)

        // Update status text based on phase
        updateStatusText(state)

        // Show action buttons for special phases
        updateActionButtons(state)

        // Enable/disable cards based on turn
        cardsAdapter.isEnabled = isMyTurn && state.phase == "playing"
    }

    private fun updateStatusText(state: GameStatusResponse) {
        txtStatus.text = when (state.phase) {
            "waiting" -> "Waiting for ${4 - state.playerCount} more player(s)..."
            "deck_cutting" -> {
                if (state.northPlayer == playerName) {
                    "YOU are NORTH! Cut the deck (1-40)"
                } else {
                    "Waiting for ${state.northPlayer} (NORTH) to cut..."
                }
            }
            "trump_selection" -> {
                if (state.westPlayer == playerName) {
                    "YOU are WEST! Select trump card"
                } else {
                    "Waiting for ${state.westPlayer} (WEST) to select trump..."
                }
            }
            "playing" -> {
                val roundSuitInfo = if (state.roundSuit != null) " | Follow: ${state.roundSuit}" else ""
                if (isMyTurn) "Your turn! Tap a card to play$roundSuitInfo"
                else "Waiting for ${state.currentPlayer}...$roundSuitInfo"
            }
            "finished" -> {
                val scores = state.teamScores
                if (scores != null) {
                    when {
                        scores.team1 > scores.team2 -> "🏆 Team 1 WINS! (${scores.team1} vs ${scores.team2})"
                        scores.team2 > scores.team1 -> "🏆 Team 2 WINS! (${scores.team2} vs ${scores.team1})"
                        else -> "TIE! (${scores.team1} vs ${scores.team2})"
                    }
                } else "Game Over!"
            }
            else -> ""
        }
    }

    private fun updateActionButtons(state: GameStatusResponse) {
        layoutActions.removeAllViews()

        when (state.phase) {
            "deck_cutting" -> {
                if (state.northPlayer == playerName) {
                    val btnCut = Button(this).apply {
                        text = "Cut Deck"
                        setOnClickListener { showCutDeckDialog() }
                    }
                    layoutActions.addView(btnCut)
                }
            }
            "trump_selection" -> {
                if (state.westPlayer == playerName) {
                    val btnTop = Button(this).apply {
                        text = "TOP"
                        setOnClickListener { selectTrump("top") }
                    }
                    val btnBottom = Button(this).apply {
                        text = "BOTTOM"
                        setOnClickListener { selectTrump("bottom") }
                    }
                    layoutActions.addView(btnTop)
                    layoutActions.addView(btnBottom)
                }
            }
        }
    }

    private fun showCutDeckDialog() {
        val input = EditText(this).apply {
            hint = "Enter number (1-40)"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
        }
        
        AlertDialog.Builder(this)
            .setTitle("Cut the Deck")
            .setMessage("Enter a number between 1 and 40 to cut the deck")
            .setView(input)
            .setPositiveButton("Cut") { _, _ ->
                val index = input.text.toString().toIntOrNull()
                if (index != null && index in 1..40) {
                    cutDeck(index)
                } else {
                    Toast.makeText(this, "Invalid number! Must be 1-40", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun cutDeck(index: Int) {
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api.cutDeck(CutDeckRequest(playerName, index))
                if (response.success) {
                    Toast.makeText(this@GameActivity, response.message ?: "Deck cut!", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@GameActivity, response.message ?: "Failed!", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun selectTrump(choice: String) {
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api.selectTrump(SelectTrumpRequest(playerName, choice))
                if (response.success) {
                    Toast.makeText(this@GameActivity, response.message ?: "Trump selected!", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@GameActivity, response.message ?: "Failed!", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun playCard(card: Card) {
        lifecycleScope.launch {
            try {
                val response = RetrofitClient.api.playCard(PlayRequest(playerName, card.id))
                if (response.success) {
                    Toast.makeText(this@GameActivity, response.message ?: "Card played!", Toast.LENGTH_SHORT).show()
                    // Immediately fetch new state
                    fetchGameState()
                    fetchHand()
                } else {
                    Toast.makeText(this@GameActivity, response.message ?: "Cannot play this card!", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@GameActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun updateHandUI() {
        // Convert card IDs to Card objects
        val cards = myHand.mapIndexed { index, cardStr ->
            val cardId = cardStr.toIntOrNull() ?: 0
            Card(
                id = cardStr,
                suit = CardMapper.getCardSuitName(cardId),
                value = CardMapper.getCardRankName(cardId)
            )
        }
        cardsAdapter.updateCards(cards)
    }

    private fun updateTableCards(roundPlays: List<RoundPlay>) {
        // Clear all slots first
        slotPlayer.removeAllViews()
        slotPartner.removeAllViews()
        slotLeft.removeAllViews()
        slotRight.removeAllViews()

        // Get my position
        val myPosition = currentState?.players?.find { it.name == playerName }?.position

        for (play in roundPlays) {
            val cardId = play.card.toIntOrNull() ?: continue
            val card = Card(
                id = play.card,
                suit = CardMapper.getCardSuitName(cardId),
                value = CardMapper.getCardRankName(cardId)
            )

            // Determine which slot based on relative position
            val slot = getSlotForPosition(play.position, myPosition)
            addCardToSlot(slot, card)
        }
    }

    private fun getSlotForPosition(playPosition: String?, myPosition: String?): FrameLayout {
        // Map positions relative to player's position
        // Player is always at bottom (slotPlayer)
        // Partner is at top (slotPartner) - opposite position
        // Left and Right opponents on the sides
        
        if (playPosition == null || myPosition == null) return slotPlayer
        
        // Extract just the position name (handles "Positions.NORTH" -> "NORTH" or "NORTH" -> "NORTH")
        val normalizePosition: (String) -> String = { pos ->
            val upper = pos.uppercase()
            when {
                upper.contains("NORTH") -> "NORTH"
                upper.contains("SOUTH") -> "SOUTH"
                upper.contains("EAST") -> "EAST"
                upper.contains("WEST") -> "WEST"
                else -> upper
            }
        }
        
        val positions = listOf("NORTH", "EAST", "SOUTH", "WEST")
        val myNormalized = normalizePosition(myPosition)
        val playNormalized = normalizePosition(playPosition)
        
        val myIndex = positions.indexOf(myNormalized)
        val playIndex = positions.indexOf(playNormalized)
        
        if (myIndex == -1 || playIndex == -1) return slotPlayer
        
        val relativePosition = (playIndex - myIndex + 4) % 4
        
        return when (relativePosition) {
            0 -> slotPlayer      // Same position (me)
            1 -> slotRight       // Next clockwise (right)
            2 -> slotPartner     // Opposite (partner)
            3 -> slotLeft        // Previous clockwise (left)
            else -> slotPlayer
        }
    }

    private fun addCardToSlot(slot: FrameLayout, card: Card) {
        val cardView = LayoutInflater.from(this).inflate(R.layout.item_card_mvp, slot, false)
        val imageView = cardView.findViewById<ImageView>(R.id.cardImage)
        imageView.setImageResource(getCardResource(card))
        
        slot.removeAllViews()
        slot.addView(cardView)
    }

    private fun getCardResource(card: Card): Int {
        val suit = card.suit.lowercase()
        val value = when (val v = card.value.lowercase()) {
            "k", "king" -> "king"
            "q", "queen" -> "queen"
            "j", "jack" -> "jack"
            "a", "ace" -> "ace"
            else -> v
        }
        val identifier = "${suit}_$value"
        val resId = resources.getIdentifier(identifier, "drawable", packageName)
        return if (resId != 0) resId else R.drawable.card_back
    }
}