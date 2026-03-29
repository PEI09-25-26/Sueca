package com.example.MVP

import android.os.Bundle
import android.view.View
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.bottomsheet.BottomSheetDialog

class EditActivity : AppCompatActivity() {

    private lateinit var bannerImage: ImageView
    private lateinit var backButton: ImageView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.edit_profile)

        bannerImage = findViewById(R.id.edit_banner_profile)
        backButton = findViewById(R.id.backButton3)

        bannerImage.setOnClickListener {
            showBannerColorPicker()
        }

        backButton.setOnClickListener {
            finish()
        }
    }

    private fun showBannerColorPicker() {
        val dialog = BottomSheetDialog(this)
        val contentView = layoutInflater.inflate(R.layout.bottom_sheet_banner, null)
        dialog.setContentView(contentView)

        fun bindBannerChip(chipId: Int, bannerDrawable: Int) {
            contentView.findViewById<View>(chipId).setOnClickListener {
                bannerImage.setBackgroundResource(bannerDrawable)
                dialog.dismiss()
            }
        }

        bindBannerChip(R.id.color_red, R.drawable.banner_red)
        bindBannerChip(R.id.color_blue, R.drawable.banner_blue)
        bindBannerChip(R.id.color_green, R.drawable.banner_green)
        bindBannerChip(R.id.color_purple, R.drawable.banner_purple)
        bindBannerChip(R.id.color_orange, R.drawable.banner_orange)
        bindBannerChip(R.id.color_pink, R.drawable.banner_pink)
        bindBannerChip(R.id.color_teal, R.drawable.banner_teal)
        bindBannerChip(R.id.color_gold, R.drawable.banner_gold)
        bindBannerChip(R.id.color_rose, R.drawable.banner_rose)
        bindBannerChip(R.id.color_slate, R.drawable.banner_slate)

        dialog.show()
    }
}
