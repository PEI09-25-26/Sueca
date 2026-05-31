package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.util.Patterns
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import com.example.MVP.utils.ErrorDialogUtils
import com.example.MVP.utils.LogUtils
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
                emailEditText.error = "O endereço de email é obrigatório."
                LogUtils.w("Validation Error (RecoverPassword): Email vazio.")
                return@setOnClickListener
            }
            if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                emailEditText.error = "Introduz um endereço de email válido."
                LogUtils.w("Validation Error (RecoverPassword): Formato de email inválido ($email).")
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
                    LogUtils.i("Codigo de recuperacao enviado para $email")
                    val intent = Intent(this@RecoverPasswordActivity, ResetPasswordActivity::class.java)
                    intent.putExtra("verificationId", verificationId)
                    intent.putExtra("email", email)
                    startActivity(intent)
                    finish()
                }
                .onFailure { error ->
                    sendCodeButton.isEnabled = true
                    ErrorDialogUtils.showApiError(this@RecoverPasswordActivity, error)
                    LogUtils.e("Nao foi possivel enviar o codigo de recuperacao: ${error.message}", error)
                }
        }
    }
}
