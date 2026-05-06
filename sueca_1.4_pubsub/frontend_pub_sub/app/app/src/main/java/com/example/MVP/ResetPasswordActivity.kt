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

class ResetPasswordActivity : AppCompatActivity() {

    private lateinit var subtitleTextView: TextView
    private lateinit var codeEditText: EditText
    private lateinit var newPasswordEditText: EditText
    private lateinit var confirmPasswordEditText: EditText
    private lateinit var resetButton: Button
    private lateinit var backToLoginLink: TextView

    private var verificationId: String = ""
    private var email: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_reset_password)

        verificationId = intent.getStringExtra("verificationId") ?: ""
        email = intent.getStringExtra("email") ?: ""

        if (verificationId.isBlank()) {
            Toast.makeText(this, "Pedido de recuperacao invalido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        subtitleTextView = findViewById(R.id.resetPasswordSubtitle)
        codeEditText = findViewById(R.id.resetCodeEditText)
        newPasswordEditText = findViewById(R.id.newPasswordEditText)
        confirmPasswordEditText = findViewById(R.id.confirmPasswordEditText)
        resetButton = findViewById(R.id.resetPasswordButton)
        backToLoginLink = findViewById(R.id.resetBackToLoginLink)

        subtitleTextView.text = "Introduz o codigo enviado para $email"

        resetButton.setOnClickListener {
            val code = codeEditText.text.toString().trim()
            val newPassword = newPasswordEditText.text.toString().trim()
            val confirmPassword = confirmPasswordEditText.text.toString().trim()

            if (!code.matches(Regex("^\\d{6}$"))) {
                Toast.makeText(this, "Codigo deve ter 6 digitos", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (newPassword.isBlank()) {
                Toast.makeText(this, "Insere a nova password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (newPassword != confirmPassword) {
                Toast.makeText(this, "As passwords nao coincidem", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            resetPassword(code, newPassword)
        }

        backToLoginLink.setOnClickListener {
            finish()
        }
    }

    private fun resetPassword(code: String, newPassword: String) {
        resetButton.isEnabled = false
        lifecycleScope.launch {
            AuthManager.resetPassword(verificationId, code, newPassword)
                .onSuccess {
                    Toast.makeText(
                        this@ResetPasswordActivity,
                        "Password atualizada com sucesso",
                        Toast.LENGTH_SHORT
                    ).show()
                    val intent = Intent(this@ResetPasswordActivity, LoginActivity::class.java)
                    intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                    startActivity(intent)
                    finish()
                }
                .onFailure { error ->
                    resetButton.isEnabled = true
                    Toast.makeText(
                        this@ResetPasswordActivity,
                        "Nao foi possivel atualizar a password: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }
}
