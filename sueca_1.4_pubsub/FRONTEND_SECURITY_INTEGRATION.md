# Frontend Security Integration Guide

## Overview

The Android frontend has been updated to support the new centralized token validation architecture. The app now:

1. **Supports Guest Users** - No login required, temporary session tokens for gameplay
2. **Automatically Manages Sessions** - Token lifecycle handled by `AuthManager`
3. **Adds Authorization Headers** - All API calls include session token via `AuthInterceptor`
4. **Supports Future User Authentication** - Login endpoint ready (to be implemented)

## Architecture

### Authentication Flow (Guest Users)

```
┌─────────────────┐
│  OnlineMenu     │
│  or             │
│  MainMenu       │
└────────┬────────┘
         │
         │ 1. User enters name & clicks Create/Join
         ▼
┌──────────────────────────────┐
│  AuthManager.                │
│  getOrCreateGuestSession     │
│  Token()                      │
└────────┬─────────────────────┘
         │
         │ 2. Call /auth/guest_session
         ▼
┌──────────────────────────────┐
│  Auth Service                │
│  - Generate player_id        │
│  - Create session            │
│  - Return JWT token          │
└────────┬─────────────────────┘
         │
         │ 3. Return (token, playerId)
         ▼
┌──────────────────────────────┐
│  AuthManager                 │
│  Stores token + playerId     │
│  in memory                   │
└────────┬─────────────────────┘
         │
         │ 4. All subsequent API calls
         │    include Authorization header
         ▼
┌──────────────────────────────┐
│  AuthInterceptor             │
│  Adds "Bearer {token}"       │
│  to request headers          │
└────────┬─────────────────────┘
         │
         ▼
    Gateway Service
    ✓ Creates room
    ✓ Joins game
    ✓ WebSocket auth
```

## Components

### 1. AuthManager.kt (NEW)

Manages guest and authenticated sessions.

**Key Methods:**
- `getOrCreateGuestSessionToken(playerName)` - Gets or creates guest session
- `getCurrentSessionToken()` - Returns current token
- `getCurrentPlayerId()` - Returns current player ID
- `clearSessionToken()` - Clears session
- `setUserToken(token, playerId, expirySeconds)` - Set user login token (future)

**Features:**
- Caches tokens in memory (25-minute TTL with 5-minute buffer)
- Singleton pattern for app-wide access
- Thread-safe

**Usage:**
```kotlin
val authManager = AuthManager.getInstance(context)
val token = authManager.getOrCreateGuestSessionToken("PlayerName")
val playerId = authManager.getCurrentPlayerId()
```

### 2. RetrofitClient.kt (UPDATED)

Now includes auth interceptor and initialization method.

**Changes:**
- Added `AuthInterceptor` class - adds Authorization header to all requests
- Added `initialize(context)` method - must be called in MainActivity or OnlineMenuActivity
- `initialize()` is called once to set up the interceptor

**Usage:**
```kotlin
// In MainMenuActivity or OnlineMenuActivity onCreate():
RetrofitClient.initialize(this)

// Now all API calls automatically include auth header
```

### 3. AuthInterceptor.kt (EMBEDDED in RetrofitClient)

Interceptor that adds Authorization header with session token.

**Logic:**
- Skips auth endpoints (`/auth/*`)
- Gets current token from AuthManager
- Adds `Authorization: Bearer {token}` header if token exists
- Allows requests without token if guest not yet initialized

**Handles:**
- Missing token gracefully
- Expired tokens (will trigger refresh on next call)
- Multiple concurrent requests

### 4. ApiService.kt (UPDATED)

Added guest session endpoint:
```kotlin
@POST("/auth/guest_session")
suspend fun createGuestSession(@Body payload: Map<String, String>): GuestSessionResponse
```

### 5. OnlineMenuActivity.kt (UPDATED)

Now initializes RetrofitClient and gets guest session before operations.

**Changes:**
- Call `RetrofitClient.initialize(this)` in onCreate()
- Call `authManager.getOrCreateGuestSessionToken(playerName)` before creating/joining room
- Pass `authManager.getCurrentPlayerId()` when creating room intent

### 6. MainMenuActivity.kt (UPDATED)

Similar updates for consistency.

### 7. Models.kt (UPDATED)

Added `GuestSessionResponse` data class:
```kotlin
data class GuestSessionResponse(
    val success: Boolean,
    val session_token: String,
    val game_id: String?,
    val player_id: String,
    val expires_at: String
)
```

## Guest User Flow

1. **App Launches** → `MainMenuActivity` or `OnlineMenuActivity`
2. **Initialize** → `RetrofitClient.initialize(this)`
3. **User enters name & clicks button**
4. **Get Session** → `authManager.getOrCreateGuestSessionToken("PlayerName")`
   - Calls `/auth/guest_session` if needed
   - Backend generates guest player ID
   - Token cached for 25 minutes
5. **All subsequent API calls** automatically include `Authorization: Bearer {token}`
6. **Token expires** → Next call triggers refresh
7. **App closed** → Token cleared from memory (not persisted)

