package com.example.MVP

import android.os.Bundle
import android.view.View
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.models.MatchHistoryEntry
import kotlinx.coroutines.launch

class MatchHistoryActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_UID = "extra_match_history_uid"
    }

    private lateinit var progressBar: ProgressBar
    private lateinit var emptyText: TextView
    private lateinit var matchListContainer: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_match_history)

        val backButton = findViewById<ImageView>(R.id.backButtonMatchHistory)
        progressBar = findViewById(R.id.matchHistoryProgress)
        emptyText = findViewById(R.id.matchHistoryEmpty)
        matchListContainer = findViewById(R.id.matchHistoryList)

        backButton.setOnClickListener { finish() }

        val uid = intent.getStringExtra(EXTRA_UID)
        if (uid == null) {
            Toast.makeText(this, "Utilizador inválido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        loadMatchHistory(uid)
    }

    private fun loadMatchHistory(uid: String) {
        progressBar.visibility = View.VISIBLE
        emptyText.visibility = View.GONE
        matchListContainer.removeAllViews()

        lifecycleScope.launch {
            AuthManager.getMatchHistory(uid)
                .onSuccess { history ->
                    progressBar.visibility = View.GONE
                    if (history.isEmpty()) {
                        emptyText.visibility = View.VISIBLE
                    } else {
                        history.forEach { entry ->
                            val card = buildMatchCard(entry)
                            matchListContainer.addView(card)
                        }
                    }
                }
                .onFailure { error ->
                    progressBar.visibility = View.GONE
                    emptyText.visibility = View.VISIBLE
                    emptyText.text = "Erro ao carregar histórico:\n${error.message}"
                }
        }
    }

    private fun buildMatchCard(entry: MatchHistoryEntry): View {
        val inflater = layoutInflater
        val card = inflater.inflate(R.layout.item_match_history, matchListContainer, false)

        val gameIdText = card.findViewById<TextView>(R.id.matchItemGameId)
        val positionText = card.findViewById<TextView>(R.id.matchItemPosition)
        val trumpText = card.findViewById<TextView>(R.id.matchItemTrump)
        val scoreText = card.findViewById<TextView>(R.id.matchItemScore)
        val winnerText = card.findViewById<TextView>(R.id.matchItemWinner)
        val handText = card.findViewById<TextView>(R.id.matchItemHand)

        // Format game id — truncate to keep it tidy
        val gameId = entry.gameId ?: "N/A"
        val shortGameId = if (gameId.length > 18) gameId.take(15) + "…" else gameId
        gameIdText.text = "Jogo: $shortGameId"

        positionText.text = "Posição: ${entry.position?.uppercase() ?: "?"}"

        val trumpDisplay = trumpSuitDisplay(entry.trumpSuit)
        trumpText.text = "Trunfo: $trumpDisplay"

        val stats = entry.gameStats
        if (stats != null) {
            scoreText.text = "Pontuação: ${stats.team1Points} — ${stats.team2Points}"
            val winnerStr = formatWinner(stats.winner)
            winnerText.text = "Vencedor: $winnerStr"
            winnerText.setTextColor(winnerColor(stats.winner))
        } else {
            scoreText.text = "Pontuação: —"
            winnerText.text = "Vencedor: —"
        }

        val hand = entry.startingHand
        handText.text = if (!hand.isNullOrEmpty()) {
            "Mão inicial: ${hand.joinToString(", ")}"
        } else {
            "Mão inicial: —"
        }

        return card
    }

    private fun trumpSuitDisplay(suit: String?): String {
        return when (suit?.lowercase()) {
            "hearts"   -> "♥ Copas"
            "diamonds" -> "♦ Ouros"
            "clubs"    -> "♣ Paus"
            "spades"   -> "♠ Espadas"
            else       -> suit?.replaceFirstChar { it.uppercase() } ?: "?"
        }
    }

    private fun formatWinner(winner: String?): String {
        return when (winner?.lowercase()) {
            "team1"  -> "Equipa 1"
            "team2"  -> "Equipa 2"
            "draw"   -> "Empate"
            else     -> winner?.replaceFirstChar { it.uppercase() } ?: "?"
        }
    }

    private fun winnerColor(winner: String?): Int {
        return when (winner?.lowercase()) {
            "team1"  -> getColor(R.color.teal_700)
            "team2"  -> getColor(R.color.badge_red)
            else     -> android.graphics.Color.WHITE
        }
    }
}
