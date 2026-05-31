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

class RegisterActivity : AppCompatActivity() {

    private lateinit var usernameEditText: EditText
    private lateinit var emailEditText: EditText
    private lateinit var passwordEditText: EditText
    private lateinit var confirmPasswordEditText: EditText
    private lateinit var registerButton: Button
    private lateinit var loginLink: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_register)

        usernameEditText = findViewById(R.id.usernameEditText)
        emailEditText = findViewById(R.id.emailEditText)
        passwordEditText = findViewById(R.id.passwordEditText)
        confirmPasswordEditText = findViewById(R.id.confirmPasswordEditText)
        registerButton = findViewById(R.id.registerButton)
        loginLink = findViewById(R.id.loginLink)

        registerButton.setOnClickListener {
            val username = usernameEditText.text.toString().trim()
            val email = emailEditText.text.toString().trim()
            val password = passwordEditText.text.toString().trim()
            val confirmPassword = confirmPasswordEditText.text.toString().trim()

            var hasError = false
            if (username.isEmpty()) {
                usernameEditText.error = "O nome de utilizador é obrigatório."
                LogUtils.w("Validation Error (Register): Nome de utilizador vazio.")
                hasError = true
            }
            if (email.isEmpty()) {
                emailEditText.error = "O endereço de email é obrigatório."
                LogUtils.w("Validation Error (Register): Email vazio.")
                hasError = true
            } else if (!isValidEmail(email)) {
                emailEditText.error = "Introduz um endereço de email válido."
                LogUtils.w("Validation Error (Register): Formato de email inválido ($email).")
                hasError = true
            }
            if (password.isEmpty()) {
                passwordEditText.error = "A palavra-passe é obrigatória."
                LogUtils.w("Validation Error (Register): Palavra-passe vazia.")
                hasError = true
            } else if (password != confirmPassword) {
                confirmPasswordEditText.error = "As palavras-passe não são iguais."
                LogUtils.w("Validation Error (Register): Passwords não coincidem.")
                hasError = true
            }
            if (hasError) return@setOnClickListener

            performRegister(username, email, password)
        }

        loginLink.setOnClickListener {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }

    private fun isValidEmail(email: String): Boolean {
        return android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()
    }

    private fun performRegister(username: String, email: String, password: String) {
        LogUtils.i("Registration started for user: $username ($email)")
        registerButton.isEnabled = false
        lifecycleScope.launch {
            AuthManager.register(username, email, password)
                .onSuccess { verificationId ->
                    LogUtils.i("Registo inicial com sucesso. Codigo enviado para $email")
                    val intent = Intent(this@RegisterActivity, VerifyEmailActivity::class.java)
                    intent.putExtra("verificationId", verificationId)
                    intent.putExtra("email", email)
                    startActivity(intent)
                    finish()
                }
                .onFailure { error ->
                    registerButton.isEnabled = true
                    ErrorDialogUtils.showApiError(this@RegisterActivity, error)
                    LogUtils.e("Registration failed: ${error.message}", error)
                }
        }
    }
}
