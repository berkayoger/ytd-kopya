// YTD Crypto Analysis API Client
class YTDApiClient {
  constructor() {
    // Ortam bazlı API base; yoksa /api
    const apiBase = typeof window !== 'undefined' && window.__API_BASE__;
    this.baseURL = apiBase ? apiBase : '/api';
    // Tek seferde refresh için kilit
    this._refreshPromise = null;

    this.authToken = localStorage.getItem('auth_token');
    this.refreshToken = localStorage.getItem('refresh_token');
    this.headers = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };
    // Varsayılan timeout (ms)
    this.defaultTimeout = 15000;
    this.setupAuthHeaders();
  }

  setupAuthHeaders() {
    if (this.authToken) {
      this.headers['Authorization'] = `Bearer ${this.authToken}`;
    } else {
      delete this.headers['Authorization'];
    }
  }

  persistTokens(accessToken, refreshToken) {
    if (accessToken) {
      this.authToken = accessToken;
      localStorage.setItem('auth_token', accessToken);
    }
    if (refreshToken) {
      this.refreshToken = refreshToken;
      localStorage.setItem('refresh_token', refreshToken);
    }
    this.setupAuthHeaders();
  }

  logout() {
    try {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('refresh_token');
    } catch (e) {
      console.warn('LocalStorage cleanup failed', e);
    }
    this.authToken = null;
    this.refreshToken = null;
    this.setupAuthHeaders();
    if (window?.location?.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  async refreshAuthToken() {
    if (!this.refreshToken) throw new Error('No refresh token available');

    // Halihazırda bir yenileme varsa onu bekle
    if (this._refreshPromise) return this._refreshPromise;

    this._refreshPromise = (async () => {
      try {
        const response = await fetch(`${this.baseURL}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: JSON.stringify({ refresh_token: this.refreshToken })
        });
        if (response.ok) {
          const data = await response.json();
          this.persistTokens(data.access_token, data.refresh_token);
          return true;
        }
      } catch (error) {
        console.error('Token refresh failed:', error);
      } finally {
        this._refreshPromise = null;
      }
      this.logout();
      return false;
    })();

    return this._refreshPromise;
  }

  async makeRequest(endpoint, options = {}) {
    try {
      // Timeout kontrolü
      const controller = new AbortController();
      const timeout = options.timeout ?? this.defaultTimeout;
      const timer = setTimeout(() => controller.abort(), timeout);

      let response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers: { ...this.headers, ...options.headers },
        signal: controller.signal
      });
      clearTimeout(timer);

      if (response.status === 401 && this.refreshToken) {
        // İstemci özelinde yeniden denemeyi kapatmak için: options._noRetry === true
        if (options._noRetry === true) {
          throw new Error('Unauthorized and retry disabled');
        }
        const refreshed = await this.refreshAuthToken();
        // refresh başarısızsa refreshAuthToken içinde logout yapılıyor
        if (refreshed) {
          const controller2 = new AbortController();
          const timer2 = setTimeout(() => controller2.abort(), timeout);
          response = await fetch(`${this.baseURL}${endpoint}`, {
            ...options,
            headers: { ...this.headers, ...options.headers },
            signal: controller2.signal
          });
          clearTimeout(timer2);
        }
      }

      const contentType = response.headers.get('content-type') || '';
      const data = contentType.includes('application/json')
        ? await response.json()
        : await response.text();

      if (response.status === 429) {
        this.handlePlanLimitExceeded(typeof data === 'string' ? { message: data } : data);
        throw new Error((data && data.message) || 'Plan limit exceeded');
      }

      if (response.status === 403) {
        this.handleInsufficientPermissions(typeof data === 'string' ? { message: data } : data);
        throw new Error((data && data.message) || 'Insufficient permissions');
      }

      if (!response.ok) {
        const errMsg = (data && (data.error || data.message)) || 'API request failed';
        throw new Error(errMsg);
      }

      return data;
    } catch (error) {
      // Abort durumunu kullanıcıya daha anlaşılır bildir
      if (error?.name === 'AbortError') {
        this.showNotification('İstek zaman aşımına uğradı. Lütfen ağı kontrol edin.', 'warning');
        throw new Error('Request timed out');
      }
      console.error('API Error:', error);
      throw error;
    }
  }

  handlePlanLimitExceeded(errorData) {
    const message = `Plan limitiniz aşıldı: ${errorData.message || ''}`.trim();
    this.showNotification(message, 'warning');
    if (errorData.upgrade_url) {
      setTimeout(() => {
        if (confirm('Planınızı yükseltmek ister misiniz?')) {
          window.location.href = errorData.upgrade_url;
        }
      }, 1200);
    }
  }

  handleInsufficientPermissions(errorData) {
    const reason = errorData?.reason ? ` (Sebep: ${errorData.reason})` : '';
    const message = `Bu işlem için yetkiniz bulunmuyor${reason}.`;
    this.showNotification(message, 'error');
  }

  showNotification(message, type = 'info') {
    try {
      const el = document.createElement('div');
      el.className = `ytd-toast ytd-toast-${type}`;
      el.textContent = message;
      Object.assign(el.style, {
        position: 'fixed', right: '16px', bottom: '16px', padding: '10px 14px',
        background: type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6',
        color: '#fff', borderRadius: '8px', boxShadow: '0 6px 20px rgba(0,0,0,.2)', zIndex: 9999
      });
      document.body.appendChild(el);
      setTimeout(() => el.remove(), 3200);
    } catch (_) {
      alert(message);
    }
  }

  get(path) { return this.makeRequest(path, { method: 'GET' }); }
  post(path, body) { return this.makeRequest(path, { method: 'POST', body: JSON.stringify(body) }); }
  put(path, body) { return this.makeRequest(path, { method: 'PUT', body: JSON.stringify(body) }); }
  delete(path) { return this.makeRequest(path, { method: 'DELETE' }); }
}

// Singleton export
window.ytdApi = new YTDApiClient();

