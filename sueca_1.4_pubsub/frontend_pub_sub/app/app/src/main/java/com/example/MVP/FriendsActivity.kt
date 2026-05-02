package com.example.MVP

import android.os.Bundle
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity

class FriendsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.friends)

        val backButton = findViewById<ImageView>(R.id.backButton2)
        backButton.setOnClickListener {
            finish()
        }
    }
}
