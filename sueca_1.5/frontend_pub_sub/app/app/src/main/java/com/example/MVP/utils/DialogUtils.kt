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
    val dialog = Dialog(context)
    dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
    dialog.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))

    val view = LayoutInflater.from(context).inflate(R.layout.dialog_exit_confirm, null)
    dialog.setContentView(view)

    view.findViewById<TextView>(R.id.dialogTitle).text = title
    view.findViewById<TextView>(R.id.dialogMessage).text = message

    view.findViewById<Button>(R.id.btnDialogNo).setOnClickListener {
        dialog.dismiss()
    }
    view.findViewById<Button>(R.id.btnDialogYes).setOnClickListener {
        dialog.dismiss()
        onConfirm()
    }

    dialog.show()
}
