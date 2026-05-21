package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {

    private lateinit var usernameEditText: EditText
    private lateinit var passwordEditText: EditText
    private lateinit var loginButton: Button
    private lateinit var forgotPasswordLink: TextView
    private lateinit var registerLink: TextView
    private lateinit var anonymousLink: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_login)

        // Auto-skip login only for authenticated accounts.
        // Anonymous users must stay on this screen so they can upgrade to a real account.
        if (AuthManager.isLoggedIn()) {
            startActivity(Intent(this, MainMenuActivity::class.java))
            finish()
            return
        }

        usernameEditText = findViewById(R.id.usernameEditText)
        passwordEditText = findViewById(R.id.passwordEditText)
        loginButton = findViewById(R.id.loginButton)
        forgotPasswordLink = findViewById(R.id.forgotPasswordLink)
        registerLink = findViewById(R.id.registerLink)
        anonymousLink = findViewById(R.id.anonymousLink)

        loginButton.setOnClickListener {
            val username = usernameEditText.text.toString().trim()
            val password = passwordEditText.text.toString().trim()

            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please fill in all fields", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            performLogin(username, password)
        }

        registerLink.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
        }

        forgotPasswordLink.setOnClickListener {
            startActivity(Intent(this, RecoverPasswordActivity::class.java))
        }

        anonymousLink.setOnClickListener {
            AuthManager.startAnonymousSession()
            Toast.makeText(this, "Entraste como anonimo", Toast.LENGTH_SHORT).show()
            startActivity(Intent(this, MainMenuActivity::class.java))
            finish()
        }
    }

    private fun performLogin(username: String, password: String) {
        loginButton.isEnabled = false
        lifecycleScope.launch {
            AuthManager.login(username, password)
                .onSuccess { user ->
                    Toast.makeText(
                        this@LoginActivity,
                        "Welcome back, ${user.username}!",
                        Toast.LENGTH_SHORT
                    ).show()
                    startActivity(Intent(this@LoginActivity, MainMenuActivity::class.java))
                    finish()
                }
                .onFailure { error ->
                    loginButton.isEnabled = true
                    Toast.makeText(
                        this@LoginActivity,
                        "Login failed: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }
}
