package com.example.MVP

import android.os.Bundle
import android.graphics.Color
import android.graphics.PorterDuff
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.graphics.toColorInt
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.MVP.models.Card
import com.example.MVP.utils.CardMapper

class GameMvp2MockActivity : AppCompatActivity() {

    private lateinit var slotPlayer: FrameLayout
    private lateinit var handRecycler: RecyclerView
    private lateinit var mockHandAdapter: MockHandAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_game_mvp_2)

        setupStaticUi()
        setupMockTable()
        setupMockHand()
    }

    private fun setupStaticUi() {
        findViewById<ImageView>(R.id.backButton).setOnClickListener {
            AlertDialog.Builder(this)
                .setMessage("Desistir do jogo?")
                .setPositiveButton("Sim") { _, _ -> finish() }
                .setNegativeButton("Nao", null)
                .show()
        }

        slotPlayer = findViewById(R.id.slotPlayer)
        handRecycler = findViewById(R.id.playerHandRecyclerView)

        findViewById<TextView>(R.id.txtPhase).text = "Ronda x"
        findViewById<TextView>(R.id.txtRound).apply {
            visibility = TextView.GONE
        }
        findViewById<TextView>(R.id.txtTrump).apply {
            visibility = TextView.GONE
        }
        findViewById<TextView>(R.id.txtTeamScores).apply {
            val label = "Pontuacao "
            val ns = "63"
            val sep = "  -  "
            val ew = "47"
            val line = label + ns + sep + ew
            text = SpannableStringBuilder(line).apply {
                setSpan(
                    ForegroundColorSpan("#FFFFFF".toColorInt()),
                    0,
                    label.length,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                setSpan(
                    ForegroundColorSpan("#FFD166".toColorInt()),
                    label.length,
                    label.length + ns.length,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
                setSpan(
                    ForegroundColorSpan("#D7DCE3".toColorInt()),
                    label.length + ns.length + sep.length,
                    line.length,
                    Spanned.SPAN_EXCLUSIVE_EXCLUSIVE
                )
            }
            visibility = TextView.VISIBLE
        }
        findViewById<TextView>(R.id.txtCurrentPlayer).apply {
            text = "Vez: Benedita (Esquerda)"
            visibility = TextView.VISIBLE
        }
        findViewById<TextView>(R.id.txtStatus).text = "Dados que vao acontecendo"

        findViewById<TextView>(R.id.slotPartnerName).text = "Joaquim"
        findViewById<TextView>(R.id.slotLeftName).text = "Benedita"
        findViewById<TextView>(R.id.slotRightName).text = "Teotónio"

        findViewById<LinearLayout>(R.id.layoutActions).removeAllViews()
    }

    private fun setupMockTable() {
        val slotPartner = findViewById<FrameLayout>(R.id.slotPartner)
        val slotLeft = findViewById<FrameLayout>(R.id.slotLeft)
        val slotRight = findViewById<FrameLayout>(R.id.slotRight)
        val slotPlayer = findViewById<FrameLayout>(R.id.slotPlayer)

        addCardToSlot(slotPartner, 18) // hearts_7
        addCardToSlot(slotLeft, 36) // spades_7
        addCardToSlot(slotRight, 11) // diamonds_3
        addCardToSlot(slotPlayer, 29) // hearts_ace
        showSingleTrumpOwner(ownerRelative = 0, cardId = 24)
    }

    private fun showSingleTrumpOwner(ownerRelative: Int, cardId: Int) {
        val slotTrump = findViewById<FrameLayout>(R.id.slotTrump)
        val slotTrumpPartner = findViewById<FrameLayout>(R.id.slotTrumpPartner)
        val slotTrumpLeft = findViewById<FrameLayout>(R.id.slotTrumpLeft)
        val slotTrumpRight = findViewById<FrameLayout>(R.id.slotTrumpRight)

        val labelPlayer = findViewById<TextView>(R.id.slotTrumpPlayerLabel)
        val labelPartner = findViewById<TextView>(R.id.slotTrumpPartnerLabel)
        val labelLeft = findViewById<TextView>(R.id.slotTrumpLeftLabel)
        val labelRight = findViewById<TextView>(R.id.slotTrumpRightLabel)

        listOf(slotTrump, slotTrumpPartner, slotTrumpLeft, slotTrumpRight).forEach { it.removeAllViews() }
        listOf(labelPlayer, labelPartner, labelLeft, labelRight).forEach { it.visibility = View.GONE }

        when (ownerRelative) {
            0 -> {
                addTrumpCornerToSlot(slotTrump, cardId)
                labelPlayer.visibility = View.VISIBLE
            }

            1 -> {
                addTrumpCornerToSlot(slotTrumpLeft, cardId)
                labelLeft.visibility = View.VISIBLE
            }

            2 -> {
                addTrumpCornerToSlot(slotTrumpPartner, cardId)
                labelPartner.visibility = View.VISIBLE
            }

            3 -> {
                addTrumpCornerToSlot(slotTrumpRight, cardId)
                labelRight.visibility = View.VISIBLE
            }
        }
    }

    private fun setupMockHand() {
        handRecycler.layoutManager = object :
            LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false) {
            override fun canScrollHorizontally(): Boolean = false
        }
        handRecycler.setHasFixedSize(true)
        handRecycler.itemAnimator = null
        handRecycler.overScrollMode = View.OVER_SCROLL_NEVER
        handRecycler.setPadding(4, 0, 4, 0)
        handRecycler.clipToPadding = false
        handRecycler.clipChildren = false
        (handRecycler.parent as? ViewGroup)?.clipChildren = false
        (handRecycler.parent as? ViewGroup)?.clipToPadding = false

        val mockCards = listOf(0, 3, 7, 9, 12, 17, 21, 26, 33, 39).map { cardId ->
            Card(
                id = cardId.toString(),
                suit = CardMapper.getCardSuitName(cardId),
                value = CardMapper.getCardRankName(cardId)
            )
        }.toMutableList()

        mockHandAdapter = MockHandAdapter(
            cards = mockCards,
            onCardPlayed = { playedCard ->
                val id = playedCard.id.toIntOrNull() ?: return@MockHandAdapter
                addCardToSlot(slotPlayer, id)
                findViewById<TextView>(R.id.txtStatus).text = "Jogaste ${CardMapper.getCard(id)}"
            }
        )

        handRecycler.adapter = mockHandAdapter
        handRecycler.post {
            mockHandAdapter.setAvailableWidth(handRecycler.width - handRecycler.paddingStart - handRecycler.paddingEnd)
        }
    }

    private fun addCardToSlot(slot: FrameLayout, cardId: Int) {
        val view = LayoutInflater.from(this).inflate(R.layout.item_card_mvp, slot, false)
        val image = view.findViewById<ImageView>(R.id.cardImage)

        val drawableName = CardMapper.getDrawableName(cardId)
        val resourceId = resources.getIdentifier(drawableName, "drawable", packageName)
        image.setImageResource(if (resourceId != 0) resourceId else R.drawable.card_back)

        slot.removeAllViews()
        slot.addView(view)
    }

    private fun addTrumpCornerToSlot(slot: FrameLayout, cardId: Int) {
        val drawableName = CardMapper.getDrawableName(cardId)
        val resourceId = resources.getIdentifier(drawableName, "drawable", packageName)

        val image = ImageView(this)
        image.setImageResource(if (resourceId != 0) resourceId else R.drawable.card_back)
        image.scaleType = ImageView.ScaleType.FIT_XY

        val slotWidth = slot.layoutParams?.width?.takeIf { it > 0 } ?: dp(35)
        val slotHeight = slot.layoutParams?.height?.takeIf { it > 0 } ?: dp(72)

        // Keep strong zoom, but lock to top-left so only the card corner is visible.
        val imageWidth = (slotWidth * 5f).toInt()
        val imageHeight = (slotHeight * 4f).toInt()

        val imageParams = FrameLayout.LayoutParams(imageWidth, imageHeight).apply {
            gravity = Gravity.TOP or Gravity.START
        }
        image.layoutParams = imageParams

        image.translationX = 0f
        image.translationY = 0f

        slot.removeAllViews()
        slot.setPadding(0, 0, 0, 0)
        slot.clipToPadding = true
        slot.clipChildren = true
        slot.background = null
        slot.addView(image)
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    private class MockHandAdapter(
        private val cards: MutableList<Card>,
        private val onCardPlayed: (Card) -> Unit
    ) : RecyclerView.Adapter<MockHandAdapter.MockCardViewHolder>() {

        private var selectedPosition: Int = RecyclerView.NO_POSITION
        private var availableWidthPx: Int = 0

        class MockCardViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val cardImage: ImageView = view.findViewById(R.id.cardImage)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): MockCardViewHolder {
            val view = LayoutInflater.from(parent.context)
                .inflate(R.layout.item_card_mvp, parent, false)
            return MockCardViewHolder(view)
        }

        override fun onBindViewHolder(holder: MockCardViewHolder, position: Int) {
            val card = cards[position]
            val resId = getCardResource(holder.itemView, card)
            holder.cardImage.setImageResource(resId)

            val params = holder.itemView.layoutParams as RecyclerView.LayoutParams
            val cardWidth = dp(holder.itemView, 60)
            params.width = cardWidth
            params.height = dp(holder.itemView, 90)
            val minOverlap = dp(holder.itemView, 8)
            val step = if (itemCount > 1 && availableWidthPx > cardWidth) {
                ((availableWidthPx - cardWidth) / (itemCount - 1)).coerceIn(1, cardWidth - minOverlap)
            } else {
                cardWidth - dp(holder.itemView, 30)
            }
            val overlap = (cardWidth - step).coerceAtLeast(minOverlap)
            params.marginStart = if (position == 0) 0 else -overlap
            params.leftMargin = if (position == 0) 0 else -overlap
            params.marginEnd = 0
            params.rightMargin = 0
            params.topMargin = 0
            params.bottomMargin = 0
            holder.itemView.layoutParams = params

            val isSelected = position == selectedPosition
            val hasSelection = selectedPosition != RecyclerView.NO_POSITION
            holder.itemView.rotation = 0f
            holder.itemView.translationY = if (isSelected) -18f else 0f
            holder.itemView.elevation = if (isSelected) dp(holder.itemView, 16).toFloat() else 0f
            holder.itemView.scaleX = if (isSelected) 1.03f else 1f
            holder.itemView.scaleY = if (isSelected) 1.03f else 1f

            if (hasSelection && !isSelected) {
                holder.itemView.alpha = 0.62f
                holder.cardImage.setColorFilter(Color.argb(125, 0, 0, 0), PorterDuff.Mode.SRC_ATOP)
            } else {
                holder.itemView.alpha = 1f
                holder.cardImage.clearColorFilter()
            }

            holder.itemView.setOnClickListener {
                val currentPos = holder.bindingAdapterPosition
                if (currentPos == RecyclerView.NO_POSITION) return@setOnClickListener

                if (currentPos == selectedPosition) {
                    val played = cards.removeAt(currentPos)
                    selectedPosition = RecyclerView.NO_POSITION
                    notifyDataSetChanged()
                    onCardPlayed(played)
                } else {
                    val previous = selectedPosition
                    selectedPosition = currentPos
                    if (previous != RecyclerView.NO_POSITION) {
                        notifyItemChanged(previous)
                        notifyItemChanged(currentPos)
                    }
                    // First selection must refresh whole hand so every non-selected card darkens.
                    if (previous == RecyclerView.NO_POSITION) {
                        notifyDataSetChanged()
                    }
                }
            }
        }

        override fun getItemCount(): Int = cards.size

        fun setAvailableWidth(widthPx: Int) {
            if (widthPx <= 0) return
            availableWidthPx = widthPx
            notifyDataSetChanged()
        }

        private fun getCardResource(view: View, card: Card): Int {
            val context = view.context
            val suit = card.suit.lowercase()
            val value = when (val v = card.value.lowercase()) {
                "k" -> "king"
                "q" -> "queen"
                "j" -> "jack"
                "a" -> "ace"
                else -> v
            }
            val identifier = "${suit}_$value"
            val resId = context.resources.getIdentifier(identifier, "drawable", context.packageName)
            return if (resId != 0) resId else R.drawable.card_back
        }

        private fun dp(view: View, value: Int): Int {
            return (value * view.resources.displayMetrics.density).toInt()
        }
    }
}
