package com.example.MVP

import com.example.MVP.models.*
import com.example.MVP.network.RetrofitClient

object FriendsManager {

    suspend fun sendFriendRequestByUsername(toUsername: String): Result<FriendRequest> {
        return try {
            val fromUid = AuthManager.getUid()
                ?: return Result.failure(Exception("User not logged in"))
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val request = SendFriendRequestByUsernameRequest(fromUid, toUsername)
            val response = RetrofitClient.api.sendFriendRequestByUsername(request, token)

            if (response.success && response.request != null) {
                Result.success(response.request)
            } else {
                Result.failure(Exception(response.message))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun sendFriendRequest(toUid: String): Result<FriendRequest> {
        return try {
            val fromUid = AuthManager.getUid()
                ?: return Result.failure(Exception("User not logged in"))
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val request = SendFriendRequestRequest(fromUid, toUid)
            val response = RetrofitClient.api.sendFriendRequest(request, token)

            if (response.success && response.request != null) {
                Result.success(response.request)
            } else {
                Result.failure(Exception(response.message))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun acceptFriendRequest(requestId: String): Result<Unit> {
        return try {
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val request = AcceptFriendRequestRequest(requestId)
            val response = RetrofitClient.api.acceptFriendRequest(request, token)

            if (response.success) {
                Result.success(Unit)
            } else {
                Result.failure(Exception(response.message))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun declineFriendRequest(requestId: String): Result<Unit> {
        return try {
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val request = DeclineFriendRequestRequest(requestId)
            val response = RetrofitClient.api.declineFriendRequest(request, token)

            if (response.success) {
                Result.success(Unit)
            } else {
                Result.failure(Exception(response.message))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun listFriends(uid: String): Result<List<UserData>> {
        return try {
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val response = RetrofitClient.api.listFriends(uid, token)

            if (response.success && response.friends != null) {
                Result.success(response.friends)
            } else {
                Result.failure(Exception(response.message ?: "Failed to fetch friends"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun listIncomingFriendRequests(uid: String): Result<List<IncomingFriendRequestData>> {
        return try {
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val response = RetrofitClient.api.listFriendRequests(uid, token)

            if (response.success && response.requests != null) {
                Result.success(response.requests)
            } else {
                Result.failure(Exception(response.message ?: "Failed to fetch friend requests"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
