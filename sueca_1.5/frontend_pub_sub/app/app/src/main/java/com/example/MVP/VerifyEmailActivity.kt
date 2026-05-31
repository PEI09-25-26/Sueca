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
            LogUtils.e("Pedido de verificacao invalido")
            finish()
            return
        }

        subtitleTextView = findViewById(R.id.verifyEmailSubtitle)
        codeEditText = findViewById(R.id.verificationCodeEditText)
        verifyButton = findViewById(R.id.verifyEmailButton)

        subtitleTextView.text = "Introduz o codigo enviado para $email"

        verifyButton.setOnClickListener {
            val code = codeEditText.text.toString().trim()
            if (!code.matches(Regex("^\\d{6}$"))) {
                codeEditText.error = "O código deve ter exatamente 6 dígitos."
                LogUtils.w("Validation Error (VerifyEmail): Código inválido ($code).")
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
                    LogUtils.i("Email verified successfully for user: ${user.username}")
                    startActivity(Intent(this@VerifyEmailActivity, MainMenuActivity::class.java))
                    finish()
                }
                .onFailure { error ->
                    verifyButton.isEnabled = true
                    ErrorDialogUtils.showApiError(this@VerifyEmailActivity, error)
                    LogUtils.e("Verificacao falhou: ${error.message}", error)
                }
        }
    }
}
