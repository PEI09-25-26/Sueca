# Frontend Security Updates - Implementation Summary

## Overview

Updated the Android frontend to support guest user sessions and work with the new centralized token validation architecture. Guest users can now play games without authentication while still being protected by the security enhancements.

## Key Changes

### 1. Guest Session Management (AuthManager.kt)

**New Component** - Manages authentication for guests and authenticated users

**Features:**
- Creates guest session tokens on first use
- Caches tokens for 25 minutes (JWT TTL is 30 min)
- Stores player ID with token
- Provides token to all API calls via interceptor
- Singleton pattern for app-wide access

**Main Methods:**
```kotlin
// Get or create guest session (called automatically)
val token = authManager.getOrCreateGuestSessionToken("PlayerName")

// Get current token
val token = authManager.getCurrentSessionToken()

// Get player ID
val playerId = authManager.getCurrentPlayerId()

// Clear on logout
authManager.clearSessionToken()
```

### 2. Authorization Interceptor (RetrofitClient.kt)

**Updated Component** - Automatically adds auth header to all API requests

**Changes:**
- Added `AuthInterceptor` class that adds `Authorization: Bearer {token}` header
- Added `initialize(context)` method to set up interceptor
- No more manual header management needed

**Usage:**
```kotlin
// Call once in MainActivity or first Activity
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    RetrofitClient.initialize(this)  // Set up interceptor
    // ... rest of onCreate
}
```

### 3. Guest Session Endpoint (ApiService.kt)

**New Endpoint** - Frontend can request guest session tokens

**Endpoint:**
```kotlin
@POST("/auth/guest_session")
suspend fun createGuestSession(@Body payload: Map<String, String>): GuestSessionResponse
```

### 4. Activities Updated

**MainMenuActivity.kt:**
- Initialize RetrofitClient
- Get guest session before game start

**OnlineMenuActivity.kt:**
- Initialize RetrofitClient
- Get guest session before creating/joining room
- Pass player ID through intent to RoomActivity

### 5. Models (Models.kt)

**New Model** - Guest session response

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

1. **User launches app** → MainMenuActivity
2. **RetrofitClient initialized** → Auth interceptor ready
3. **User enters game mode** → OnlineMenuActivity or starts directly
4. **AuthManager creates guest session** → Calls `/auth/guest_session`
5. **Backend returns** → session_token + player_id
6. **Token cached in memory** → Valid for 25 minutes
7. **User creates/joins room** → All requests include token via interceptor
8. **Token expires** → Refreshed on next API call
9. **App closes** → Token cleared (no persistence)

## Security Benefits

✓ **No Credentials Needed** - Guests play without login  
✓ **Session-Scoped** - Each guest has unique session token  
✓ **Automatic Authorization** - Interceptor adds headers transparently  
✓ **Token Expiration** - 30-minute TTL prevents long-lived tokens  
✓ **Revocation Support** - Tokens can be revoked server-side via JTI denylist  
✓ **No Local Storage** - Tokens only in memory (cleared on app close)  
✓ **Rate Limiting** - Backend can rate-limit by token  

## Files Modified

| File | Changes |
|------|---------|
| `AuthManager.kt` | NEW - Guest session management |
| `RetrofitClient.kt` | UPDATED - Added AuthInterceptor + initialize() |
| `ApiService.kt` | UPDATED - Added createGuestSession() endpoint |
| `MainMenuActivity.kt` | UPDATED - Initialize + get session |
| `OnlineMenuActivity.kt` | UPDATED - Initialize + get session |
| `Models.kt` | UPDATED - Added GuestSessionResponse |
| `FRONTEND_SECURITY_INTEGRATION.md` | NEW - Complete guide |

## Backend Coordination

**Ensure backend has:**
- ✓ `POST /auth/guest_session` endpoint (NEW in gateway routes)
- ✓ Session manager that creates sessions
- ✓ Authorization header checking on all endpoints
- ✓ `SUECA_JWT_SECRET` environment variable set

## Testing Checklist

- [ ] App launches without errors
- [ ] `RetrofitClient.initialize()` called in MainActivity
- [ ] Guest session endpoint returns token
- [ ] Token cached (reused within 25 min)
- [ ] Token includes in Authorization header
- [ ] Create room works with token
- [ ] Join room works with token
- [ ] WebSocket connects with token
- [ ] Token refreshes when expired
- [ ] App closes → token cleared

## Deployment Steps

1. **Backend:**
   - Deploy updated `apps/gateway/routes/auth_routes.py` with `/auth/guest_session` endpoint
   - Ensure `SUECA_JWT_SECRET` is set

2. **Frontend:**
   - Build and deploy updated APK
   - Ensure `RetrofitClient.initialize()` called early in MainMenuActivity

3. **Verify:**
   - Test guest user flow from app launch to gameplay
   - Check Logcat for "Authorization: Bearer" in requests
   - Verify token obtained from `/auth/guest_session`

## Backward Compatibility

- Existing game logic unchanged
- Room creation/joining same as before
- Additional: Session token automatically included in requests
- Interceptor skips `/auth/*` endpoints (no double auth)

## Future Enhancements

1. **User Login** - Implement user login flow
   - Call `/auth/login` with credentials
   - Get JWT token + player ID
   - Use same session mechanism

2. **Profile Management** - Update player profile
   - Call `/user/{uid}` endpoints
   - Uses same auth token

3. **Persistent Sessions** - Save token to device
   - Encrypted SharedPreferences
   - Auto-login on app restart

4. **Social Features** - Friend codes, etc.
   - Use existing endpoints with auth

## Troubleshooting

**"Token validation failed"**
- Check `RetrofitClient.initialize()` called
- Verify backend auth service running
- Check logs for 401 responses

**"No session token"**
- `getOrCreateGuestSessionToken()` not called
- Backend `/auth/guest_session` not implemented
- Network unreachable

**"Guest session token expired"**
- Normal after 30 minutes
- App will auto-refresh on next API call

## Code Examples

**Initialize RetrofitClient:**
```kotlin
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // Set up auth interceptor
        RetrofitClient.initialize(this)
    }
}
```

**Get Guest Session:**
```kotlin
lifecycleScope.launch {
    val authManager = AuthManager.getInstance(context)
    val token = authManager.getOrCreateGuestSessionToken("PlayerName")
    val playerId = authManager.getCurrentPlayerId()
    
    // All subsequent API calls now include auth header
    val response = GatewayClient.createRoom()
}
```

**Use Authenticated API:**
```kotlin
// No need to manually add Authorization header
// AuthInterceptor does it automatically
val status = RetrofitClient.api.getStatus(gameId)
```

## Questions?

Refer to:
- `FRONTEND_SECURITY_INTEGRATION.md` - Detailed architecture
- Backend: `CENTRALIZED_AUTH_ARCHITECTURE.md` - Auth service design
- Backend: `IMPLEMENTATION_SUMMARY.md` - Deployment guide
