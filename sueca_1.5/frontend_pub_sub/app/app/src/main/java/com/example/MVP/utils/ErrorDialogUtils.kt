package com.example.MVP.utils

import android.content.Context
import android.view.View
import androidx.appcompat.app.AlertDialog
import com.google.android.material.snackbar.Snackbar
import retrofit2.HttpException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

object ErrorDialogUtils {

    /**
     * Shows a blocking error dialog for critical issues.
     */
    fun showError(context: Context, title: String, message: String, onDismiss: (() -> Unit)? = null) {
        val cleanMessage = cleanTechnicalMessage(message)
        LogUtils.e("UI Error Dialog ($title): $message (Clean: $cleanMessage)")
        
        AlertDialog.Builder(context, android.R.style.Theme_DeviceDefault_Light_Dialog_Alert)
            .setTitle(title)
            .setMessage(cleanMessage)
            .setPositiveButton("OK") { _, _ -> onDismiss?.invoke() }
            .setOnDismissListener { onDismiss?.invoke() }
            .show()
    }

    /**
     * Shows a transient snackbar for recoverable or informative errors.
     */
    fun showSnackbar(view: View, message: String, actionText: String? = null, action: (() -> Unit)? = null) {
        val cleanMessage = cleanTechnicalMessage(message)
        LogUtils.w("UI Snackbar: $message (Clean: $cleanMessage)")
        
        val duration = if (actionText != null) Snackbar.LENGTH_INDEFINITE else Snackbar.LENGTH_LONG
        val snackbar = Snackbar.make(view, cleanMessage, duration)
        if (actionText != null && action != null) {
            snackbar.setAction(actionText) { action() }
        } else {
            snackbar.setAction("OK") { snackbar.dismiss() }
        }
        snackbar.show()
    }

    /**
     * Maps API exceptions to user-friendly messages and displays them in a dialog.
     */
    fun showApiError(context: Context, throwable: Throwable) {
        val title = "Atenção"
        val message = mapThrowableToMessage(throwable)
        showError(context, title, message)
    }

    /**
     * Maps API exceptions to user-friendly messages for Snackbars.
     */
    fun showApiSnackbar(view: View, throwable: Throwable, actionText: String? = "Tentar", action: (() -> Unit)? = null) {
        val message = mapThrowableToMessage(throwable)
        showSnackbar(view, message, actionText, action)
    }

    /**
     * Replaces technical or system messages with user-friendly text.
     */
    private fun cleanTechnicalMessage(message: String): String {
        val technicalPatterns = listOf(
            Regex(".*\\b(5\\d{2}|4\\d{2})\\b.*"), // HTTP Status codes
            Regex(".*\\b(failed|timeout|refused|reset|socket|exception|null|body|token)\\b.*", RegexOption.IGNORE_CASE),
            Regex(".*HTTP.*", RegexOption.IGNORE_CASE),
            Regex(".*Request.*", RegexOption.IGNORE_CASE)
        )

        if (technicalPatterns.any { it.containsMatchIn(message) }) {
            return "Ocorreu um erro na ligação ao servidor. Por favor, tenta novamente."
        }
        return message
    }

    private fun mapThrowableToMessage(throwable: Throwable): String {
        return when (throwable) {
            is HttpException -> {
                when (throwable.code()) {
                    401 -> "A tua sessão expirou ou os dados estão errados. Por favor, verifica e tenta de novo."
                    403 -> "Não tens permissão para realizar esta ação."
                    404 -> "O conteúdo solicitado não foi encontrado."
                    in 500..599 -> "Erro no servidor: por favor tente mais tarde."
                    else -> "Erro na ligação (${throwable.code()}). Tenta novamente."
                }
            }
            is UnknownHostException, is ConnectException -> {
                "Sem ligação ao servidor. Verifica a tua internet."
            }
            is SocketTimeoutException -> {
                "A ligação está demorada. Tenta novamente."
            }
            else -> {
                val msg = throwable.message ?: ""
                if (msg.isNotBlank()) cleanTechnicalMessage(msg) else "Ocorreu um erro inesperado."
            }
        }
    }
}
