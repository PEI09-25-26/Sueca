package com.example.MVP

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKeys
import com.example.MVP.models.*
import com.example.MVP.network.RetrofitClient
import com.example.MVP.utils.LogUtils
import org.json.JSONObject
import retrofit2.HttpException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException

object AuthManager {
	private const val PREFS_NAME = "SuecaAuthSecure"
	private const val KEY_TOKEN = "auth_token"
	private const val KEY_UID = "user_uid"
	private const val KEY_USERNAME = "username"
	private const val KEY_EMAIL = "email"
	private const val KEY_FRIEND_CODE = "friend_code"
	private const val KEY_IS_ANONYMOUS = "is_anonymous"
	private const val KEY_ANONYMOUS_NAME = "anonymous_name"
	private val GUEST_NAME_REGEX = Regex("^Guest\\s+\\d+$")

	private lateinit var prefs: SharedPreferences
	private var secureStorageAvailable: Boolean = false
	private var runtimeToken: String? = null
	private var runtimeUid: String? = null
	private var runtimeUsername: String? = null
	private var runtimeEmail: String? = null
	private var runtimeFriendCode: String? = null

	// In-memory fallback when secure persistence isn't available
	private var inMemoryToken: String? = null
	private var inMemoryUid: String? = null
	private var inMemoryUsername: String? = null
	private var inMemoryEmail: String? = null
	private var inMemoryFriendCode: String? = null
	private var inMemoryIsAnonymous: Boolean = false
	private var inMemoryAnonymousName: String? = null

	private fun isInitialized(): Boolean = ::prefs.isInitialized

