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
            val intent = Intent(this, ProfileActivity::class.java)
            intent.putExtra(ProfileActivity.EXTRA_PROFILE_UID, friend.uid)
            startActivity(intent)
        }

        addFriendInput = findViewById(R.id.input_add_friend)
        addFriendButton = findViewById(R.id.button_add_friend)

        friendRequestsContainer = findViewById<LinearLayout>(R.id.friend_requests_container)
        txtNoRequests = findViewById(R.id.txt_no_requests)

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
            
            btnAccept.setOnClickListener { respondToRequest(request.id, true) }
            btnReject.setOnClickListener { respondToRequest(request.id, false) }
            
            // Optionally load profile pic if available in future
            profileImg.setImageResource(R.drawable.profile_pic1)

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
