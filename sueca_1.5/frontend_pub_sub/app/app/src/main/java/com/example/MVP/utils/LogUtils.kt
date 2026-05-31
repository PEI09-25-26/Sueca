package com.example.MVP.utils

import android.util.Log

object LogUtils {
    private const val TAG = "SuecaDebug"

    /**
     * Log a Debug message.
     */
    fun d(message: String) {
        Log.d(TAG, message)
    }

    /**
     * Log an Info message.
     */
    fun i(message: String) {
        Log.i(TAG, message)
    }

    /**
     * Log a Warning message.
     */
    fun w(message: String) {
        Log.w(TAG, message)
    }

    /**
     * Log an Error message.
     */
    fun e(message: String, throwable: Throwable? = null) {
        if (throwable != null) {
            Log.e(TAG, message, throwable)
        } else {
            Log.e(TAG, message)
        }
    }
}