	fun initialize(context: Context) {
		try {
			val masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC)
			prefs = EncryptedSharedPreferences.create(
				PREFS_NAME,
				masterKeyAlias,
				context,
				EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
				EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
			)
			secureStorageAvailable = true
		} catch (e: Exception) {
			prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
			secureStorageAvailable = false
		}
	}

	fun getToken(): String? {
		if (!isInitialized()) return null
		return if (secureStorageAvailable) prefs.getString(KEY_TOKEN, null) else inMemoryToken
	}

	fun getUid(): String? {
		if (!isInitialized()) return null
		return if (secureStorageAvailable) prefs.getString(KEY_UID, null) else inMemoryUid
	}

	fun getUsername(): String? {
		if (!isInitialized()) return null
		return if (secureStorageAvailable) prefs.getString(KEY_USERNAME, null) else inMemoryUsername
	}

	fun getEmail(): String? {
		if (!isInitialized()) return null
		return if (secureStorageAvailable) prefs.getString(KEY_EMAIL, null) else inMemoryEmail
	}

	fun getSavedFriendCode(): String? {
		if (!isInitialized()) return null
		return if (secureStorageAvailable) prefs.getString(KEY_FRIEND_CODE, null) else inMemoryFriendCode
	}

	fun saveFriendCode(code: String) {
		if (!isInitialized()) return
		if (secureStorageAvailable) {
			prefs.edit().putString(KEY_FRIEND_CODE, code).apply()
		} else {
			inMemoryFriendCode = code
		}
	}

	fun isAnonymous(): Boolean {
		if (!isInitialized()) return false
		return if (secureStorageAvailable) prefs.getBoolean(KEY_IS_ANONYMOUS, false) else inMemoryIsAnonymous
	}

	fun getAnonymousName(): String? {
		if (!isInitialized()) return null
		return if (secureStorageAvailable) prefs.getString(KEY_ANONYMOUS_NAME, null) else inMemoryAnonymousName
	}

	fun getPlayerDisplayName(): String? {
		if (isLoggedIn()) {
			return getUsername()
		}

		val anonymousName = getAnonymousName()?.trim()
		if (!anonymousName.isNullOrBlank() && GUEST_NAME_REGEX.matches(anonymousName)) {
			return anonymousName
		}

		val guestName = generateGuestName()
		if (isInitialized()) {
			if (secureStorageAvailable) {
				prefs.edit().apply {
					putBoolean(KEY_IS_ANONYMOUS, true)
					putString(KEY_ANONYMOUS_NAME, guestName)
					apply()
				}
			} else {
				inMemoryIsAnonymous = true
				inMemoryAnonymousName = guestName
			}
		}
		return guestName
	}

	fun isLoggedIn(): Boolean = getToken() != null && getUid() != null

	fun getAuthHeader(): String? {
		val token = getToken() ?: return null
		return "Bearer $token"
	}

	fun startAnonymousSession(name: String? = null) {
		if (!isInitialized()) return
		val anonymousName = name?.trim()
		val guestName = if (!anonymousName.isNullOrBlank() && GUEST_NAME_REGEX.matches(anonymousName)) {
			anonymousName
		} else {
			generateGuestName()
		}
		if (secureStorageAvailable) {
			prefs.edit().apply {
				remove(KEY_TOKEN)
				remove(KEY_UID)
				remove(KEY_USERNAME)
				remove(KEY_EMAIL)
				putBoolean(KEY_IS_ANONYMOUS, true)
				putString(KEY_ANONYMOUS_NAME, guestName)
				apply()
			}
		} else {
			// Keep anonymous session in-memory only
			inMemoryToken = null
			inMemoryUid = null
			inMemoryUsername = null
			inMemoryEmail = null
			inMemoryIsAnonymous = true
			inMemoryAnonymousName = guestName
		}
	}

	private fun generateGuestName(): String {
		return "Guest ${(1000..9999).random()}"
	}

	suspend fun register(username: String, email: String, password: String): Result<String> {
		return try {
			val request = RegisterRequest(username, email, password)
			val response = RetrofitClient.api.registerUser(request)

			if (response.success && !response.verificationId.isNullOrBlank()) {
				Result.success(response.verificationId)
			} else {
				Result.failure(Exception(response.message))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun verifyEmailCode(verificationId: String, code: String): Result<UserData> {
		return try {
			val request = VerifyEmailRequest(verificationId, code)
			val response = RetrofitClient.api.verifyEmail(request)

			if (response.success && response.user != null && response.token != null) {
				saveUserData(response.user, response.token)
				Result.success(response.user)
			} else {
				Result.failure(Exception(response.message))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun login(username: String, password: String): Result<UserData> {
		return try {
			val request = LoginRequest(username, password)
			val response = RetrofitClient.api.loginUser(request)

			if (response.success && response.user != null && response.token != null) {
				saveUserData(response.user, response.token)
				Result.success(response.user)
			} else {
				Result.failure(Exception(response.message))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun recoverPassword(email: String): Result<String> {
		return try {
			val response = RetrofitClient.api.recoverPassword(email)

			if (response.success && !response.verificationId.isNullOrBlank()) {
				Result.success(response.verificationId)
			} else {
				Result.failure(Exception(response.message ?: "Failed to request password recovery"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun resetPassword(verificationId: String, code: String, newPassword: String): Result<Unit> {
		return try {
			val request = ResetPasswordRequest(verificationId, code, newPassword)
			val response = RetrofitClient.api.resetPassword(request)

			if (response.success) {
				Result.success(Unit)
			} else {
				Result.failure(Exception(response.message ?: "Failed to reset password"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun logout(): Result<Unit> {
		return try {
			val uid = getUid() ?: return Result.failure(Exception("No user logged in"))
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))

			val request = LogoutRequest(uid)
			val response = RetrofitClient.api.logoutUser(request, token)

			if (response.success) {
				clearUserData()
				Result.success(Unit)
			} else {
				// If server returns error, we still clear local state to allow new login
				clearUserData()
				Result.success(Unit)
			}
		} catch (e: Exception) {
			clearUserData()
			Result.success(Unit)
		}
	}

	suspend fun getUser(uid: String): Result<UserData> {
		return try {
			val token = getAuthHeader() ?: return Result.failure(Exception("No user logged in"))
			val response = RetrofitClient.api.getUser(uid, token)

			if (response.success && response.user != null) {
				Result.success(response.user)
			} else {
				Result.failure(Exception(response.message ?: "Failed to get user"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun getMatchHistory(uid: String): Result<List<com.example.MVP.models.MatchHistoryEntry>> {
		return try {
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))
			val response = RetrofitClient.api.getMatchHistory(uid, token)

			if (response.success) {
				Result.success(response.history ?: emptyList())
			} else {
				Result.failure(Exception(response.message ?: "Failed to get match history"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun updateUser(uid: String, updateRequest: UpdateUserRequest): Result<UserData> {
		return try {
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))
			val response = RetrofitClient.api.updateUser(uid, updateRequest, token)

			if (response.success && response.user != null) {
				saveUserData(response.user, getToken()!!)
				Result.success(response.user)
			} else {
				Result.failure(Exception(response.message ?: "Failed to update user"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun deleteUser(uid: String): Result<Unit> {
		return try {
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))
			val response = RetrofitClient.api.deleteUser(uid, token)

			if (response.success) {
				clearUserData()
				Result.success(Unit)
			} else {
				Result.failure(Exception(response.message))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun requestAccountDelete(uid: String): Result<Unit> {
		return try {
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))
			val response = RetrofitClient.api.requestDeleteAccount(DeleteAccountRequest(uid), token)
			if (response.success) {
				response.verificationId?.let {
					prefs.edit().putString("pending_delete_verification_id", it).apply()
				}
				Result.success(Unit)
			} else {
				Result.failure(Exception(response.message ?: "Failed to request delete"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun confirmAccountDelete(uid: String, code: String): Result<Unit> {
		return try {
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))
			val verificationId = prefs.getString("pending_delete_verification_id", null)
				?: return Result.failure(Exception("Missing delete verification context"))
			val response = RetrofitClient.api.confirmDeleteAccount(ConfirmDeleteAccountRequest(uid, verificationId, code), token)
			if (response.success) {
				prefs.edit().remove("pending_delete_verification_id").apply()
				clearUserData()
				Result.success(Unit)
			} else {
				Result.failure(Exception(response.message ?: "Failed to delete account"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	suspend fun updatePresence(status: String): Result<Unit> {
		return try {
			val uid = getUid() ?: return Result.failure(Exception("No user logged in"))
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))
			val response = RetrofitClient.api.updateUser(uid, UpdateUserRequest(status = status), token)

			if (response.success) {
				Result.success(Unit)
			} else {
				Result.failure(Exception(response.message ?: "Failed to update presence"))
			}
		} catch (e: Exception) {
			Result.failure(e)
		}
	}

	private fun saveUserData(user: UserData, token: String) {
		if (!isInitialized()) return
		LogUtils.i("Saving user data and token to secure storage for UID: ${user.uid}")
		// Store to secure prefs when available, otherwise keep in-memory only
		if (secureStorageAvailable) {
			prefs.edit().apply {
				putString(KEY_TOKEN, token)
				putString(KEY_UID, user.uid)
				putString(KEY_USERNAME, user.username)
				putString(KEY_EMAIL, user.email)
				if (user.friendCode != null) {
					putString(KEY_FRIEND_CODE, user.friendCode)
				}
				putBoolean(KEY_IS_ANONYMOUS, false)
				remove(KEY_ANONYMOUS_NAME)
				apply()
			}
			// keep runtime mirrors
			runtimeToken = token
			runtimeUid = user.uid
			runtimeUsername = user.username
			runtimeEmail = user.email
			runtimeFriendCode = user.friendCode
		} else {
			// Do not persist sensitive data to plaintext storage
			inMemoryToken = token
			inMemoryUid = user.uid
			inMemoryUsername = user.username
			inMemoryEmail = user.email
			inMemoryFriendCode = user.friendCode
			inMemoryIsAnonymous = false
			inMemoryAnonymousName = null
		}
	}

	private fun clearUserData() {
		if (!isInitialized()) return
		LogUtils.i("Clearing user data from storage (Logout/Cleanup)")
		// Clear in-memory and secure storage if used
		inMemoryToken = null
		inMemoryUid = null
		inMemoryUsername = null
		inMemoryEmail = null
		inMemoryFriendCode = null
		inMemoryIsAnonymous = false
		inMemoryAnonymousName = null
		runtimeToken = null
		runtimeUid = null
		runtimeUsername = null
		runtimeEmail = null
		runtimeFriendCode = null
		if (secureStorageAvailable) {
			prefs.edit().apply {
				remove(KEY_TOKEN)
				remove(KEY_UID)
				remove(KEY_USERNAME)
				remove(KEY_EMAIL)
				remove(KEY_FRIEND_CODE)
				remove(KEY_IS_ANONYMOUS)
				remove(KEY_ANONYMOUS_NAME)
				apply()
			}
		}
	}
}
