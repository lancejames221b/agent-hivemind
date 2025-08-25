/**
 * hAIveMind Control Dashboard - Enhanced JavaScript Functions
 * Lance James, Unit 221B Inc.
 */

// Global state
let currentUserData = null;

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    loadCurrentUser();
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
                localStorage.removeItem('haivemind_user');
                window.location.href = '/admin/login.html';
            } else {
                return response.json();
            }
        }).then(userData => {
            if (userData) {
                localStorage.setItem('haivemind_user', JSON.stringify(userData.user));
                currentUserData = userData.user;
            }
        }).catch(() => {
            // If verification fails, redirect to login
            localStorage.removeItem('haivemind_token');
            localStorage.removeItem('haivemind_user');
            window.location.href = '/admin/login.html';
        });
    }
}

function loadCurrentUser() {
    const userStr = localStorage.getItem('haivemind_user');
    if (userStr) {
        currentUserData = JSON.parse(userStr);
        const userElement = document.getElementById('current-user');
        if (userElement) {
            userElement.textContent = `${currentUserData.username} (${currentUserData.role})`;
        }
    }
}

function logout() {
    localStorage.removeItem('haivemind_token');
    localStorage.removeItem('haivemind_user');
    window.location.href = '/admin/login.html';
}

async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('haivemind_token');
    
    if (!token) {
        throw new Error('No authentication token');
    }
    
    const headers = {
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };

    return fetch(url, {
        ...options,
        headers
    });
}

// Alias for compatibility
const authenticatedFetch = fetchWithAuth;

// Utility Functions
function formatDateTime(isoString) {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    return date.toLocaleString();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showInfo(message) {
    showNotification(message, 'info');
}

function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelectorAll('.notification');
    existing.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return false;
    
    const text = element.textContent || element.value;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showSuccess('Copied to clipboard!');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showSuccess('Copied to clipboard!');
    } catch (err) {
        showError('Failed to copy to clipboard');
    }
    
    document.body.removeChild(textArea);
}

// Modal handling
function closeModal() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

// Close modals when clicking outside
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
});

// Login form handler (for login.html)
async function handleLogin(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const credentials = {
        username: formData.get('username'),
        password: formData.get('password')
    };

    try {
        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(credentials),
        });

        if (response.ok) {
            const result = await response.json();
            
            // Store token and user data
            localStorage.setItem('haivemind_token', result.token);
            localStorage.setItem('haivemind_user', JSON.stringify(result.user));
            
            // Redirect to dashboard
            window.location.href = '/admin/dashboard.html';
        } else {
            const error = await response.json();
            showError(error.detail || 'Login failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Network error during login');
    }
}

// Legacy function names for backward compatibility
const authenticatedFetch = fetchWithAuth;

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
        if (!token) {
            console.log('No authentication token available for WebSocket connection');
            return;
        }
        
        // WebSocket temporarily disabled - endpoint not available in remote_mcp_server.py
        console.log('WebSocket functionality temporarily disabled');
        return;
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/admin/ws?token=${token}`;
        
        console.log('Attempting WebSocket connection to:', wsUrl.replace(/token=[^&]+/, 'token=***'));
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('Admin WebSocket connected successfully');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            showSuccess('Real-time updates connected');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket message received:', data.type);
                this.handleMessage(data);
            } catch (error) {
                console.error('WebSocket message parsing error:', error);
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('Admin WebSocket disconnected:', event.code, event.reason);
            if (event.code === 1008) {
                // Authentication failed
                showError(`WebSocket authentication failed: ${event.reason}`);
                localStorage.removeItem('haivemind_token');
                localStorage.removeItem('haivemind_user');
                window.location.href = '/admin/login.html';
                return;
            }
            showInfo('Real-time updates disconnected. Attempting to reconnect...');
            this.scheduleReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            showError('WebSocket connection error occurred');
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
        
        // Handle built-in message types
        switch (type) {
            case 'connection_established':
                console.log('WebSocket connection established for user:', data.user?.username);
                break;
            case 'pong':
                console.log('WebSocket pong received');
                break;
            case 'stats_update':
                this.updateDashboardStats(data.data);
                break;
            case 'error':
                console.error('WebSocket error:', data.message);
                showError(`Server error: ${data.message}`);
                break;
            default:
                // Handle custom message types via listeners
                const listeners = this.listeners.get(type) || [];
                listeners.forEach(callback => callback(payload || data));
                break;
        }
    }
    
    updateDashboardStats(stats) {
        // Update dashboard statistics if elements exist
        if (stats) {
            const elements = {
                'total-users': stats.total_users,
                'total-devices': stats.total_devices,
                'active-devices': stats.active_devices,
                'total-api-keys': stats.total_api_keys
            };
            
            Object.entries(elements).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element && value !== undefined) {
                    element.textContent = value;
                }
            });
        }
    }
    
    sendPing() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
        }
    }
    
    requestStats() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'get_stats' }));
        }
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
    
    // Send periodic pings to keep connection alive
    setInterval(() => {
        adminWS.sendPing();
    }, 30000); // Every 30 seconds
    
    // Request stats updates periodically
    setInterval(() => {
        adminWS.requestStats();
    }, 60000); // Every minute
}