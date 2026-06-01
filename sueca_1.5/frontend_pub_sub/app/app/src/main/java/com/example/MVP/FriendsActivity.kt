package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.example.MVP.models.IncomingFriendRequestData
import com.example.MVP.models.PlayerStatsData
import com.example.MVP.models.UserData
import com.example.MVP.utils.ErrorDialogUtils
import com.example.MVP.utils.LogUtils
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class FriendsActivity : AppCompatActivity() {

    private lateinit var friendsListView: ListView
    private var friends: List<UserData> = emptyList()
    private lateinit var adapter: FriendsAdapter

    private lateinit var addFriendInput: EditText
    private lateinit var addFriendButton: Button

    private lateinit var friendRequestsContainer: LinearLayout
    private lateinit var txtNoRequests: TextView
    private lateinit var txtFriendCode: TextView

    private var pendingRequests: List<IncomingFriendRequestData> = emptyList()
    private var refreshPollingJob: Job? = null

    companion object {
        private const val REFRESH_INTERVAL_MS = 10_000L
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)

        if (!AuthManager.isLoggedIn()) {
            showCreateAccountPrompt()
            return
        }

        setContentView(R.layout.friends)

        val backButton = findViewById<ImageView>(R.id.backButton2)
        backButton.setOnClickListener {
            finish()
        }

        friendsListView = findViewById(R.id.friendsListView)
        val emptyView = findViewById<View>(R.id.emptyViewTextView)
        friendsListView.emptyView = emptyView

        adapter = FriendsAdapter(this, emptyList())
        friendsListView.adapter = adapter
        friendsListView.setOnItemClickListener { _, _, position, _ ->
            val friend = friends.getOrNull(position) ?: return@setOnItemClickListener
            showFriendInfoSheet(friend, request = null, showActions = false)
        }

        addFriendInput = findViewById(R.id.input_add_friend)
        addFriendButton = findViewById(R.id.button_add_friend)

        friendRequestsContainer = findViewById<LinearLayout>(R.id.friend_requests_container)
        txtNoRequests = findViewById(R.id.txt_no_requests)
        txtFriendCode = findViewById(R.id.txt_friend_code)

        addFriendButton.setOnClickListener {
            val friendCode = addFriendInput.text.toString().trim()
            if (friendCode.isBlank()) {
                addFriendInput.error = "Insere o código de amigo."
                LogUtils.w("Insere o codigo de amigo")
                return@setOnClickListener
            }
            sendFriendRequest(friendCode)
        }

    }

    private fun sendFriendRequest(friendCode: String) {
        lifecycleScope.launch {
            FriendsManager.sendFriendRequestByCode(friendCode)
                .onSuccess {
                    addFriendInput.text?.clear()
                    ErrorDialogUtils.showSnackbar(findViewById(android.R.id.content), "Pedido de amizade enviado.")
                    loadPendingRequests()
                }
                .onFailure { error ->
                    val msg = error.message ?: "Erro desconhecido"
                    if (msg.contains("already friends", ignoreCase = true) || msg.contains("já são amigos", ignoreCase = true)) {
                        ErrorDialogUtils.showSnackbar(findViewById(android.R.id.content), "Vocês já são amigos.")
                    } else if (msg.contains("exists", ignoreCase = true)) {
                        ErrorDialogUtils.showSnackbar(findViewById(android.R.id.content), "O pedido de amizade já existe.")
                    } else {
                        ErrorDialogUtils.showApiSnackbar(findViewById(android.R.id.content), error) {
                            sendFriendRequest(friendCode)
                        }
                    }
                }
        }
    }

    private fun loadPendingRequests() {
        val uid = AuthManager.getUid()
        if (uid == null) {
            renderPendingRequests(emptyList())
            return
        }

        lifecycleScope.launch {
            FriendsManager.listIncomingFriendRequests(uid)
                .onSuccess { requests ->
                    pendingRequests = requests
                    renderPendingRequests(requests)
                }
                .onFailure {
                    renderPendingRequests(emptyList())
                }
        }
    }

    private fun renderPendingRequests(requests: List<IncomingFriendRequestData>) {
        friendRequestsContainer.removeAllViews()
        friendRequestsContainer.addView(txtNoRequests)

        if (requests.isEmpty()) {
            txtNoRequests.visibility = View.VISIBLE
            return
        }

        txtNoRequests.visibility = View.GONE

        requests.forEach { request ->
            val itemView = layoutInflater.inflate(R.layout.item_friend_request, friendRequestsContainer, false)
            
            val nameText = itemView.findViewById<TextView>(R.id.request_name)
            val btnAccept = itemView.findViewById<Button>(R.id.accept_request)
            val btnReject = itemView.findViewById<Button>(R.id.reject_request)
            val profileImg = itemView.findViewById<ImageView>(R.id.request_profile_img)

            nameText.text = request.fromUsername.ifBlank { request.fromUid }
            applyPhotoPreview(profileImg, null)

            lifecycleScope.launch {
                val sender = runCatching {
                    AuthManager.getUser(request.fromUid).getOrThrow()
                }.getOrNull()

                if (sender != null) {
                    nameText.text = sender.username
                    applyPhotoPreview(profileImg, sender.photoURL)
                    itemView.contentDescription = "Pedido de amizade de ${sender.username}"
                } else {
                    itemView.contentDescription = "Pedido de amizade de ${request.fromUsername.ifBlank { request.fromUid }}"
                }
            }
            
            btnAccept.setOnClickListener { respondToRequest(request.id, true) }
            btnReject.setOnClickListener { respondToRequest(request.id, false) }
            itemView.setOnClickListener { showRequestInfoSheet(request) }
            profileImg.setOnClickListener { showRequestInfoSheet(request) }
            nameText.setOnClickListener { showRequestInfoSheet(request) }

            friendRequestsContainer.addView(itemView)
        }
    }

    private fun respondToRequest(requestId: String, accept: Boolean) {
        lifecycleScope.launch {
            val result = if (accept) {
                FriendsManager.acceptFriendRequest(requestId)
            } else {
                FriendsManager.declineFriendRequest(requestId)
            }

            result.onSuccess {
                ErrorDialogUtils.showSnackbar(findViewById(android.R.id.content), if (accept) "Pedido de amizade aceite." else "Pedido de amizade recusado.")
                loadPendingRequests()
                loadFriends()
            }.onFailure { error ->
                ErrorDialogUtils.showApiSnackbar(findViewById(android.R.id.content), error) {
                    respondToRequest(requestId, accept)
                }
            }
        }
    }

    private fun loadFriends() {
        val uid = AuthManager.getUid()
        if (uid == null) {
            LogUtils.e("User not logged in while loading friends")
            return
        }

        lifecycleScope.launch {
            FriendsManager.listFriends(uid).onSuccess { friendsList ->
                friends = friendsList
                adapter = FriendsAdapter(this@FriendsActivity, friendsList)
                friendsListView.adapter = adapter
                adapter.notifyDataSetChanged()
            }.onFailure { error ->
                LogUtils.e("Error loading friends: ${error.message}", error)
            }
        }
    }

    private fun showRequestInfoSheet(request: IncomingFriendRequestData) {
        lifecycleScope.launch {
            val friend = runCatching {
                AuthManager.getUser(request.fromUid).getOrThrow()
            }.getOrNull()

            if (friend != null) {
                showFriendInfoSheet(friend, request, showActions = true)
            } else {
                LogUtils.e("Nao foi possivel carregar o perfil.")
            }
        }
    }

    private fun showFriendInfoSheet(friend: UserData, request: IncomingFriendRequestData?, showActions: Boolean) {
        val dialog = BottomSheetDialog(this)
        val contentView = layoutInflater.inflate(R.layout.bottom_sheet_friend_info, null)
        dialog.setContentView(contentView)

        val bannerView = contentView.findViewById<ImageView>(R.id.friend_info_banner)
        val avatarView = contentView.findViewById<ImageView>(R.id.friend_info_avatar)
        val statusView = contentView.findViewById<View>(R.id.friend_info_status)
        val usernameView = contentView.findViewById<TextView>(R.id.friend_info_username)
        val descriptionView = contentView.findViewById<TextView>(R.id.friend_info_description)
        val winsView = contentView.findViewById<TextView>(R.id.friend_info_stat_wins)
        val winrateView = contentView.findViewById<TextView>(R.id.friend_info_stat_winrate)
        val gamesView = contentView.findViewById<TextView>(R.id.friend_info_stat_total_games)
        val streakView = contentView.findViewById<TextView>(R.id.friend_info_stat_streak)
        val friendsCountView = contentView.findViewById<TextView>(R.id.friend_info_stat_friend_count)
        
        val actionRow = contentView.findViewById<View>(R.id.friend_info_action_row)
        val acceptButton = contentView.findViewById<Button>(R.id.friend_info_accept)
        val rejectButton = contentView.findViewById<Button>(R.id.friend_info_reject)
        val removeFriendButton = contentView.findViewById<Button>(R.id.friend_info_remove_friend)

        applyBannerPreview(bannerView, friend.bannerURL)
        applyPhotoPreview(avatarView, friend.photoURL)
        statusView.setBackgroundResource(
            if (friend.status == "online") R.drawable.status_indicator_online else R.drawable.status_indicator_offline
        )

        usernameView.text = friend.username
        descriptionView.text = friend.description.ifBlank { "Sem descricao disponivel." }
        applyFriendStats(friend.stats, winsView, winrateView, gamesView, streakView)
        friendsCountView.text = "Amigos: ${friend.friendsCount}"

        if (showActions && request != null) {
            actionRow.visibility = View.VISIBLE
            removeFriendButton.visibility = View.GONE
            acceptButton.setOnClickListener {
                respondToRequest(request.id, true)
                dialog.dismiss()
            }
            rejectButton.setOnClickListener {
                respondToRequest(request.id, false)
                dialog.dismiss()
            }
        } else {
            actionRow.visibility = View.GONE
            removeFriendButton.visibility = View.VISIBLE
            removeFriendButton.setOnClickListener {
                lifecycleScope.launch {
                    FriendsManager.removeFriend(friend.uid)
                        .onSuccess {
                            ErrorDialogUtils.showSnackbar(findViewById(android.R.id.content), "Amigo removido.")
                            loadFriends()
                            dialog.dismiss()
                        }
                        .onFailure { error ->
                            ErrorDialogUtils.showApiSnackbar(findViewById(android.R.id.content), error) {
                                removeFriendButton.performClick()
                            }
                        }
                }
            }
        }

        dialog.show()
    }

    private fun applyFriendStats(
        stats: PlayerStatsData?,
        winsView: TextView,
        winrateView: TextView,
        gamesView: TextView,
        streakView: TextView
    ) {
        val wins = stats?.wins ?: 0
        val losses = stats?.losses ?: 0
        val draws = stats?.draws ?: 0
        val gamesPlayed = stats?.gamesPlayed ?: (wins + losses + draws)
        val winrate = if (gamesPlayed > 0) ((wins * 100.0) / gamesPlayed).toInt() else 0

        winsView.text = "Vitorias: $wins"
        winrateView.text = "Win Rate: $winrate%"
        gamesView.text = "Jogos Totais: $gamesPlayed"
        streakView.text = "Empates: $draws"
    }

    private fun applyBannerPreview(imageView: ImageView, bannerKey: String?) {
        when (bannerKey) {
            "banner_red" -> imageView.setImageResource(R.drawable.banner_red)
            "banner_blue" -> imageView.setImageResource(R.drawable.banner_blue)
            "banner_green" -> imageView.setImageResource(R.drawable.banner_green)
            "banner_purple" -> imageView.setImageResource(R.drawable.banner_purple)
            "banner_orange" -> imageView.setImageResource(R.drawable.banner_orange)
            "banner_pink" -> imageView.setImageResource(R.drawable.banner_pink)
            "banner_teal" -> imageView.setImageResource(R.drawable.banner_teal)
            "banner_gold" -> imageView.setImageResource(R.drawable.banner_gold)
            "banner_rose" -> imageView.setImageResource(R.drawable.banner_rose)
            "banner_slate" -> imageView.setImageResource(R.drawable.banner_slate)
            else -> imageView.setImageResource(R.drawable.banner_background)
        }
    }

    private fun applyPhotoPreview(imageView: ImageView, photoKey: String?) {
        when (photoKey) {
            "profile_pic1" -> imageView.setImageResource(R.drawable.profile_pic1)
            "profile_pic2" -> imageView.setImageResource(R.drawable.profile_pic2)
            "profile_pic3" -> imageView.setImageResource(R.drawable.profile_pic3)
            "profile_pic4" -> imageView.setImageResource(R.drawable.profile_pic4)
            "profile_pic5" -> imageView.setImageResource(R.drawable.profile_pic5)
            else -> imageView.setImageResource(R.drawable.sueca)
        }
    }

    override fun onResume() {
        super.onResume()
        if (AuthManager.isLoggedIn()) {
            loadFriends()
            loadPendingRequests()
            startPolling()
            
            val savedCode = AuthManager.getSavedFriendCode()
            if (savedCode != null) {
                txtFriendCode.text = savedCode
            } else {
                lifecycleScope.launch {
                    FriendsManager.getFriendCode().onSuccess { response ->
                        txtFriendCode.text = response.code
                        AuthManager.saveFriendCode(response.code)
                    }
                }
            }
        }
    }

    override fun onPause() {
        super.onPause()
        stopPolling()
    }

    private fun startPolling() {
        if (refreshPollingJob != null) return
        refreshPollingJob = lifecycleScope.launch {
            while (true) {
                delay(REFRESH_INTERVAL_MS)
                loadFriends()
                loadPendingRequests()
            }
        }
    }

    private fun stopPolling() {
        refreshPollingJob?.cancel()
        refreshPollingJob = null
    }

    private fun showCreateAccountPrompt() {
        com.example.MVP.utils.showCustomConfirmDialog(
            context = this,
            title = "Criar conta",
            message = "Para aceder aos amigos precisas de criar ou iniciar conta.",
            positiveText = "REGISTAR",
            negativeText = "LOGIN",
            onConfirm = {
                startActivity(Intent(this, RegisterActivity::class.java))
                finish()
            },
            onCancel = {
                startActivity(Intent(this, LoginActivity::class.java))
                finish()
            }
        )
    }
}
