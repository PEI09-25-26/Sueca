package com.example.MVP.utils

import android.app.Dialog
import android.content.Context
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.view.LayoutInflater
import android.view.Window
import android.widget.Button
import android.widget.TextView
import com.example.MVP.R

/**
 * Displays a themed exit-confirmation dialog with no internal Material divider lines.
 *
 * @param context  The calling Activity context.
 * @param title    Bold title text shown at the top.
 * @param message  Subtext shown below the title.
 * @param onConfirm Lambda executed when the user taps "Sim".
 */
fun showExitDialog(
    context: Context,
    title: String,
    message: String,
    onConfirm: () -> Unit
) {
    showCustomConfirmDialog(
        context = context,
        title = title,
        message = message,
        positiveText = "SIM",
        negativeText = "NÃO",
        onConfirm = onConfirm
    )
}

/**
 * Displays a customizable themed two-button confirmation dialog.
 */
fun showCustomConfirmDialog(
    context: Context,
    title: String,
    message: String,
    positiveText: String = "SIM",
    negativeText: String = "NÃO",
    neutralText: String? = null,
    onConfirm: () -> Unit,
    onCancel: (() -> Unit)? = null,
    onNeutral: (() -> Unit)? = null
) {
    val dialog = Dialog(context, com.example.MVP.R.style.CustomDialogTheme)
    dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
    dialog.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))

    val view = LayoutInflater.from(context).inflate(R.layout.dialog_exit_confirm, null)
    dialog.setContentView(view)

    view.findViewById<TextView>(R.id.dialogTitle).text = title
    view.findViewById<TextView>(R.id.dialogMessage).text = message

    val btnNo = view.findViewById<Button>(R.id.btnDialogNo)
    btnNo.text = negativeText
    btnNo.setOnClickListener {
        dialog.dismiss()
        onCancel?.invoke()
    }

    val btnYes = view.findViewById<Button>(R.id.btnDialogYes)
    btnYes.text = positiveText
    btnYes.setOnClickListener {
        dialog.dismiss()
        onConfirm()
    }

    val btnNeutral = view.findViewById<Button>(R.id.btnDialogNeutral)
    if (neutralText != null) {
        btnNeutral.visibility = android.view.View.VISIBLE
        btnNeutral.text = neutralText
        btnNeutral.setOnClickListener {
            dialog.dismiss()
            onNeutral?.invoke()
        }
    } else {
        btnNeutral.visibility = android.view.View.GONE
    }

    dialog.show()
}
