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
import com.example.MVP.models.RoundData
import kotlinx.coroutines.launch
import com.example.MVP.utils.CardMapper

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
        val dateText = card.findViewById<TextView>(R.id.matchItemDate)
        val positionText = card.findViewById<TextView>(R.id.matchItemPosition)
        val trumpText = card.findViewById<TextView>(R.id.matchItemTrump)
        val scoreText = card.findViewById<TextView>(R.id.matchItemScore)
        val winnerText = card.findViewById<TextView>(R.id.matchItemWinner)
        val handText = card.findViewById<TextView>(R.id.matchItemHand)

        // Format game id — truncate to keep it tidy
        val gameId = entry.gameId ?: "N/A"
        val shortGameId = if (gameId.length > 18) gameId.take(15) + "…" else gameId
        gameIdText.text = "Id da Sala: $shortGameId"

        // Parse and format date from "YYYY-MM-DD..." to "DD/MM/YYYY"
        val rawDate = entry.finishedAt?.take(10)
        val formattedDate = if (rawDate != null && rawDate.length == 10) {
            val parts = rawDate.split("-")
            if (parts.size == 3) {
                "${parts[2]}/${parts[1]}/${parts[0]}"
            } else {
                rawDate
            }
        } else {
            "—"
        }
        dateText.text = formattedDate

        val positionDisplay = formatPosition(entry.position)
        positionText.text = "Posição: $positionDisplay"

        val trumpDisplay = trumpSuitDisplay(entry.trumpSuit)
        trumpText.text = "Trunfo: $trumpDisplay"

        val stats = entry.gameStats
        if (stats != null) {
            scoreText.text = "Pontuação: ${stats.team1Points} — ${stats.team2Points}"
            val winnerStr = formatWinner(stats.winner)
            winnerText.text = "Vencedor: $winnerStr"
        } else {
            scoreText.text = "Pontuação: —"
            winnerText.text = "Vencedor: —"
        }

        val hand = entry.startingHand
        handText.text = if (!hand.isNullOrEmpty()) {
            val cardNames = hand.map { cardId ->
                cardId.toIntOrNull()?.let { getDrawableCardName(it) } ?: "?"
            }
            "Mão inicial: \n ${cardNames.joinToString(", ")}"
        } else {
            "Mão inicial: \n —, —, —, —, —, —, —, —, —, —"
        }

        val roundsContainer = card.findViewById<LinearLayout>(R.id.matchItemRoundsContainer)
        val toggleText = card.findViewById<TextView>(R.id.matchItemRoundsToggleText)

        card.setOnClickListener {
            if (roundsContainer.visibility == View.VISIBLE) {
                roundsContainer.visibility = View.GONE
                toggleText.text = "▼ Toque para ver rondas"
            } else {
                roundsContainer.visibility = View.VISIBLE
                toggleText.text = "▲ Toque para ocultar rondas"
                if (roundsContainer.childCount == 0) {
                    populateRoundsContainer(roundsContainer, entry)
                }
            }
        }

        return card
    }

    private fun populateRoundsContainer(container: LinearLayout, entry: MatchHistoryEntry) {
        val roundsMap = entry.rounds
        if (roundsMap.isNullOrEmpty()) {
            val emptyView = TextView(this)
            emptyView.text = "Sem detalhes das rondas disponíveis."
            emptyView.setTextColor(android.graphics.Color.GRAY)
            emptyView.textSize = 13f
            emptyView.gravity = android.view.Gravity.CENTER
            emptyView.setPadding(0, 16, 0, 16)
            container.addView(emptyView)
            return
        }

        // Sort numerical: round_1, round_2, ..., round_10
        val sortedRounds = roundsMap.entries.sortedBy { (key, _) ->
            key.removePrefix("round_").toIntOrNull() ?: 0
        }

        val inflater = layoutInflater
        sortedRounds.forEach { (key, roundData) ->
            val roundView = inflater.inflate(R.layout.item_match_history_round, container, false)

            val roundTitleText = roundView.findViewById<TextView>(R.id.roundItemTitle)
            val leadSuitText = roundView.findViewById<TextView>(R.id.roundItemLeadSuit)
            val playedCardText = roundView.findViewById<TextView>(R.id.roundItemPlayedCard)
            val positionText = roundView.findViewById<TextView>(R.id.roundItemPosition)
            val trickText = roundView.findViewById<TextView>(R.id.roundItemTrick)
            val handText = roundView.findViewById<TextView>(R.id.roundItemHand)

            val roundNumber = key.removePrefix("round_")
            roundTitleText.text = "Ronda $roundNumber"

            val leadSuitDisplay = trumpSuitDisplay(roundData.leadSuit)
            leadSuitText.text = "Saída: $leadSuitDisplay"

            val cardId = roundData.cardPlayed?.toIntOrNull()
            val cardPlayedDisplay = cardId?.let { getDrawableCardName(it) } ?: "—"
            playedCardText.text = "Jogou: $cardPlayedDisplay"

            val pos = roundData.positionInTrick ?: 0
            val posStr = when (pos) {
                1 -> "1º a jogar"
                2 -> "2º a jogar"
                3 -> "3º a jogar"
                4 -> "4º a jogar"
                else -> "Posição: —"
            }
            positionText.text = posStr

            // Format trick play order sequence: Card1 -> Card2 -> Card3 -> Card4
            val trickList = roundData.cardsInTrick
            if (!trickList.isNullOrEmpty()) {
                val trickCardNames = trickList.mapIndexed { index, cardIdStr ->
                    val cId = cardIdStr.toIntOrNull()
                    val cName = cId?.let { getDrawableCardName(it) } ?: "?"
                    val isOurs = (index + 1) == pos
                    if (isOurs) "[$cName]" else cName
                }
                trickText.text = "Vaza: " + trickCardNames.joinToString(" → ")
            } else {
                trickText.text = "Vaza: —"
            }

            // Format starting hand for this round
            val handList = roundData.handBeforePlay
            if (!handList.isNullOrEmpty()) {
                val handCardNames = handList.map { cardIdStr ->
                    val cId = cardIdStr.toIntOrNull()
                    cId?.let { getDrawableCardName(it) } ?: "?"
                }
                handText.text = "Mão antes: " + handCardNames.joinToString(", ")
            } else {
                handText.text = "Mão antes: —"
            }

            container.addView(roundView)
        }
    }

    private fun trumpSuitDisplay(suit: String?): String {
        return when (suit?.lowercase()) {
            "♥"   -> "♥ Copas"
            "♦" -> "♦ Ouros"
            "♣"    -> "♣ Paus"
            "♠"   -> "♠ Espadas"
            else       -> suit?.replaceFirstChar { it.uppercase() } ?: "?"
        }
    }

    private fun formatWinner(winner: String?): String {
        return when (winner?.lowercase()) {
            "team 1 (n/s)"  -> "Equipa 1 (N/S)"
            "team 2 (e/w)"  -> "Equipa 2 (E/O)"
            "draw"   -> "Empate"
            else     -> winner?.replaceFirstChar { it.uppercase() } ?: "?"
        }
    }

    private fun formatPosition(position: String?): String {
        return when (position?.lowercase()) {
            "north" -> "Norte"
            "south" -> "Sul"
            "east"  -> "Este"
            "west"  -> "Oeste"
            else     -> position ?: "?"
        }
    }

    fun getDrawableCardName(cardId: Int): String {
        val suit = CardMapper.getCardSuit(cardId)
        val rank = CardMapper.getCardRank(cardId)
        return "${rank}${suit}"
    }
}
