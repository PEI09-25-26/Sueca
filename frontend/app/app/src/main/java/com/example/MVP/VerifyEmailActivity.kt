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

class VerifyEmailActivity : AppCompatActivity() {

    private lateinit var codeEditText: EditText
    private lateinit var verifyButton: Button
    private lateinit var subtitleTextView: TextView

    private var verificationId: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.activity_verify_email)

        verificationId = intent.getStringExtra("verificationId") ?: ""
        val email = intent.getStringExtra("email") ?: ""

        if (verificationId.isBlank()) {
            Toast.makeText(this, "Pedido de verificação inválido", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        subtitleTextView = findViewById(R.id.verifyEmailSubtitle)
        codeEditText = findViewById(R.id.verificationCodeEditText)
        verifyButton = findViewById(R.id.verifyEmailButton)

        subtitleTextView.text = "Introduz o código enviado para $email"

        verifyButton.setOnClickListener {
            val code = codeEditText.text.toString().trim()
            if (!code.matches(Regex("^\\d{6}$"))) {
                Toast.makeText(this, "Código deve ter 6 dígitos", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            verifyCode(code)
        }
    }

    private fun verifyCode(code: String) {
        verifyButton.isEnabled = false
        lifecycleScope.launch {
            AuthManager.verifyEmailCode(verificationId, code)
                .onSuccess { user ->
                    Toast.makeText(
                        this@VerifyEmailActivity,
                        "Email verificado! Bem-vindo, ${user.username}!",
                        Toast.LENGTH_SHORT
                    ).show()
                    startActivity(Intent(this@VerifyEmailActivity, MainMenuActivity::class.java))
                    finish()
                }
                .onFailure { error ->
                    verifyButton.isEnabled = true
                    Toast.makeText(
                        this@VerifyEmailActivity,
                        "Verificação falhou: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }
}
