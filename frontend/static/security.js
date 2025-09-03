/**
 * Frontend security utilities for XSS prevention
 */

class SecurityUtils {
    /**
     * Escape HTML to prevent XSS attacks
     * @param {string} unsafe - Unsafe HTML string
     * @returns {string} - Safe HTML string
     */
    static escapeHtml(unsafe) {
        if (typeof unsafe !== 'string') return unsafe;
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;')
            .replace(/\//g, '&#x2F;');
    }

    /**
     * Sanitize input for display
     * @param {string} input - User input
     * @returns {string} - Sanitized input
     */
    static sanitizeInput(input) {
        if (!input) return '';
        let sanitized = input.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        sanitized = sanitized.replace(/javascript:/gi, '');
        sanitized = sanitized.replace(/\s*on\w+\s*=\s*[^>]*/gi, '');
        return this.escapeHtml(sanitized);
    }

    /**
     * Validate JSON response to prevent XSS
     * @param {object} jsonData - JSON response data
     * @returns {object} - Sanitized JSON data
     */
    static sanitizeJsonResponse(jsonData) {
        if (typeof jsonData !== 'object' || jsonData === null) {
            return jsonData;
        }
        if (Array.isArray(jsonData)) {
            return jsonData.map((item) => this.sanitizeJsonResponse(item));
        }
        const sanitized = {};
        for (const [key, value] of Object.entries(jsonData)) {
            if (typeof value === 'string') {
                sanitized[key] = this.escapeHtml(value);
            } else if (typeof value === 'object') {
                sanitized[key] = this.sanitizeJsonResponse(value);
            } else {
                sanitized[key] = value;
            }
        }
        return sanitized;
    }

    /**
     * Safe DOM insertion
     * @param {HTMLElement} element - Target element
     * @param {string} content - Content to insert
     */
    static safeSetContent(element, content) {
        if (!element) return;
        element.textContent = content;
    }

    /**
     * Safe HTML insertion with limited allowed tags
     * @param {HTMLElement} element - Target element
     * @param {string} htmlContent - HTML content
     */
    static safeSetHTML(element, htmlContent) {
        if (!element || !htmlContent) return;
        const temp = document.createElement('div');
        temp.innerHTML = htmlContent;
        const scripts = temp.querySelectorAll('script');
        scripts.forEach((script) => script.remove());
        const allElements = temp.querySelectorAll('*');
        allElements.forEach((el) => {
            Array.from(el.attributes).forEach((attr) => {
                if (attr.name.startsWith('on') || attr.value.includes('javascript:')) {
                    el.removeAttribute(attr.name);
                }
            });
        });
        element.innerHTML = temp.innerHTML;
    }

    /**
     * Validate and sanitize form data before submission
     * @param {FormData} formData - Form data to validate
     * @returns {FormData} - Sanitized form data
     */
    static sanitizeFormData(formData) {
        const sanitizedData = new FormData();
        for (const [key, value] of formData.entries()) {
            if (typeof value === 'string') {
                sanitizedData.append(key, this.sanitizeInput(value));
            } else {
                sanitizedData.append(key, value);
            }
        }
        return sanitizedData;
    }

    /**
     * Setup Content Security Policy violation reporting
     */
    static setupCSPReporting() {
        document.addEventListener('securitypolicyviolation', (e) => {
            console.warn('CSP Violation:', {
                blockedURI: e.blockedURI,
                violatedDirective: e.violatedDirective,
                originalPolicy: e.originalPolicy,
                sourceFile: e.sourceFile,
                lineNumber: e.lineNumber
            });
            fetch('/api/security/csp-violation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    blockedURI: e.blockedURI,
                    violatedDirective: e.violatedDirective,
                    sourceFile: e.sourceFile,
                    lineNumber: e.lineNumber
                })
            }).catch((err) => console.error('Failed to report CSP violation:', err));
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    SecurityUtils.setupCSPReporting();
});
