/**
 * Security utilities for CSRF protection and secure API calls
 * YTD-Kopya Frontend Security Module
 */

class SecurityManager {
    constructor() {
        this.csrfToken = null;
        this.tokenExpiresAt = null;
        this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
    }

    /**
     * Fetch CSRF token from server
     * @returns {Promise<string>} CSRF token
     */
    async fetchCSRFToken() {
        try {
            const response = await fetch(`${this.baseURL}/auth/csrf-token`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch CSRF token: ${response.status}`);
            }

            const data = await response.json();
            this.csrfToken = data.csrfToken;
            this.tokenExpiresAt = new Date(data.expiresAt);

            console.info('CSRF token fetched successfully');
            return this.csrfToken;
        } catch (error) {
            console.error('Error fetching CSRF token:', error);
            throw error;
        }
    }

    /**
     * Check if current CSRF token is valid and not expired
     * @returns {boolean}
     */
    isCSRFTokenValid() {
        if (!this.csrfToken || !this.tokenExpiresAt) {
            return false;
        }
        return new Date() < this.tokenExpiresAt;
    }

    /**
     * Get valid CSRF token, fetch new one if needed
     * @returns {Promise<string>}
     */
    async getCSRFToken() {
        if (!this.isCSRFTokenValid()) {
            await this.fetchCSRFToken();
        }
        return this.csrfToken;
    }

    /**
     * Make secure API call with CSRF protection
     * @param {string} url - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Response>}
     */
    async secureRequest(url, options = {}) {
        const method = options.method || 'GET';
        const needsCSRF = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase());

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (needsCSRF) {
            try {
                const token = await this.getCSRFToken();
                headers['X-CSRF-Token'] = token;
            } catch (error) {
                console.error('Failed to get CSRF token:', error);
                throw new Error('CSRF protection failed');
            }
        }

        const response = await fetch(`${this.baseURL}${url}`, {
            ...options,
            headers,
            credentials: 'include',
        });

        if (response.status === 400) {
            const errorData = await response.json().catch(() => ({}));
            if (errorData.error === 'csrf_failed') {
                console.warn('CSRF validation failed, retrying with fresh token...');
                this.csrfToken = null;
                return this.secureRequest(url, options);
            }
        }

        return response;
    }

    /**
     * Clear stored security tokens
     */
    clearTokens() {
        this.csrfToken = null;
        this.tokenExpiresAt = null;
    }
}

export const securityManager = new SecurityManager();

export const secureRequest = (url, options) => securityManager.secureRequest(url, options);
export const getCSRFToken = () => securityManager.getCSRFToken();
