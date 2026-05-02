package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import com.google.android.material.button.MaterialButton
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class ProfileActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_PROFILE_UID = "extra_profile_uid"
    }

    private lateinit var bannerImageView: ImageView
    private lateinit var profileImageView: ImageView
    private lateinit var usernameTextView: TextView
    private lateinit var emailTextView: TextView
    private lateinit var descriptionTextView: TextView
    private lateinit var friendsCountTextView: TextView
    private lateinit var statusIndicator: View
    private lateinit var logoutButton: MaterialButton
    private lateinit var editProfileButton: MaterialButton

    private var viewedUid: String? = null
    private var isViewingOwnProfile: Boolean = true

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)

        if (!AuthManager.isLoggedIn()) {
            showCreateAccountPrompt()
            return
        }

        setContentView(R.layout.profile)

        val backButton = findViewById<ImageView>(R.id.backButton3)
        editProfileButton = findViewById(R.id.edit_profile)
        bannerImageView = findViewById(R.id.banner_profile)
        profileImageView = findViewById(R.id.image_profile)
        
        usernameTextView = findViewById(R.id.usernameTextView)
        emailTextView = findViewById(R.id.emailTextView)
        descriptionTextView = findViewById(R.id.descriptionTextView)
        friendsCountTextView = findViewById(R.id.friendsCountTextView)
        statusIndicator = findViewById(R.id.statusIndicator)
        logoutButton = findViewById(R.id.logoutButton)

        val ownUid = AuthManager.getUid()
        viewedUid = intent.getStringExtra(EXTRA_PROFILE_UID) ?: ownUid
        isViewingOwnProfile = viewedUid != null && viewedUid == ownUid

        if (!isViewingOwnProfile) {
            editProfileButton.visibility = View.GONE
            logoutButton.visibility = View.GONE
            emailTextView.visibility = View.GONE
        } else {
            editProfileButton.visibility = View.VISIBLE
            logoutButton.visibility = View.VISIBLE
            emailTextView.visibility = View.VISIBLE
        }

        backButton.setOnClickListener {
            finish()
        }

        editProfileButton.setOnClickListener {
            val intent = Intent(this, EditActivity::class.java)
            startActivity(intent)
        }
        
        logoutButton.setOnClickListener {
            performLogout()
        }
        
    }
    
    private fun loadUserProfile() {
        val uid = viewedUid
        if (uid == null) {
            Toast.makeText(this, "User not logged in", Toast.LENGTH_SHORT).show()
            return
        }
        
        lifecycleScope.launch {
            AuthManager.getUser(uid)
                .onSuccess { user ->
                    usernameTextView.text = "${user.username}"
                    emailTextView.text = "${user.email}"
                    descriptionTextView.text = "${user.description}"
                    friendsCountTextView.text = "Amigos: ${user.friendsCount}"
                    applyBannerPreview(user.bannerURL)
                    applyPhotoPreview(user.photoURL)
                    
                    // Update status indicator based on user's status
                    updateStatusIndicator(user.status)
                }
                .onFailure { error ->
                    Toast.makeText(
                        this@ProfileActivity,
                        "Failed to load profile: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }
    
    private fun updateStatusIndicator(status: String) {
        if (status == "online") {
            statusIndicator.setBackgroundResource(R.drawable.status_indicator_online)
        } else {
            statusIndicator.setBackgroundResource(R.drawable.status_indicator_offline)
        }
    }

    private fun applyBannerPreview(bannerKey: String?) {
        when (bannerKey) {
            "banner_red" -> bannerImageView.setImageResource(R.drawable.banner_red)
            "banner_blue" -> bannerImageView.setImageResource(R.drawable.banner_blue)
            "banner_green" -> bannerImageView.setImageResource(R.drawable.banner_green)
            "banner_purple" -> bannerImageView.setImageResource(R.drawable.banner_purple)
            "banner_orange" -> bannerImageView.setImageResource(R.drawable.banner_orange)
            "banner_pink" -> bannerImageView.setImageResource(R.drawable.banner_pink)
            "banner_teal" -> bannerImageView.setImageResource(R.drawable.banner_teal)
            "banner_gold" -> bannerImageView.setImageResource(R.drawable.banner_gold)
            "banner_rose" -> bannerImageView.setImageResource(R.drawable.banner_rose)
            "banner_slate" -> bannerImageView.setImageResource(R.drawable.banner_slate)
            else -> bannerImageView.setImageResource(R.drawable.banner_background)
        }
    }

    private fun applyPhotoPreview(photoKey: String?) {
        when (photoKey) {
            "profile_pic1" -> profileImageView.setImageResource(R.drawable.profile_pic1)
            "profile_pic2" -> profileImageView.setImageResource(R.drawable.profile_pic2)
            "profile_pic3" -> profileImageView.setImageResource(R.drawable.profile_pic3)
            "profile_pic4" -> profileImageView.setImageResource(R.drawable.profile_pic4)
            "profile_pic5" -> profileImageView.setImageResource(R.drawable.profile_pic5)
            else -> profileImageView.setImageResource(R.drawable.sueca)
        }
    }
    
    private fun performLogout() {
        lifecycleScope.launch {
            AuthManager.logout()
                .onSuccess {
                    Toast.makeText(this@ProfileActivity, "Logged out successfully", Toast.LENGTH_SHORT).show()
                    val intent = Intent(this@ProfileActivity, LoginActivity::class.java)
                    intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK
                    startActivity(intent)
                    finish()
                }
                .onFailure { error ->
                    Toast.makeText(
                        this@ProfileActivity,
                        "Logout failed: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }
    
    override fun onResume() {
        super.onResume()
        if (AuthManager.isLoggedIn() && viewedUid != null) {
            loadUserProfile()
        }
    }

    private fun showCreateAccountPrompt() {
        AlertDialog.Builder(this)
            .setTitle("Criar conta")
            .setMessage("Para aceder ao perfil precisas de criar ou iniciar conta.")
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
