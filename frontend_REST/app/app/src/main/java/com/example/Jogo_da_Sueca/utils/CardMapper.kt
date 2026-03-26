package com.example.Jogo_da_Sueca.utils

/**
 * Maps card IDs (0-39) to their corresponding suit and rank.
 * Mirrors the Python CardMapper from server.py
 */
object CardMapper {
    private val SUITS = listOf("♣", "♦", "♥", "♠")
    private val SUIT_NAMES = listOf("clubs", "diamonds", "hearts", "spades")
    private val RANKS = listOf("2", "3", "4", "5", "6", "Q", "J", "K", "7", "A")
    private val RANK_NAMES = mapOf(
        "2" to "2", "3" to "3", "4" to "4", "5" to "5", "6" to "6",
        "Q" to "queen", "J" to "jack", "K" to "king", "7" to "7", "A" to "ace"
    )
    private const val SUIT_SIZE = 10
    
    private val RANK_VALUES = mapOf(
        "2" to 0, "3" to 0, "4" to 0, "5" to 0, "6" to 0,
        "Q" to 2, "J" to 3, "K" to 4, "7" to 10, "A" to 11
    )

    /**
     * Returns a card's suit symbol given its ID (0-39).
     */
    fun getCardSuit(cardId: Int): String {
        val suitIndex = cardId / SUIT_SIZE
        return SUITS.getOrElse(suitIndex) { "?" }
    }

    /**
     * Returns a card's suit name given its ID (0-39).
     * e.g., "hearts", "spades", etc.
     */
    fun getCardSuitName(cardId: Int): String {
        val suitIndex = cardId / SUIT_SIZE
        return SUIT_NAMES.getOrElse(suitIndex) { "unknown" }
    }

    /**
     * Returns a card's rank given its ID (0-39).
     */
    fun getCardRank(cardId: Int): String {
        val rankIndex = cardId % SUIT_SIZE
        return RANKS.getOrElse(rankIndex) { "?" }
    }

    /**
     * Returns a card's rank name given its ID (0-39).
     * e.g., "ace", "king", "queen", "jack", or the number
     */
    fun getCardRankName(cardId: Int): String {
        val rank = getCardRank(cardId)
        return RANK_NAMES[rank] ?: rank
    }

    /**
     * Returns a formatted card string given its ID.
     * e.g., "A♠", "K♥", "7♣"
     */
    fun getCard(cardId: Int): String {
        return "${getCardRank(cardId)}${getCardSuit(cardId)}"
    }

    /**
     * Returns a card's point value given its ID.
     */
    fun getCardPoints(cardId: Int): Int {
        val rank = getCardRank(cardId)
        return RANK_VALUES[rank] ?: 0
    }

    /**
     * Parses a card ID from a string.
     * Returns null if invalid.
     */
    fun parseCardId(cardStr: String): Int? {
        return cardStr.trim().toIntOrNull()
    }

    /**
     * Converts a card ID to a drawable resource name.
     * e.g., cardId 39 -> "spades_ace"
     */
    fun getDrawableName(cardId: Int): String {
        val suitName = getCardSuitName(cardId)
        val rankName = getCardRankName(cardId)
        return "${suitName}_$rankName"
    }
}
