/**
 * Authentication API calls with CSRF protection
 * YTD-Kopya Frontend Authentication Module
 */

import { secureRequest, securityManager } from './security';

/**
 * Login with email and password (session-based)
 * @param {string} email 
 * @param {string} password 
 * @returns {Promise<Object>} User data and session info
 */
export async function login(email, password) {
    try {
        const response = await secureRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                email: email.trim().toLowerCase(),
                password,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Login failed: ${response.status}`);
        }

        console.info('Login successful');
        return data;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

/**
 * Logout from current session
 * @returns {Promise<void>}
 */
export async function logout() {
    try {
        await secureRequest('/auth/logout', {
            method: 'POST',
        });
        securityManager.clearTokens();
        console.info('Logout successful');
    } catch (error) {
        console.error('Logout error:', error);
        securityManager.clearTokens();
        throw error;
    }
}

/**
 * Get current user info
 * @returns {Promise<Object>} Current user data
 */
export async function getCurrentUser() {
    try {
        const response = await secureRequest('/auth/me', {
            method: 'GET',
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Failed to get user: ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Get current user error:', error);
        throw error;
    }
}

/**
 * Test CSRF protection (for development/testing)
 */
export const testCSRF = () => secureRequest('/auth/csrf-validate', { method: 'POST' });
