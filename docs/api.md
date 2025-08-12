# API Documentation

## GET /api/limits/status

Returns the current user's subscription plan and usage limits.

### Authentication
- JWT Bearer token required.

### Response
- **200 OK**
```
{
  "plan": "premium",
  "limits": {
    "daily_requests": {"used": 45, "max": 100, "percent": 45},
    "monthly_requests": {"used": 1200, "max": 3000, "percent": 40}
  }
}
```

### Error Responses
- **401 Unauthorized**: `{ "error": "Kullanıcı bulunamadı." }`
- **403 Forbidden**: `{ "error": "Özellik kapalı." }`
- **500 Internal Server Error**: `{ "error": "Limitler alınamadı." }`
