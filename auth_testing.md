# Auth-Gated App Testing Playbook

## Step 1: Create Test User & Session
```bash
mongosh --eval "
use('yoocreat');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  _id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  username: 'Test User',
  password_hash: null,
  google_id: 'google_test_123',
  created_at: new Date().toISOString()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API
```bash
# Test auth endpoint
curl -X GET "http://localhost:8001/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3: Browser Testing
```javascript
// Set cookie and navigate
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "localhost",
    "path": "/",
    "httpOnly": true,
    "secure": false,
    "sameSite": "Lax"
}]);
await page.goto("http://localhost:3000");
```

## Critical Fix: ID Schema
- MongoDB stores as '_id'
- Pydantic uses 'id' or maps via Field(alias="_id")

## Success Indicators
✅ /api/auth/me returns user data
✅ Dashboard loads without redirect
✅ CRUD operations work
