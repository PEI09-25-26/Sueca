package com.example.MVP

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.ImageView
import android.widget.Switch
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.constraintlayout.widget.ConstraintLayout
import com.example.MVP.models.Card

class HybridActivity : AppCompatActivity() {

    private lateinit var modeSwitch: Switch
    private lateinit var modeText: TextView
    private lateinit var previewView: PreviewView
    private lateinit var mesaContainer: ConstraintLayout
    private lateinit var handRecyclerView: RecyclerView

    private lateinit var handAdapter: CardsAdapter
    private var isHost: Boolean = false

    private val cameraPermissionRequestCode = 11

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_hybrid)

        isHost = intent.getBooleanExtra("isHost", false)

        findViewById<ImageView>(R.id.backButton).setOnClickListener { finish() }

        modeSwitch = findViewById(R.id.activity_hybrid_switch)
        modeText = findViewById(R.id.txtHybridMode)
        previewView = findViewById(R.id.previewView)
        mesaContainer = findViewById(R.id.mesaContainer)
        handRecyclerView = findViewById(R.id.playerHandRecyclerView)

        setupMockedTable()
        setupMockedPhoneHand()
        setupSwitch()

        if (allPermissionsGranted()) {
            startCameraPreview()
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA),
                cameraPermissionRequestCode
            )
        }
    }

    private fun setupSwitch() {
        // false -> camera; true -> mesa
        modeSwitch.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                modeSwitch.text = "Mesa ativa"
                modeText.text = "Modo atual: mesa"
                previewView.visibility = android.view.View.GONE
                mesaContainer.visibility = android.view.View.VISIBLE
            } else {
                modeSwitch.text = "Camera ativa"
                modeText.text = "Modo atual: camera"
                previewView.visibility = android.view.View.VISIBLE
                mesaContainer.visibility = android.view.View.GONE

                if (allPermissionsGranted()) {
                    startCameraPreview()
                } else {
                    ActivityCompat.requestPermissions(
                        this,
                        arrayOf(Manifest.permission.CAMERA),
                        cameraPermissionRequestCode
                    )
                }
            }
        }
    }

    private fun setupMockedTable() {
        // Mocked cards that represent a fixed table state.
        setCardResource(R.id.card_north, "clubs_2")
        setCardResource(R.id.card_west, "hearts_king")
        // Requested: no mocked card on the right player (east) and phone player (south).
        setCardBack(R.id.card_east)
        setCardBack(R.id.card_south)
        setCardResource(R.id.trump_card, "clubs_ace")
    }

    private fun setupMockedPhoneHand() {
        val handCards = if (isHost) {
            // Host view should keep the phone hand hidden.
            List(10) { index ->
                Card((index + 1).toString(), "hidden", "hidden")
            }
        } else {
            listOf(
                Card("1", "clubs", "ace"),
                Card("2", "hearts", "7"),
                Card("3", "spades", "king"),
                Card("4", "diamonds", "2"),
                Card("5", "hearts", "jack"),
                Card("6", "clubs", "5"),
                Card("7", "spades", "3"),
                Card("8", "diamonds", "queen"),
                Card("9", "clubs", "6"),
                Card("10", "hearts", "ace")
            )
        }

        handAdapter = CardsAdapter(
            handCards
        ) {
            // Mock hand only; no action yet.
        }

        handAdapter.isEnabled = false
        handRecyclerView.layoutManager = GridLayoutManager(this, 5)
        handRecyclerView.adapter = handAdapter
    }

    private fun setCardResource(viewId: Int, cardName: String) {
        val cardView = findViewById<ImageView>(viewId)
        val resourceId = resources.getIdentifier(cardName, "drawable", packageName)
        if (resourceId != 0) {
            cardView.setImageResource(resourceId)
        } else {
            cardView.setImageResource(R.drawable.card_back)
        }
    }

    private fun setCardBack(viewId: Int) {
        findViewById<ImageView>(viewId).setImageResource(R.drawable.card_back)
    }

    private fun startCameraPreview() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)

        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(previewView.surfaceProvider)
            }

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    preview
                )
            } catch (_: Exception) {
                // Keep the activity usable in mesa mode even when camera bind fails.
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun allPermissionsGranted(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) ==
            PackageManager.PERMISSION_GRANTED
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == cameraPermissionRequestCode && grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) {
            startCameraPreview()
        }
    }
}
