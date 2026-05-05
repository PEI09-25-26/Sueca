package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
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

    private lateinit var requestCard1: View
    private lateinit var requestCard2: View
    private lateinit var requestName1: TextView
    private lateinit var requestName2: TextView
    private lateinit var acceptRequest1: Button
    private lateinit var acceptRequest2: Button
    private lateinit var rejectRequest1: Button
    private lateinit var rejectRequest2: Button

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

        requestCard1 = findViewById(R.id.request_card_1)
        requestCard2 = findViewById(R.id.request_card_2)
        requestName1 = findViewById(R.id.request_name_1)
        requestName2 = findViewById(R.id.request_name_2)
        acceptRequest1 = findViewById(R.id.accept_request_1)
        acceptRequest2 = findViewById(R.id.accept_request_2)
        rejectRequest1 = findViewById(R.id.reject_request_1)
        rejectRequest2 = findViewById(R.id.reject_request_2)

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
        val req1 = requests.getOrNull(0)
        val req2 = requests.getOrNull(1)

        if (req1 == null) {
            requestCard1.visibility = View.GONE
        } else {
            requestCard1.visibility = View.VISIBLE
            requestName1.text = req1.fromUsername.ifBlank { req1.fromUid }

            acceptRequest1.setOnClickListener { respondToRequest(req1.id, true) }
            rejectRequest1.setOnClickListener { respondToRequest(req1.id, false) }
        }

        if (req2 == null) {
            requestCard2.visibility = View.GONE
        } else {
            requestCard2.visibility = View.VISIBLE
            requestName2.text = req2.fromUsername.ifBlank { req2.fromUid }

            acceptRequest2.setOnClickListener { respondToRequest(req2.id, true) }
            rejectRequest2.setOnClickListener { respondToRequest(req2.id, false) }
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
