package com.example.MVP

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import androidx.recyclerview.widget.RecyclerView
import com.example.MVP.models.Card

class CardsAdapter(
    private var cards: List<Card>,
    private val onCardClick: (Card) -> Unit
) : RecyclerView.Adapter<CardsAdapter.CardViewHolder>() {

    private var availableWidthPx: Int = 0

    var isEnabled: Boolean = true
        set(value) {
            field = value
            notifyDataSetChanged()
        }

    class CardViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val cardImage: ImageView = view.findViewById(R.id.cardImage)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): CardViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_card_mvp, parent, false)
        return CardViewHolder(view)
    }

    override fun onBindViewHolder(holder: CardViewHolder, position: Int) {
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
        val startMargin = if (position == 0) 0 else -overlap
        params.marginStart = startMargin
        params.leftMargin = startMargin
        params.marginEnd = 0
        params.rightMargin = 0
        params.topMargin = 0
        params.bottomMargin = 0
        holder.itemView.layoutParams = params
        
        // Visualmente desativar a carta se não for a vez
        holder.itemView.alpha = if (isEnabled) 1.0f else 0.5f
        
        holder.itemView.setOnClickListener {
            if (isEnabled) {
                onCardClick(card)
            }
        }
    }

    override fun getItemCount() = cards.size

    fun updateCards(newCards: List<Card>) {
        cards = newCards
        notifyDataSetChanged()
    }

    fun setAvailableWidth(widthPx: Int) {
        if (widthPx <= 0) return
        availableWidthPx = widthPx
        notifyDataSetChanged()
    }

    fun getCards(): List<Card> = cards

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