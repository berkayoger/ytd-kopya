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
  },
  "reset_at": "2025-02-01T00:00:00"
}
```
### Notes
- `reset_at`: ISO-8601 UTC timestamp for when monthly limits reset.
- Reset day is configurable via environment variable `LIMITS_RESET_DAY` (1–28).  
  If not set, it defaults to the 1st day of each month.

### Error Responses
- **401 Unauthorized**: `{ "error": "Kullanıcı bulunamadı." }`
- **403 Forbidden**: `{ "error": "Özellik kapalı." }`
- **500 Internal Server Error**: `{ "error": "Limitler alınamadı." }`
