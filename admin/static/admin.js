/**
 * hAIveMind Admin Panel - Common JavaScript Functions
 * Lance James, Unit 221B Inc.
 */

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
});

function checkAuth() {
    const token = localStorage.getItem('haivemind_token');
    const currentPage = window.location.pathname;
    
    // If no token and not on login page, redirect to login
    if (!token && !currentPage.includes('login.html')) {
        window.location.href = '/admin/login.html';
        return;
    }
    
    // If we have a token and not on login page, verify it's still valid
    if (token && !currentPage.includes('login.html')) {
        fetch('/admin/api/verify', {
            headers: { 'Authorization': `Bearer ${token}` }
        }).then(response => {
            if (!response.ok) {
                localStorage.removeItem('haivemind_token');
                window.location.href = '/admin/login.html';
            }
        }).catch(() => {
            // If verification fails, redirect to login
            localStorage.removeItem('haivemind_token');
            window.location.href = '/admin/login.html';
        });
    }
}

function logout() {
    localStorage.removeItem('haivemind_token');
    window.location.href = '/admin/login.html';
}

async function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem('haivemind_token');
    
    if (!token) {
        throw new Error('No authentication token');
    }
    
    const headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    // If unauthorized, redirect to login
    if (response.status === 401) {
        localStorage.removeItem('haivemind_token');
        window.location.href = '/admin/login.html';
        throw new Error('Authentication failed');
    }
    
    return response;
}

// Utility functions
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function formatDuration(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
}

// Common API error handler
function handleApiError(error, fallbackMessage = 'An error occurred') {
    console.error('API Error:', error);
    if (error.message && error.message !== 'Authentication failed') {
        return error.message;
    }
    return fallbackMessage;
}

// Show toast notifications
function showToast(message, type = 'info') {
    // Create toast element if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
        `;
        document.body.appendChild(toastContainer);
    }
    
    const toast = document.createElement('div');
    toast.style.cssText = `
        background: ${type === 'error' ? '#f8d7da' : type === 'success' ? '#d4edda' : '#d1ecf1'};
        color: ${type === 'error' ? '#721c24' : type === 'success' ? '#155724' : '#0c5460'};
        padding: 12px 20px;
        border-radius: 6px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 5000);
}

// Add CSS animations for toasts
if (!document.getElementById('toast-styles')) {
    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// Real-time updates via WebSocket (if available)
class AdminWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.reconnectAttempts = 0;
        this.listeners = new Map();
    }
    
    connect() {
        const token = localStorage.getItem('haivemind_token');
        if (!token) return;
        
        const wsUrl = `ws://${window.location.host}/admin/ws?token=${token}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Admin WebSocket connected');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('WebSocket message parsing error:', error);
            }
        };
        
        this.ws.onclose = () => {
            console.log('Admin WebSocket disconnected');
            this.scheduleReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts < 10) {
            setTimeout(() => {
                this.reconnectAttempts++;
                this.connect();
            }, Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay));
        }
    }
    
    handleMessage(data) {
        const { type, payload } = data;
        const listeners = this.listeners.get(type) || [];
        listeners.forEach(callback => callback(payload));
    }
    
    on(eventType, callback) {
        if (!this.listeners.has(eventType)) {
            this.listeners.set(eventType, []);
        }
        this.listeners.get(eventType).push(callback);
    }
    
    off(eventType, callback) {
        const listeners = this.listeners.get(eventType) || [];
        const index = listeners.indexOf(callback);
        if (index > -1) {
            listeners.splice(index, 1);
        }
    }
}

// Initialize WebSocket connection for real-time updates
const adminWS = new AdminWebSocket();

// Auto-connect WebSocket if not on login page
if (!window.location.pathname.includes('login.html')) {
    adminWS.connect();
}