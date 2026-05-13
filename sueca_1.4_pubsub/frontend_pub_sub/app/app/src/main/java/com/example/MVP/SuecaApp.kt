package com.example.MVP

import android.app.Activity
import android.app.Application
import android.os.Bundle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SuecaApp : Application(), Application.ActivityLifecycleCallbacks {

    private var startedActivities = 0

    override fun onCreate() {
        super.onCreate()
        AuthManager.initialize(applicationContext)
        registerActivityLifecycleCallbacks(this)
    }

    override fun onActivityStarted(activity: Activity) {
        startedActivities += 1
        if (startedActivities == 1 && AuthManager.isLoggedIn()) {
            CoroutineScope(Dispatchers.IO).launch {
                AuthManager.updatePresence("online")
            }
        }
    }

    override fun onActivityStopped(activity: Activity) {
        startedActivities -= 1
        if (startedActivities == 0 && AuthManager.isLoggedIn()) {
            CoroutineScope(Dispatchers.IO).launch {
                AuthManager.updatePresence("offline")
            }
        }
    }

    override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) = Unit

    override fun onActivityResumed(activity: Activity) = Unit

    override fun onActivityPaused(activity: Activity) = Unit

    override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) = Unit

    override fun onActivityDestroyed(activity: Activity) = Unit
}
