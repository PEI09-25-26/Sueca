package com.example.MVP

import android.content.Context
import android.content.SharedPreferences
import com.example.MVP.models.*
import com.example.MVP.network.RetrofitClient
import org.json.JSONObject
import retrofit2.HttpException

object AuthManager {
	private const val PREFS_NAME = "SuecaAuth"
	private const val KEY_TOKEN = "auth_token"
	private const val KEY_UID = "user_uid"
	private const val KEY_USERNAME = "username"
	private const val KEY_EMAIL = "email"
	private const val KEY_IS_ANONYMOUS = "is_anonymous"
	private const val KEY_ANONYMOUS_NAME = "anonymous_name"
	private val GUEST_NAME_REGEX = Regex("^Guest\\s+\\d+$")

	private lateinit var prefs: SharedPreferences

	private fun isInitialized(): Boolean = ::prefs.isInitialized

	fun initialize(context: Context) {
		prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
	}

	fun getToken(): String? {
		if (!isInitialized()) return null
		return prefs.getString(KEY_TOKEN, null)
	}

	fun getUid(): String? {
		if (!isInitialized()) return null
		return prefs.getString(KEY_UID, null)
	}

	fun getUsername(): String? {
		if (!isInitialized()) return null
		return prefs.getString(KEY_USERNAME, null)
	}

	fun getEmail(): String? {
		if (!isInitialized()) return null
		return prefs.getString(KEY_EMAIL, null)
	}

	fun isAnonymous(): Boolean {
		if (!isInitialized()) return false
		return prefs.getBoolean(KEY_IS_ANONYMOUS, false)
	}

	fun getAnonymousName(): String? {
		if (!isInitialized()) return null
		return prefs.getString(KEY_ANONYMOUS_NAME, null)
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
			prefs.edit().apply {
				putBoolean(KEY_IS_ANONYMOUS, true)
				putString(KEY_ANONYMOUS_NAME, guestName)
				apply()
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

		prefs.edit().apply {
			remove(KEY_TOKEN)
			remove(KEY_UID)
			remove(KEY_USERNAME)
			remove(KEY_EMAIL)
			putBoolean(KEY_IS_ANONYMOUS, true)
			putString(KEY_ANONYMOUS_NAME, guestName)
			apply()
		}
	}

	private fun generateGuestName(): String {
		return "Guest ${(1000..9999).random()}"
	}

	private fun extractApiErrorMessage(e: Exception): String {
		if (e is HttpException) {
			val body = e.response()?.errorBody()?.string()
			if (!body.isNullOrBlank()) {
				return try {
					JSONObject(body).optString("message", "Request failed (${e.code()})")
				} catch (_: Exception) {
					"Request failed (${e.code()})"
				}
			}
			return "Request failed (${e.code()})"
		}
		return e.message ?: "Unknown error"
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
			Result.failure(Exception(extractApiErrorMessage(e)))
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
			Result.failure(Exception(extractApiErrorMessage(e)))
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
			Result.failure(Exception(extractApiErrorMessage(e)))
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
				Result.failure(Exception(response.message))
			}
		} catch (e: Exception) {
			clearUserData()
			Result.failure(Exception(extractApiErrorMessage(e)))
		}
	}

	suspend fun getUser(uid: String): Result<UserData> {
		return try {
			val token = getAuthHeader() ?: return Result.failure(Exception("No auth token"))
			val response = RetrofitClient.api.getUser(uid, token)

			if (response.success && response.user != null) {
				Result.success(response.user)
			} else {
				Result.failure(Exception(response.message ?: "Failed to get user"))
			}
		} catch (e: Exception) {
			Result.failure(Exception(extractApiErrorMessage(e)))
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
			Result.failure(Exception(extractApiErrorMessage(e)))
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
			Result.failure(Exception(extractApiErrorMessage(e)))
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
			Result.failure(Exception(extractApiErrorMessage(e)))
		}
	}

	private fun saveUserData(user: UserData, token: String) {
		if (!isInitialized()) return
		prefs.edit().apply {
			putString(KEY_TOKEN, token)
			putString(KEY_UID, user.uid)
			putString(KEY_USERNAME, user.username)
			putString(KEY_EMAIL, user.email)
			putBoolean(KEY_IS_ANONYMOUS, false)
			remove(KEY_ANONYMOUS_NAME)
			apply()
		}
	}

	private fun clearUserData() {
		if (!isInitialized()) return
		prefs.edit().apply {
			remove(KEY_TOKEN)
			remove(KEY_UID)
			remove(KEY_USERNAME)
			remove(KEY_EMAIL)
			remove(KEY_IS_ANONYMOUS)
			remove(KEY_ANONYMOUS_NAME)
			apply()
		}
	}
}
