// frontend/static/api.js
// Basic axios client with CSRF support
// eslint-disable-next-line no-undef
const apiClient = axios.create({
    baseURL: 'http://localhost:5000',
    withCredentials: true
});

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

apiClient.interceptors.request.use(config => {
    const method = config.method.toLowerCase();
    if (['post', 'put', 'patch', 'delete'].includes(method)) {
        const csrfToken = getCookie('csrf-token');
        if (csrfToken) {
            config.headers['X-CSRF-Token'] = csrfToken;
        }
    }
    return config;
});

async function login(username, password) {
    return apiClient.post('/api/auth/login', { username, password });
}

async function getProtected() {
    return apiClient.get('/api/auth/protected');
}
