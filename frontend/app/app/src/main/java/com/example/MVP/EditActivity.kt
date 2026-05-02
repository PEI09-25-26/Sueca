package com.example.MVP

import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.button.MaterialButton
import com.example.MVP.models.UpdateUserRequest
import kotlinx.coroutines.launch

class EditActivity : AppCompatActivity() {

    private lateinit var bannerImage: ImageView
    private lateinit var profileImage: ImageView
    private lateinit var backButton: ImageView
    private lateinit var nameEditText: EditText
    private lateinit var descriptionEditText: EditText
    private lateinit var saveButton: MaterialButton

    private var selectedBanner: String = ""
    private var selectedPhoto: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AuthManager.initialize(applicationContext)
        setContentView(R.layout.edit_profile)

        bannerImage = findViewById(R.id.edit_banner_profile)
        profileImage = findViewById(R.id.edit_image_profile)
        backButton = findViewById(R.id.backButton3)
        nameEditText = findViewById(R.id.edit_name_profile)
        descriptionEditText = findViewById(R.id.edit_description_profile)
        saveButton = findViewById(R.id.edit_save_profile)

        loadCurrentUser()

        bannerImage.setOnClickListener {
            showBannerColorPicker()
        }

        profileImage.setOnClickListener {
            showProfilePicturePicker()
        }

        backButton.setOnClickListener {
            finish()
        }

        saveButton.setOnClickListener {
            saveProfileChanges()
        }
    }

    private fun loadCurrentUser() {
        val uid = AuthManager.getUid()
        if (uid == null) {
            Toast.makeText(this, "User not logged in", Toast.LENGTH_SHORT).show()
            finish()
            return
        }

        lifecycleScope.launch {
            AuthManager.getUser(uid)
                .onSuccess { user ->
                    nameEditText.setText(user.username)
                    descriptionEditText.setText(user.description)

                    selectedBanner = user.bannerURL
                    selectedPhoto = user.photoURL

                    applyBannerPreview(selectedBanner)
                    applyPhotoPreview(selectedPhoto)
                }
                .onFailure { error ->
                    Toast.makeText(
                        this@EditActivity,
                        "Erro a carregar perfil: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }

    private fun saveProfileChanges() {
        val uid = AuthManager.getUid()
        if (uid == null) {
            Toast.makeText(this, "User not logged in", Toast.LENGTH_SHORT).show()
            return
        }

        val description = descriptionEditText.text.toString().trim()
        saveButton.isEnabled = false

        lifecycleScope.launch {
            val request = UpdateUserRequest(
                description = description,
                photoURL = selectedPhoto,
                bannerURL = selectedBanner,
            )

            AuthManager.updateUser(uid, request)
                .onSuccess {
                    Toast.makeText(this@EditActivity, "Perfil atualizado", Toast.LENGTH_SHORT).show()
                    finish()
                }
                .onFailure { error ->
                    saveButton.isEnabled = true
                    Toast.makeText(
                        this@EditActivity,
                        "Erro ao guardar: ${error.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
        }
    }

    private fun showBannerColorPicker() {
        val dialog = BottomSheetDialog(this)
        val contentView = layoutInflater.inflate(R.layout.bottom_sheet_banner, null)
        dialog.setContentView(contentView)

        fun bindBannerChip(chipId: Int, bannerDrawable: Int, bannerKey: String) {
            contentView.findViewById<View>(chipId).setOnClickListener {
                selectedBanner = bannerKey
                bannerImage.setImageResource(bannerDrawable)
                dialog.dismiss()
            }
        }

        bindBannerChip(R.id.color_red, R.drawable.banner_red, "banner_red")
        bindBannerChip(R.id.color_blue, R.drawable.banner_blue, "banner_blue")
        bindBannerChip(R.id.color_green, R.drawable.banner_green, "banner_green")
        bindBannerChip(R.id.color_purple, R.drawable.banner_purple, "banner_purple")
        bindBannerChip(R.id.color_orange, R.drawable.banner_orange, "banner_orange")
        bindBannerChip(R.id.color_pink, R.drawable.banner_pink, "banner_pink")
        bindBannerChip(R.id.color_teal, R.drawable.banner_teal, "banner_teal")
        bindBannerChip(R.id.color_gold, R.drawable.banner_gold, "banner_gold")
        bindBannerChip(R.id.color_rose, R.drawable.banner_rose, "banner_rose")
        bindBannerChip(R.id.color_slate, R.drawable.banner_slate, "banner_slate")

        dialog.show()
    }

    private fun showProfilePicturePicker() {
        val dialog = BottomSheetDialog(this)
        val contentView = layoutInflater.inflate(R.layout.bottom_sheet_profile_picture, null)
        dialog.setContentView(contentView)

        fun bindProfileOption(viewId: Int, drawableId: Int, photoKey: String) {
            contentView.findViewById<View>(viewId).setOnClickListener {
                selectedPhoto = photoKey
                profileImage.setImageResource(drawableId)
                dialog.dismiss()
            }
        }

        bindProfileOption(R.id.profile_pic1_option, R.drawable.profile_pic1, "profile_pic1")
        bindProfileOption(R.id.profile_pic2_option, R.drawable.profile_pic2, "profile_pic2")
        bindProfileOption(R.id.profile_pic3_option, R.drawable.profile_pic3, "profile_pic3")
        bindProfileOption(R.id.profile_pic4_option, R.drawable.profile_pic4, "profile_pic4")
        bindProfileOption(R.id.profile_pic5_option, R.drawable.profile_pic5, "profile_pic5")

        dialog.show()
    }

    private fun applyBannerPreview(bannerKey: String?) {
        when (bannerKey) {
            "banner_red" -> bannerImage.setImageResource(R.drawable.banner_red)
            "banner_blue" -> bannerImage.setImageResource(R.drawable.banner_blue)
            "banner_green" -> bannerImage.setImageResource(R.drawable.banner_green)
            "banner_purple" -> bannerImage.setImageResource(R.drawable.banner_purple)
            "banner_orange" -> bannerImage.setImageResource(R.drawable.banner_orange)
            "banner_pink" -> bannerImage.setImageResource(R.drawable.banner_pink)
            "banner_teal" -> bannerImage.setImageResource(R.drawable.banner_teal)
            "banner_gold" -> bannerImage.setImageResource(R.drawable.banner_gold)
            "banner_rose" -> bannerImage.setImageResource(R.drawable.banner_rose)
            "banner_slate" -> bannerImage.setImageResource(R.drawable.banner_slate)
            else -> bannerImage.setImageResource(R.drawable.banner_background)
        }
    }

    private fun applyPhotoPreview(photoKey: String?) {
        when (photoKey) {
            "profile_pic1" -> profileImage.setImageResource(R.drawable.profile_pic1)
            "profile_pic2" -> profileImage.setImageResource(R.drawable.profile_pic2)
            "profile_pic3" -> profileImage.setImageResource(R.drawable.profile_pic3)
            "profile_pic4" -> profileImage.setImageResource(R.drawable.profile_pic4)
            "profile_pic5" -> profileImage.setImageResource(R.drawable.profile_pic5)
            else -> profileImage.setImageResource(R.drawable.sueca)
        }
    }
}
