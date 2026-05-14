package com.example.MVP

import com.example.MVP.models.*
import com.example.MVP.network.RetrofitClient

object FriendsManager {

    suspend fun sendFriendRequestByCode(friendCode: String): Result<FriendRequest> {
        return try {
            val fromUid = AuthManager.getUid()
                ?: return Result.failure(Exception("User not logged in"))
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val lookup = RetrofitClient.api.getUserByFriendCode(friendCode, token)
            val targetUid = lookup.user?.uid
                ?: return Result.failure(Exception(lookup.message ?: "Codigo de amigo invalido"))

            if (targetUid == fromUid) {
                return Result.failure(Exception("Nao podes adicionar-te a ti proprio"))
            }

            val request = SendFriendRequestRequest(fromUid, targetUid)
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

    suspend fun removeFriend(friendUid: String): Result<Unit> {
        return try {
            val userUid = AuthManager.getUid()
                ?: return Result.failure(Exception("User not logged in"))
            val token = AuthManager.getAuthHeader()
                ?: return Result.failure(Exception("No auth token"))

            val request = FriendRequest(
                id = "",
                fromUid = userUid,
                toUid = friendUid,
                status = "pending",
                createdAt = "",
                updatedAt = ""
            )
            val response = RetrofitClient.api.removeFriend(request, token)

            if (response.success) {
                Result.success(Unit)
            } else {
                Result.failure(Exception(response.message ?: "Failed to remove friend"))
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

    suspend fun getFriendCode(): Result<FriendCodeResponse> {
        return try {
            val uid = AuthManager.getUid() ?: return Result.failure(Exception("User not logged in"))
            val token = AuthManager.getAuthHeader() ?: return Result.failure(Exception("No auth token"))

            val response = RetrofitClient.api.getFriendCode(uid, token)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