## Authenticated User Flow (Future)

For future user login support:

```kotlin
// After successful login (via /auth/login endpoint):
val authManager = AuthManager.getInstance(context)
authManager.setUserToken(
    token = jwtToken,
    playerId = uid,
    expirySeconds = 3600  // JWT expiry
)

// Now all subsequent calls use this token instead
```

## Token Lifecycle

| Event | Action |
|-------|--------|
| App launches | No token |
| User enters name | `getOrCreateGuestSessionToken()` called |
| Token obtained | Cached in `AuthManager` |
| API call made | `AuthInterceptor` adds `Authorization: Bearer {token}` |
| Token expires (30 min) | Cached expiry expires |
| Next API call | `AuthManager` detects expiry, triggers refresh |
| New token obtained | Cached, used in next request |
| App closes | Token cleared |
| App reopens | New token requested |

## Security Features

1. **No hardcoded secrets** - Tokens generated by backend
2. **Automatic authorization** - Interceptor adds headers transparently
3. **Token expiry** - 30-minute JWT TTL + 5-minute buffer
4. **No persistence** - Guest tokens not saved to disk
5. **Per-session** - Each app launch gets new token
6. **Scope-based** - Guest tokens limited to game operations
7. **JTI tracking** - Each token has unique JTI for revocation

## Troubleshooting

### "Token validation failed"
- Ensure `RetrofitClient.initialize()` called in MainActivity
- Verify auth service is running on backend
- Check `AUTH_SERVICE_URL` environment variable

### "invalid or expired session token"
- Guest session may have expired (30 min)
- Restart app to get new token
- Or manually call `getOrCreateGuestSessionToken()` again

### "Connection refused to auth service"
- Auth service not running
- Check `apps/auth/main.py` is started
- Verify `SUECA_JWT_SECRET` environment variable set

### No Authorization header in requests
- `RetrofitClient.initialize()` not called
- Check that initialization happens early in MainActivity

## Testing

### Test Guest User Flow

1. Run backend services
2. Run Android app
3. MainMenuActivity loads
4. Select "Online" → OnlineMenuActivity
5. Enter name (or leave blank for random)
6. Click "Create Room"
   - Should call `/auth/guest_session`
   - Should create room
   - Should navigate to RoomActivity
7. Open Android Studio Logcat
   - Should see HTTP requests with `Authorization: Bearer ...` header

### Test Token Caching

1. Create guest session
2. Wait 1 minute
3. Make another API call
4. Should use same token (no new `/auth/guest_session` call)

### Test Token Refresh

1. Create guest session
2. Manually set expiry time to current time in AuthManager (for testing)
3. Make another API call
4. Should call `/auth/guest_session` again for new token

## Environment Variables

No new environment variables needed on frontend. Backend requires:

- `SECRET_KEY` - For user access tokens
- `SUECA_JWT_SECRET` - For session/game tokens
- `SUECA_SERVICE_JWT_SECRET` - For service tokens

## Migration from Old Frontend

If migrating from a frontend without auth:

1. Add `RetrofitClient.initialize(context)` to MainActivity
2. Add `authManager.getOrCreateGuestSessionToken()` before room operations
3. Remove any manual token handling code
4. Replace any hardcoded `Authorization` headers
5. Test guest user flow

## Future Enhancements

1. **User Login** - Implement `/auth/login` endpoint call
2. **Token Refresh** - Add refresh token endpoint for extended sessions
3. **Persistent Sessions** - Save token to SharedPreferences (with encryption)
4. **Account Management** - Link guest sessions to user accounts
5. **Profile Management** - Update profile via `/user/{uid}` endpoint
6. **Logout** - Call `/auth/logout` endpoint to revoke token

## API Reference

### Guest Session Endpoint

**Request:**
```
POST /auth/guest_session
Content-Type: application/json

{
  "player_name": "PlayerName"  // optional
}
```

**Response:**
```json
{
  "success": true,
  "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "player_id": "guest_a1b2c3d4",
  "game_id": null,
  "expires_at": "2026-05-16T10:35:00Z"
}
```

### Authorized Request Example

```
POST /game/command/join
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "game_id": "SALA001",
  "mode": "virtual",
  "payload": {
    "name": "PlayerName",
    "position": "North"
  }
}
```

## Implementation Checklist

- [x] Add `AuthManager.kt` for session management
- [x] Add `AuthInterceptor` to `RetrofitClient.kt`
- [x] Add `initialize()` method to `RetrofitClient`
- [x] Add `/auth/guest_session` endpoint to `ApiService`
- [x] Add `GuestSessionResponse` model
- [x] Update `MainMenuActivity` to initialize and get session
- [x] Update `OnlineMenuActivity` to initialize and get session
- [ ] Test guest user flow end-to-end
- [ ] Test token caching and refresh
- [ ] Test multiple concurrent requests
- [ ] Future: Implement user login flow
