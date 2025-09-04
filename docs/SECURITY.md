# YTD-Kopya Security Implementation Guide

Bu doküman, projedeki güvenlik özelliklerini ve kullanımını açıklar.

## 🔐 CSRF Koruması

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

## 🌐 CORS Ayarları

Geliştirme ortamı örneği:
```env
YTD_CORS_ALLOW_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
YTD_CORS_ALLOW_METHODS=GET,POST,PUT,PATCH,DELETE,OPTIONS
```

Üretim ortamında wildcard (`*`) kullanmayın ve gerçek domainleri tanımlayın.
