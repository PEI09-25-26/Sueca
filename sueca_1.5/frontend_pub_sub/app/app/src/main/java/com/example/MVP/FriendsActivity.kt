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
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.example.MVP.models.IncomingFriendRequestData
import com.example.MVP.models.UserData
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
    private var lastRefreshAt: Long = 0L

    companion object {
        private const val REFRESH_INTERVAL_MS = 5_000L
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
                Toast.makeText(this, "Insere o codigo de amigo", Toast.LENGTH_SHORT).show()
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
                    Toast.makeText(this@FriendsActivity, "Pedido enviado", Toast.LENGTH_SHORT).show()
                    loadPendingRequests()
                }
                .onFailure { error ->
                    Toast.makeText(
                        this@FriendsActivity,
                        "Erro a enviar pedido: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
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
                Toast.makeText(
                    this@FriendsActivity,
                    if (accept) "Pedido aceite" else "Pedido recusado",
                    Toast.LENGTH_SHORT
                ).show()
                loadPendingRequests()
                loadFriends()
            }.onFailure { error ->
                Toast.makeText(
                    this@FriendsActivity,
                    "Erro: ${error.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }

    private fun loadFriends() {
        val uid = AuthManager.getUid()
        if (uid == null) {
            Toast.makeText(this, "User not logged in", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            FriendsManager.listFriends(uid).onSuccess { friendsList ->
                friends = friendsList
                adapter = FriendsAdapter(this@FriendsActivity, friendsList)
                friendsListView.adapter = adapter
                adapter.notifyDataSetChanged()
            }.onFailure { error ->
                Toast.makeText(
                    this@FriendsActivity,
                    "Error loading friends: ${error.message}",
                    Toast.LENGTH_SHORT
                ).show()
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
                Toast.makeText(this@FriendsActivity, "Nao foi possivel carregar o perfil.", Toast.LENGTH_SHORT).show()
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
        winsView.text = "Vitorias: x"
        winrateView.text = "Win Rate: x%"
        gamesView.text = "Jogos Totais: x"
        streakView.text = "Streak de Vitorias: x"
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
                            Toast.makeText(this@FriendsActivity, "Amigo removido", Toast.LENGTH_SHORT).show()
                            loadFriends()
                            dialog.dismiss()
                        }
                        .onFailure { error ->
                            Toast.makeText(this@FriendsActivity, "Erro ao remover amigo: ${error.message}", Toast.LENGTH_SHORT).show()
                        }
                }
            }
        }

        dialog.show()
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
            val now = System.currentTimeMillis()
            if ((now - lastRefreshAt) < REFRESH_INTERVAL_MS) {
                return
            }
            lastRefreshAt = now
            loadFriends()
            loadPendingRequests()
            
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

    private fun showCreateAccountPrompt() {
        AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle("Criar conta")
            .setMessage("Para aceder aos amigos precisas de criar ou iniciar conta.")
            .setPositiveButton("Registar") { _, _ ->
                startActivity(Intent(this, RegisterActivity::class.java))
                finish()
            }
            .setNegativeButton("Login") { _, _ ->
                startActivity(Intent(this, LoginActivity::class.java))
                finish()
            }
            .setCancelable(false)
            .show()
    }
}
