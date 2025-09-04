# YTD-Kopya Security Implementation Guide

Bu doküman, projedeki güvenlik özelliklerini ve kullanımını açıklar.

## CSRF Koruması

### Web İstemcileri
```javascript
const tokenResponse = await fetch('/auth/csrf-token', {
    credentials: 'include'
});
const { csrfToken } = await tokenResponse.json();

await fetch('/api/protected-action', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken
    },
    credentials: 'include',
    body: JSON.stringify(data)
});
```

### Mobil/API İstemcileri
```javascript
await fetch('/api/v1/data', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + jwt_token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

## CORS Ayarları

**Development:**
```env
YTD_CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
YTD_CORS_SUPPORTS_CREDENTIALS=true
```

**Production:**
```env
YTD_CORS_ALLOW_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
YTD_CORS_SUPPORTS_CREDENTIALS=true
```

> **Uyarı:** Production'da credentials kullanırken `*` wildcard ASLA kullanmayın!

## Rate Limiting

```env
YTD_RATE_LIMIT_DEFAULT=100/minute
YTD_RATE_LIMIT_LOGIN=5/minute
YTD_RATE_LIMIT_CSRF_TOKEN=50/minute
YTD_RATE_LIMIT_WHITELIST=10.0.0.0/8,172.16.0.0/12
```

## Frontend Kullanımı

### React/Vue/Angular
```javascript
import { securityManager } from './utils/security';

await securityManager.fetchCSRFToken();

const response = await securityManager.secureRequest('/api/data', {
  method: 'POST',
  body: JSON.stringify(payload)
});
```

### Vanilla JavaScript
```javascript
const tokenRes = await fetch('/auth/csrf-token', { credentials: 'include' });
const { csrfToken } = await tokenRes.json();

await fetch('/protected/action', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
  },
  credentials: 'include',
  body: JSON.stringify(data)
});
```

## Test Endpoints

- `GET /auth/csrf-token` - CSRF token al
- `POST /auth/csrf-validate` - CSRF token test et
- `GET /api/v1/ping` - API sağlık kontrolü

