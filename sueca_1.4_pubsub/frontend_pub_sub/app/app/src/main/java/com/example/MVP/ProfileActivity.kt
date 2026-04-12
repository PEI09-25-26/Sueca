package com.example.MVP

import android.content.Intent
import android.os.Bundle
import android.widget.ImageView
import com.google.android.material.button.MaterialButton
import androidx.appcompat.app.AppCompatActivity

class ProfileActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.profile)

        val backButton = findViewById<ImageView>(R.id.backButton3)
        val editProfileButton = findViewById<MaterialButton>(R.id.edit_profile)

        backButton.setOnClickListener {
            finish()
        }

        editProfileButton.setOnClickListener {
            val intent = Intent(this, EditActivity::class.java)
            startActivity(intent)
        }
    }
}
