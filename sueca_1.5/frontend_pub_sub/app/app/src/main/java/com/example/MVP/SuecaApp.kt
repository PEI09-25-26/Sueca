package com.example.MVP

import android.app.Activity
import android.app.Application
import android.os.Bundle
import android.util.Log
import com.example.MVP.network.PresenceMqttManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch


class SuecaApp : Application(), Application.ActivityLifecycleCallbacks {

    init {
        Log.e("SuecaApp", "CRITICAL: SuecaApp class initialized (static init)")
    }

    private var startedActivities = 0

    override fun onCreate() {
        super.onCreate()
        Log.e("SuecaApp", "CRITICAL: SuecaApp.onCreate() called")
        AuthManager.initialize(applicationContext)
        registerActivityLifecycleCallbacks(this)
    }

    override fun onActivityStarted(activity: Activity) {
        startedActivities += 1
        val loggedIn = AuthManager.isLoggedIn()
        Log.d("SuecaApp", "Activity Started: ${activity.localClassName}, Total: $startedActivities, LoggedIn: $loggedIn")
        
        if (loggedIn) {
            val uid = AuthManager.getUid()
            Log.d("SuecaApp", "Attempting Presence connect for UID: $uid")
            if (uid != null) {
                PresenceMqttManager.connect(uid)
            }
        }
    }

    override fun onActivityStopped(activity: Activity) {
        startedActivities -= 1
        if (startedActivities == 0) {
            PresenceMqttManager.disconnect()
        }
    }

    override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) = Unit

    override fun onActivityResumed(activity: Activity) = Unit

    override fun onActivityPaused(activity: Activity) = Unit

    override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) = Unit

    override fun onActivityDestroyed(activity: Activity) = Unit
}
