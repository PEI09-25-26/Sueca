package com.example.Jogo_da_Sueca

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.View
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
import androidx.lifecycle.lifecycleScope
import com.example.Jogo_da_Sueca.models.Card
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class HybridActivity : AppCompatActivity() {

    private lateinit var modeSwitch: Switch
    private lateinit var modeText: TextView
    private lateinit var previewView: PreviewView
    private lateinit var mesaContainer: ConstraintLayout
    private lateinit var handRecyclerView: RecyclerView
    private lateinit var recognitionOverlay: View
    private lateinit var recognitionStateImage: ImageView
    private lateinit var recognitionProgressText: TextView

    private lateinit var handAdapter: CardsAdapter
    private var isHost: Boolean = false
    private var virtualPhonePlayers: Int = 0
    private var isRecognitionRunning: Boolean = false
    private var recognitionJob: Job? = null

    private val cardsPerVirtualPlayer = 10
    private val virtualHands = mutableMapOf<Int, MutableList<Card>>()

    private val cameraPermissionRequestCode = 11

    private val recognitionPool = listOf(
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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_hybrid)

        isHost = intent.getBooleanExtra("isHost", false)
        virtualPhonePlayers = intent.getIntExtra("virtualPhonePlayers", if (isHost) 1 else 0)

        findViewById<ImageView>(R.id.backButton).setOnClickListener { finish() }

        modeSwitch = findViewById(R.id.activity_hybrid_switch)
        modeText = findViewById(R.id.txtHybridMode)
        previewView = findViewById(R.id.previewView)
        mesaContainer = findViewById(R.id.mesaContainer)
        handRecyclerView = findViewById(R.id.playerHandRecyclerView)
        recognitionOverlay = findViewById(R.id.recognitionOverlay)
        recognitionStateImage = findViewById(R.id.imgRecognitionState)
        recognitionProgressText = findViewById(R.id.txtRecognitionProgress)

        setupMockedTable()
        setupMockedPhoneHand()
        setupSwitch()

        if (shouldRunRecognitionFlow()) {
            startRecognitionMock()
        }

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
                previewView.visibility = View.GONE
                recognitionOverlay.visibility = View.GONE
                mesaContainer.visibility = View.VISIBLE
            } else {
                modeSwitch.text = "Camera ativa"
                modeText.text = "Modo atual: camera"
                mesaContainer.visibility = View.GONE

                if (isRecognitionRunning) {
                    previewView.visibility = View.GONE
                    recognitionOverlay.visibility = View.VISIBLE
                } else {
                    previewView.visibility = View.VISIBLE
                    recognitionOverlay.visibility = View.GONE
                }

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
        // In hybrid recognition flow, cards are appended one-by-one as they are recognized.
        val handCards = emptyList<Card>()

        handAdapter = CardsAdapter(
            handCards
        ) {
            // Mock hand only; no action yet.
        }

        handAdapter.isEnabled = false
        handRecyclerView.layoutManager = GridLayoutManager(this, 5)
        handRecyclerView.adapter = handAdapter
    }

    private fun shouldRunRecognitionFlow(): Boolean {
        // Host: receives cards for each virtual phone player.
        // Virtual phone player: receives own 10 cards one by one.
        return if (isHost) virtualPhonePlayers > 0 else true
    }

    private fun startRecognitionMock() {
        if (isRecognitionRunning) return

        isRecognitionRunning = true
        modeSwitch.isEnabled = false
        modeSwitch.isChecked = false
        modeSwitch.text = "Camera ativa"
        modeText.text = "Modo atual: camera"

        previewView.visibility = View.GONE
        mesaContainer.visibility = View.GONE
        recognitionOverlay.visibility = View.VISIBLE

        recognitionJob = lifecycleScope.launch {
            var recognizedTotal = 0
            val playersToProcess = if (isHost) {
                virtualPhonePlayers.coerceAtLeast(1)
            } else {
                1
            }
            val totalToRecognize = playersToProcess * cardsPerVirtualPlayer

            for (playerIndex in 1..playersToProcess) {
                val hand = virtualHands.getOrPut(playerIndex) { mutableListOf() }

                for (cardSlot in 1..cardsPerVirtualPlayer) {
                    // Eye icon while waiting for the next card to be shown to camera.
                    recognitionStateImage.setImageResource(R.drawable.ic_hybrid_eye)
                    recognitionProgressText.text = if (isHost) {
                        "Mostra ao telemovel a carta $cardSlot/$cardsPerVirtualPlayer"
                    } else {
                        "A aguardar carta $cardSlot/$cardsPerVirtualPlayer"
                    }
                    delay(600)

                    val card = recognitionPool[(recognizedTotal) % recognitionPool.size]
                    hand.add(mapCardForCurrentRole(card))
                    recognizedTotal += 1

                    updateVirtualHandUI(playerIndex)

                    // Show success for 2 seconds after each recognized card.
                    recognitionStateImage.setImageResource(R.drawable.ic_hybrid_check)
                    recognitionProgressText.text =
                        "Carta reconhecida ($recognizedTotal/$totalToRecognize)"
                    delay(2000)
                }
            }

            isRecognitionRunning = false
            modeSwitch.isEnabled = true
            recognitionOverlay.visibility = View.GONE
            previewView.visibility = View.VISIBLE
            recognitionProgressText.text = "Reconhecimento terminado"
        }
    }

    private fun updateVirtualHandUI(playerIndex: Int) {
        val cards = virtualHands[playerIndex].orEmpty()
        handAdapter.updateCards(cards)
    }

    private fun mapCardForCurrentRole(card: Card): Card {
        return if (isHost) {
            // Host should only see card backs while helping to recognize virtual player's hand.
            Card(card.id, "hidden", "hidden")
        } else {
            // Virtual player sees the actual recognized cards.
            card
        }
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

    override fun onDestroy() {
        recognitionJob?.cancel()
        super.onDestroy()
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
