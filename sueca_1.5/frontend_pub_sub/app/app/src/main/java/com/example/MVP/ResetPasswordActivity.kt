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
            LogUtils.e("Pedido de recuperacao invalido")
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

            var hasError = false
            if (!code.matches(Regex("^\\d{6}$"))) {
                codeEditText.error = "O código deve ter exatamente 6 dígitos."
                LogUtils.w("Validation Error (ResetPassword): Código inválido ($code).")
                hasError = true
            }
            if (newPassword.isEmpty()) {
                newPasswordEditText.error = "A nova palavra-passe é obrigatória."
                LogUtils.w("Validation Error (ResetPassword): Nova password vazia.")
                hasError = true
            }
            if (newPassword != confirmPassword) {
                confirmPasswordEditText.error = "As palavras-passe não são iguais."
                LogUtils.w("Validation Error (ResetPassword): Passwords não coincidem.")
                hasError = true
            }

            if (hasError) return@setOnClickListener

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
                    LogUtils.i("Password atualizada com sucesso")
                    val intent = Intent(this@ResetPasswordActivity, LoginActivity::class.java)
                    intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
                    startActivity(intent)
                    finish()
                }
                .onFailure { error ->
                    resetButton.isEnabled = true
                    ErrorDialogUtils.showApiError(this@ResetPasswordActivity, error)
                    LogUtils.e("Nao foi possivel atualizar a password: ${error.message}", error)
                }
        }
    }
}
