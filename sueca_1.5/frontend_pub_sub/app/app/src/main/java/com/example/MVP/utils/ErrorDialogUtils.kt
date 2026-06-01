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
    fun showError(
        context: Context,
        title: String,
        message: String,
        buttonText: String = "OK",
        onDismiss: (() -> Unit)? = null
    ) {
        val cleanMessage = cleanTechnicalMessage(message)
        LogUtils.e("UI Error Dialog ($title): $message (Clean: $cleanMessage)")
        
        val dialog = android.app.Dialog(context, com.example.MVP.R.style.CustomDialogTheme)
        dialog.requestWindowFeature(android.view.Window.FEATURE_NO_TITLE)
        dialog.window?.setBackgroundDrawable(android.graphics.drawable.ColorDrawable(android.graphics.Color.TRANSPARENT))
        
        val inflater = android.view.LayoutInflater.from(context)
        val view = inflater.inflate(com.example.MVP.R.layout.dialog_info, null)
        dialog.setContentView(view)
        
        view.findViewById<android.widget.TextView>(com.example.MVP.R.id.dialogTitle).text = title
        view.findViewById<android.widget.TextView>(com.example.MVP.R.id.dialogMessage).text = cleanMessage
        
        val btnOk = view.findViewById<android.widget.Button>(com.example.MVP.R.id.btnDialogOk)
        btnOk.text = buttonText
        btnOk.setOnClickListener {
            dialog.dismiss()
            onDismiss?.invoke()
        }
        
        dialog.setOnDismissListener {
            onDismiss?.invoke()
        }
        
        dialog.show()
    }

    /**
     * Shows a transient snackbar for recoverable or informative errors.
     */
    fun showSnackbar(view: View, message: String, actionText: String? = null, action: (() -> Unit)? = null) {
        val cleanMessage = cleanTechnicalMessage(message)
        LogUtils.w("UI Snackbar: $message (Clean: $cleanMessage)")
        
        val snackbar = Snackbar.make(view, cleanMessage, Snackbar.LENGTH_LONG)
        if (actionText != null && action != null) {
            snackbar.setAction(actionText) { action() }
        } else {
            snackbar.setAction("OK") { snackbar.dismiss() }
        }
        
        // Custom styling to make it unified and premium
        val snackbarView = snackbar.view
        snackbarView.setBackgroundResource(com.example.MVP.R.drawable.snackbar_bg)
        
        // Adjust padding to make it elegant
        val params = snackbarView.layoutParams as? android.view.ViewGroup.MarginLayoutParams
        if (params != null) {
            params.setMargins(16, 16, 16, 16)
            snackbarView.layoutParams = params
        }
        
        // Text styling
        val textView = snackbarView.findViewById<android.widget.TextView>(com.google.android.material.R.id.snackbar_text)
        textView.setTextColor(android.graphics.Color.WHITE)
        textView.textSize = 14f
        
        // Action styling
        val actionButton = snackbarView.findViewById<android.widget.Button>(com.google.android.material.R.id.snackbar_action)
        actionButton.setTextColor(android.graphics.Color.parseColor("#FF9900")) // Bright orange accent
        actionButton.setTypeface(null, android.graphics.Typeface.BOLD)
        
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
     * Swapped to display a premium Dialog like requested.
     */
    fun showApiSnackbar(view: View, throwable: Throwable, actionText: String? = "OK", action: (() -> Unit)? = null) {
        val message = mapThrowableToMessage(throwable)
        val context = view.context
        showError(
            context = context,
            title = "Atenção",
            message = message,
            buttonText = "OK",
            onDismiss = action
        )
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
