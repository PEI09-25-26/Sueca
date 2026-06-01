package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.MVP.utils.ErrorDialogUtils
import com.example.MVP.utils.LogUtils
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

            var hasError = false
            if (username.isEmpty()) {
                usernameEditText.error = "Por favor, introduz o teu nome de utilizador."
                LogUtils.w("Validation Error (Login): Nome de utilizador vazio.")
                hasError = true
            }
            if (password.isEmpty()) {
                passwordEditText.error = "A palavra-passe é obrigatória."
                LogUtils.w("Validation Error (Login): Palavra-passe vazia.")
                hasError = true
            }

            if (hasError) return@setOnClickListener

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
            startActivity(Intent(this, MainMenuActivity::class.java))
            finish()
        }
    }

    private fun performLogin(username: String, password: String) {
        loginButton.isEnabled = false
        lifecycleScope.launch {
            AuthManager.login(username, password)
                .onSuccess { user ->
                    LogUtils.i("Login successful for user: ${user.username} (UID: ${user.uid})")
                    startActivity(Intent(this@LoginActivity, MainMenuActivity::class.java))
                    finish()
                }
                .onFailure { error ->
                    loginButton.isEnabled = true
                    ErrorDialogUtils.showApiError(this@LoginActivity, error)
                    LogUtils.e("Login failed: ${error.message}", error)
                }
        }
    }
}
