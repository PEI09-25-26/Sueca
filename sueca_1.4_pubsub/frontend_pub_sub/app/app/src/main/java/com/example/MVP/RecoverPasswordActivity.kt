package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.util.Patterns
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

class RecoverPasswordActivity : AppCompatActivity() {

    private lateinit var emailEditText: EditText
    private lateinit var sendCodeButton: Button
    private lateinit var backToLoginLink: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_recover_password)

        emailEditText = findViewById(R.id.recoverEmailEditText)
        sendCodeButton = findViewById(R.id.sendRecoveryCodeButton)
        backToLoginLink = findViewById(R.id.recoverBackToLoginLink)

        sendCodeButton.setOnClickListener {
            val email = emailEditText.text.toString().trim()
            if (email.isBlank()) {
                Toast.makeText(this, "Insere o email", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                Toast.makeText(this, "Email invalido", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            requestRecoveryCode(email)
        }

        backToLoginLink.setOnClickListener {
            finish()
        }
    }

    private fun requestRecoveryCode(email: String) {
        sendCodeButton.isEnabled = false
        lifecycleScope.launch {
            AuthManager.recoverPassword(email)
                .onSuccess { verificationId ->
                    Toast.makeText(
                        this@RecoverPasswordActivity,
                        "Codigo enviado para o email",
                        Toast.LENGTH_SHORT
                    ).show()
                    val intent = Intent(this@RecoverPasswordActivity, ResetPasswordActivity::class.java)
                    intent.putExtra("verificationId", verificationId)
                    intent.putExtra("email", email)
                    startActivity(intent)
                    finish()
                }
                .onFailure { error ->
                    sendCodeButton.isEnabled = true
                    Toast.makeText(
                        this@RecoverPasswordActivity,
                        "Nao foi possivel enviar o codigo: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }
}
