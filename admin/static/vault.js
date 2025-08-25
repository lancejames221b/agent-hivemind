/**
 * hAIveMind Credential Vault Dashboard - JavaScript Functions
 * Author: Lance James, Unit 221B
 * Comprehensive vault management with security features and hAIveMind integration
 */

// Global state management
let vaultState = {
    isUnlocked: false,
    sessionTimer: null,
    sessionDuration: 30 * 60, // 30 minutes in seconds
    currentCredentials: [],
    filteredCredentials: [],
    currentPage: 1,
    itemsPerPage: 12,
    searchQuery: '',
    filters: {
        environment: '',
        type: '',
        status: ''
    },
    selectedCredential: null,
    darkMode: localStorage.getItem('vault_dark_mode') === 'true'
};

// Initialize vault dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeVault();
    setupEventListeners();
    checkVaultStatus();
});

/**
 * Initialize vault dashboard
 */
function initializeVault() {
    // Apply dark mode if enabled
    if (vaultState.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
        updateDarkModeIcon();
    }
    
    // Check if vault is already unlocked
    const vaultToken = sessionStorage.getItem('vault_token');
    if (vaultToken) {
        unlockVaultInterface();
        loadCredentials();
    } else {
        showVaultUnlockModal();
    }
    
    // Setup session timer
    setupSessionTimer();
    
    // Load initial data
    loadVaultStats();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('credentialSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(searchCredentials, 300));
    }
    
    // Filter functionality
    const filters = ['environmentFilter', 'typeFilter', 'statusFilter'];
    filters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.addEventListener('change', filterCredentials);
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Session activity tracking
    document.addEventListener('click', resetSessionTimer);
    document.addEventListener('keypress', resetSessionTimer);
    
    // Clipboard security
    document.addEventListener('copy', handleClipboardSecurity);
    
    // Screen recording detection (basic)
    if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
        detectScreenRecording();
    }
}

/**
 * Check vault status
 */
async function checkVaultStatus() {
    try {
        const response = await fetch('/api/v1/vault/status', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const status = await response.json();
            updateVaultStatusBar(status);
        }
    } catch (error) {
        console.error('Error checking vault status:', error);
        showNotification('Failed to check vault status', 'error');
    }
}

/**
 * Show vault unlock modal
 */
function showVaultUnlockModal() {
    const modal = document.getElementById('vaultUnlockModal');
    const mainContent = document.getElementById('vaultMainContent');
    
    if (modal && mainContent) {
        modal.classList.add('show');
        mainContent.style.display = 'none';
        
        // Focus on password input
        setTimeout(() => {
            const passwordInput = document.getElementById('masterPassword');
            if (passwordInput) {
                passwordInput.focus();
            }
        }, 300);
    }
}

/**
 * Unlock vault
 */
async function unlockVault(event) {
    event.preventDefault();
    
    const masterPassword = document.getElementById('masterPassword').value;
    const rememberSession = document.getElementById('rememberSession').checked;
    
    if (!masterPassword) {
        showNotification('Please enter your master password', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/v1/vault/unlock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                master_password: masterPassword,
                remember_session: rememberSession
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Store vault token
            sessionStorage.setItem('vault_token', result.vault_token);
            if (rememberSession) {
                localStorage.setItem('vault_remember', 'true');
            }
            
            // Unlock interface
            unlockVaultInterface();
            
            // Load credentials
            await loadCredentials();
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('vault_unlock', {
                action: 'vault_unlocked',
                timestamp: new Date().toISOString(),
                remember_session: rememberSession
            });
            
            showNotification('Vault unlocked successfully', 'success');
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to unlock vault', 'error');
            
            // Clear password field
            document.getElementById('masterPassword').value = '';
        }
    } catch (error) {
        console.error('Error unlocking vault:', error);
        showNotification('Failed to unlock vault', 'error');
    }
}

/**
 * Unlock vault interface
 */
function unlockVaultInterface() {
    const modal = document.getElementById('vaultUnlockModal');
    const mainContent = document.getElementById('vaultMainContent');
    
    if (modal && mainContent) {
        modal.classList.remove('show');
        mainContent.style.display = 'block';
        vaultState.isUnlocked = true;
        
        // Update status bar
        updateVaultStatusIndicator(true);
        
        // Start session timer
        startSessionTimer();
    }
}

/**
 * Lock vault
 */
async function lockVault() {
    try {
        // Clear vault token
        sessionStorage.removeItem('vault_token');
        localStorage.removeItem('vault_remember');
        
        // Lock interface
        lockVaultInterface();
        
        // Notify server
        await fetch('/api/v1/vault/lock', {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        // Store hAIveMind memory
        await storeHAIveMindMemory('vault_lock', {
            action: 'vault_locked',
            timestamp: new Date().toISOString()
        });
        
        showNotification('Vault locked', 'info');
    } catch (error) {
        console.error('Error locking vault:', error);
    }
}

/**
 * Lock vault interface
 */
function lockVaultInterface() {
    vaultState.isUnlocked = false;
    clearSessionTimer();
    updateVaultStatusIndicator(false);
    showVaultUnlockModal();
    
    // Clear sensitive data
    vaultState.currentCredentials = [];
    vaultState.filteredCredentials = [];
    vaultState.selectedCredential = null;
    
    // Clear credential grid
    const credentialsGrid = document.getElementById('credentialsGrid');
    if (credentialsGrid) {
        credentialsGrid.innerHTML = '<div class="loading-placeholder"><i class="fas fa-lock"></i><p>Vault is locked</p></div>';
    }
}

/**
 * Session timer management
 */
function setupSessionTimer() {
    const timerElement = document.getElementById('sessionTimer');
    if (!timerElement) return;
    
    vaultState.sessionTimer = setInterval(() => {
        if (vaultState.sessionDuration <= 0) {
            lockVault();
            return;
        }
        
        vaultState.sessionDuration--;
        updateSessionTimerDisplay();
    }, 1000);
}

function startSessionTimer() {
    vaultState.sessionDuration = 30 * 60; // Reset to 30 minutes
    updateSessionTimerDisplay();
}

function resetSessionTimer() {
    if (vaultState.isUnlocked) {
        vaultState.sessionDuration = 30 * 60;
        updateSessionTimerDisplay();
    }
}

function clearSessionTimer() {
    if (vaultState.sessionTimer) {
        clearInterval(vaultState.sessionTimer);
        vaultState.sessionTimer = null;
    }
}

function updateSessionTimerDisplay() {
    const timerElement = document.getElementById('sessionTimer');
    if (!timerElement) return;
    
    const minutes = Math.floor(vaultState.sessionDuration / 60);
    const seconds = vaultState.sessionDuration % 60;
    timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    // Warning when less than 5 minutes
    if (vaultState.sessionDuration <= 300) {
        timerElement.style.color = 'var(--vault-warning)';
        if (vaultState.sessionDuration <= 60) {
            timerElement.style.color = 'var(--vault-danger)';
        }
    } else {
        timerElement.style.color = '';
    }
}

/**
 * Load credentials from API
 */
async function loadCredentials() {
    if (!vaultState.isUnlocked) return;
    
    try {
        showLoadingState();
        
        const response = await fetch('/api/v1/vault/credentials', {
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            const credentials = await response.json();
            vaultState.currentCredentials = credentials;
            vaultState.filteredCredentials = credentials;
            
            renderCredentials();
            updatePagination();
            updateVaultStats();
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('credentials_loaded', {
                action: 'credentials_loaded',
                count: credentials.length,
                timestamp: new Date().toISOString()
            });
        } else if (response.status === 401) {
            // Vault token expired
            lockVault();
        } else {
            throw new Error('Failed to load credentials');
        }
    } catch (error) {
        console.error('Error loading credentials:', error);
        showNotification('Failed to load credentials', 'error');
        showErrorState();
    }
}

/**
 * Search credentials
 */
function searchCredentials() {
    const searchInput = document.getElementById('credentialSearch');
    if (!searchInput) return;
    
    vaultState.searchQuery = searchInput.value.toLowerCase();
    applyFilters();
    
    // Show/hide clear button
    const clearButton = document.querySelector('.search-clear');
    if (clearButton) {
        clearButton.style.display = vaultState.searchQuery ? 'block' : 'none';
    }
}

/**
 * Clear search
 */
function clearSearch() {
    const searchInput = document.getElementById('credentialSearch');
    if (searchInput) {
        searchInput.value = '';
        vaultState.searchQuery = '';
        applyFilters();
        
        const clearButton = document.querySelector('.search-clear');
        if (clearButton) {
            clearButton.style.display = 'none';
        }
    }
}

/**
 * Filter credentials
 */
function filterCredentials() {
    // Update filter state
    vaultState.filters.environment = document.getElementById('environmentFilter')?.value || '';
    vaultState.filters.type = document.getElementById('typeFilter')?.value || '';
    vaultState.filters.status = document.getElementById('statusFilter')?.value || '';
    
    applyFilters();
}

/**
 * Apply filters and search
 */
function applyFilters() {
    let filtered = vaultState.currentCredentials;
    
    // Apply search
    if (vaultState.searchQuery) {
        filtered = filtered.filter(credential => 
            credential.name.toLowerCase().includes(vaultState.searchQuery) ||
            credential.description?.toLowerCase().includes(vaultState.searchQuery) ||
            credential.service.toLowerCase().includes(vaultState.searchQuery) ||
            credential.tags?.some(tag => tag.toLowerCase().includes(vaultState.searchQuery))
        );
    }
    
    // Apply environment filter
    if (vaultState.filters.environment) {
        filtered = filtered.filter(credential => 
            credential.environment === vaultState.filters.environment
        );
    }
    
    // Apply type filter
    if (vaultState.filters.type) {
        filtered = filtered.filter(credential => 
            credential.credential_type === vaultState.filters.type
        );
    }
    
    // Apply status filter
    if (vaultState.filters.status) {
        filtered = filtered.filter(credential => {
            const status = getCredentialStatus(credential);
            return status === vaultState.filters.status;
        });
    }
    
    vaultState.filteredCredentials = filtered;
    vaultState.currentPage = 1;
    
    renderCredentials();
    updatePagination();
}

/**
 * Reset filters
 */
function resetFilters() {
    // Clear search
    const searchInput = document.getElementById('credentialSearch');
    if (searchInput) {
        searchInput.value = '';
    }
    
    // Clear filters
    const filters = ['environmentFilter', 'typeFilter', 'statusFilter'];
    filters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.value = '';
        }
    });
    
    // Reset state
    vaultState.searchQuery = '';
    vaultState.filters = { environment: '', type: '', status: '' };
    vaultState.filteredCredentials = vaultState.currentCredentials;
    vaultState.currentPage = 1;
    
    renderCredentials();
    updatePagination();
    
    // Hide clear button
    const clearButton = document.querySelector('.search-clear');
    if (clearButton) {
        clearButton.style.display = 'none';
    }
}

/**
 * Render credentials grid
 */
function renderCredentials() {
    const credentialsGrid = document.getElementById('credentialsGrid');
    if (!credentialsGrid) return;
    
    const startIndex = (vaultState.currentPage - 1) * vaultState.itemsPerPage;
    const endIndex = startIndex + vaultState.itemsPerPage;
    const pageCredentials = vaultState.filteredCredentials.slice(startIndex, endIndex);
    
    if (pageCredentials.length === 0) {
        credentialsGrid.innerHTML = `
            <div class="loading-placeholder">
                <i class="fas fa-search"></i>
                <p>No credentials found</p>
                <button class="btn btn-primary" onclick="showCreateCredentialModal()">
                    <i class="fas fa-plus"></i> Create First Credential
                </button>
            </div>
        `;
        return;
    }
    
    credentialsGrid.innerHTML = pageCredentials.map(credential => 
        renderCredentialCard(credential)
    ).join('');
}

/**
 * Render individual credential card
 */
function renderCredentialCard(credential) {
    const status = getCredentialStatus(credential);
    const statusClass = status.toLowerCase().replace(' ', '-');
    const typeIcon = getCredentialTypeIcon(credential.credential_type);
    const environmentBadge = getEnvironmentBadge(credential.environment);
    
    return `
        <div class="credential-card ${statusClass}" onclick="viewCredential('${credential.id}')" data-credential-id="${credential.id}">
            <div class="credential-header">
                <div class="credential-title">
                    <h3>${escapeHtml(credential.name)}</h3>
                    <p>${escapeHtml(credential.description || '')}</p>
                </div>
                <div class="credential-type-badge">
                    <i class="${typeIcon}"></i> ${credential.credential_type.replace('_', ' ').toUpperCase()}
                </div>
            </div>
            
            <div class="credential-meta">
                <div class="credential-meta-item">
                    <i class="fas fa-server"></i>
                    <span>${escapeHtml(credential.service)}</span>
                </div>
                <div class="credential-meta-item">
                    <i class="fas fa-layer-group"></i>
                    <span>${environmentBadge}</span>
                </div>
                <div class="credential-meta-item">
                    <i class="fas fa-calendar"></i>
                    <span>${formatDate(credential.created_at)}</span>
                </div>
                ${credential.expires_at ? `
                <div class="credential-meta-item">
                    <i class="fas fa-clock"></i>
                    <span>Expires ${formatDate(credential.expires_at)}</span>
                </div>
                ` : ''}
            </div>
            
            ${credential.tags && credential.tags.length > 0 ? `
            <div class="credential-tags">
                ${credential.tags.map(tag => `<span class="credential-tag">${escapeHtml(tag)}</span>`).join('')}
            </div>
            ` : ''}
            
            <div class="credential-status ${status.toLowerCase().replace(' ', '-')}">
                <i class="fas ${getStatusIcon(status)}"></i>
                <span>${status}</span>
            </div>
            
            <div class="credential-actions" onclick="event.stopPropagation()">
                <button class="credential-action-btn" onclick="viewCredential('${credential.id}')" title="View Details">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="credential-action-btn" onclick="editCredential('${credential.id}')" title="Edit">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="credential-action-btn" onclick="copyCredential('${credential.id}')" title="Copy">
                    <i class="fas fa-copy"></i> Copy
                </button>
                <button class="credential-action-btn danger" onclick="deleteCredential('${credential.id}')" title="Delete">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `;
}

/**
 * Show create credential modal
 */
function showCreateCredentialModal() {
    const modal = document.getElementById('credentialModal');
    const title = document.getElementById('credentialModalTitle');
    const form = document.getElementById('credentialForm');
    
    if (modal && title && form) {
        title.textContent = 'Create New Credential';
        form.reset();
        vaultState.selectedCredential = null;
        
        // Clear dynamic fields
        const fieldsContainer = document.getElementById('credentialFields');
        if (fieldsContainer) {
            fieldsContainer.innerHTML = '';
        }
        
        modal.classList.add('show');
        
        // Focus on name input
        setTimeout(() => {
            const nameInput = document.getElementById('credentialName');
            if (nameInput) {
                nameInput.focus();
            }
        }, 300);
    }
}

/**
 * Update credential fields based on type
 */
function updateCredentialFields() {
    const typeSelect = document.getElementById('credentialType');
    const fieldsContainer = document.getElementById('credentialFields');
    
    if (!typeSelect || !fieldsContainer) return;
    
    const credentialType = typeSelect.value;
    fieldsContainer.innerHTML = getCredentialTypeFields(credentialType);
}

/**
 * Get credential type specific fields
 */
function getCredentialTypeFields(type) {
    const commonFields = `
        <div class="form-section">
            <h3>Credential Data</h3>
    `;
    
    const endFields = `
        </div>
    `;
    
    switch (type) {
        case 'password':
            return commonFields + `
                <div class="form-row">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <div class="password-input-group">
                            <input type="password" id="password" required>
                            <button type="button" class="password-toggle" onclick="togglePasswordVisibility('password')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="form-group">
                    <button type="button" class="btn btn-secondary" onclick="generatePassword()">
                        <i class="fas fa-key"></i> Generate Strong Password
                    </button>
                </div>
            ` + endFields;
            
        case 'api_key':
            return commonFields + `
                <div class="form-group">
                    <label for="apiKey">API Key</label>
                    <textarea id="apiKey" rows="3" required placeholder="Enter API key"></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="apiUrl">API URL (optional)</label>
                        <input type="url" id="apiUrl" placeholder="https://api.example.com">
                    </div>
                    <div class="form-group">
                        <label for="apiVersion">API Version (optional)</label>
                        <input type="text" id="apiVersion" placeholder="v1">
                    </div>
                </div>
            ` + endFields;
            
        case 'certificate':
            return commonFields + `
                <div class="form-group">
                    <label for="certificate">Certificate (PEM format)</label>
                    <textarea id="certificate" rows="8" required placeholder="-----BEGIN CERTIFICATE-----"></textarea>
                </div>
                <div class="form-group">
                    <label for="privateKey">Private Key (PEM format)</label>
                    <textarea id="privateKey" rows="8" placeholder="-----BEGIN PRIVATE KEY-----"></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="certPassword">Certificate Password (if encrypted)</label>
                        <div class="password-input-group">
                            <input type="password" id="certPassword">
                            <button type="button" class="password-toggle" onclick="togglePasswordVisibility('certPassword')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="certFormat">Format</label>
                        <select id="certFormat">
                            <option value="pem">PEM</option>
                            <option value="p12">PKCS#12</option>
                            <option value="jks">Java KeyStore</option>
                        </select>
                    </div>
                </div>
            ` + endFields;
            
        case 'ssh_key':
            return commonFields + `
                <div class="form-group">
                    <label for="sshPrivateKey">Private Key</label>
                    <textarea id="sshPrivateKey" rows="8" required placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"></textarea>
                </div>
                <div class="form-group">
                    <label for="sshPublicKey">Public Key</label>
                    <textarea id="sshPublicKey" rows="3" placeholder="ssh-rsa AAAAB3..."></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="sshPassphrase">Passphrase (if encrypted)</label>
                        <div class="password-input-group">
                            <input type="password" id="sshPassphrase">
                            <button type="button" class="password-toggle" onclick="togglePasswordVisibility('sshPassphrase')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="sshKeyType">Key Type</label>
                        <select id="sshKeyType">
                            <option value="rsa">RSA</option>
                            <option value="ed25519">Ed25519</option>
                            <option value="ecdsa">ECDSA</option>
                        </select>
                    </div>
                </div>
            ` + endFields;
            
        case 'database_connection':
            return commonFields + `
                <div class="form-row">
                    <div class="form-group">
                        <label for="dbHost">Host</label>
                        <input type="text" id="dbHost" required placeholder="localhost">
                    </div>
                    <div class="form-group">
                        <label for="dbPort">Port</label>
                        <input type="number" id="dbPort" placeholder="5432">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="dbName">Database Name</label>
                        <input type="text" id="dbName" required>
                    </div>
                    <div class="form-group">
                        <label for="dbType">Database Type</label>
                        <select id="dbType">
                            <option value="postgresql">PostgreSQL</option>
                            <option value="mysql">MySQL</option>
                            <option value="mongodb">MongoDB</option>
                            <option value="redis">Redis</option>
                            <option value="sqlite">SQLite</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="dbUsername">Username</label>
                        <input type="text" id="dbUsername" required>
                    </div>
                    <div class="form-group">
                        <label for="dbPassword">Password</label>
                        <div class="password-input-group">
                            <input type="password" id="dbPassword" required>
                            <button type="button" class="password-toggle" onclick="togglePasswordVisibility('dbPassword')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="form-group">
                    <label for="dbConnectionString">Connection String (optional)</label>
                    <textarea id="dbConnectionString" rows="2" placeholder="Full connection string if needed"></textarea>
                </div>
            ` + endFields;
            
        case 'oauth_credentials':
            return commonFields + `
                <div class="form-row">
                    <div class="form-group">
                        <label for="clientId">Client ID</label>
                        <input type="text" id="clientId" required>
                    </div>
                    <div class="form-group">
                        <label for="clientSecret">Client Secret</label>
                        <div class="password-input-group">
                            <input type="password" id="clientSecret" required>
                            <button type="button" class="password-toggle" onclick="togglePasswordVisibility('clientSecret')">
                                <i class="fas fa-eye"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="oauthScope">Scope</label>
                        <input type="text" id="oauthScope" placeholder="read write">
                    </div>
                    <div class="form-group">
                        <label for="redirectUri">Redirect URI</label>
                        <input type="url" id="redirectUri" placeholder="https://app.example.com/callback">
                    </div>
                </div>
                <div class="form-group">
                    <label for="authUrl">Authorization URL</label>
                    <input type="url" id="authUrl" placeholder="https://oauth.example.com/authorize">
                </div>
                <div class="form-group">
                    <label for="tokenUrl">Token URL</label>
                    <input type="url" id="tokenUrl" placeholder="https://oauth.example.com/token">
                </div>
            ` + endFields;
            
        case 'token':
            return commonFields + `
                <div class="form-group">
                    <label for="tokenValue">Token Value</label>
                    <textarea id="tokenValue" rows="4" required placeholder="Enter token value"></textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="tokenType">Token Type</label>
                        <select id="tokenType">
                            <option value="bearer">Bearer</option>
                            <option value="jwt">JWT</option>
                            <option value="api_token">API Token</option>
                            <option value="access_token">Access Token</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="tokenHeader">Header Name (optional)</label>
                        <input type="text" id="tokenHeader" placeholder="Authorization">
                    </div>
                </div>
            ` + endFields;
            
        default:
            return commonFields + `
                <div class="form-group">
                    <label for="credentialValue">Credential Value</label>
                    <textarea id="credentialValue" rows="4" required placeholder="Enter credential data"></textarea>
                </div>
            ` + endFields;
    }
}

/**
 * Save credential (create or update)
 */
async function saveCredential(event) {
    event.preventDefault();
    
    if (!vaultState.isUnlocked) {
        showNotification('Vault is locked', 'error');
        return;
    }
    
    try {
        const formData = collectCredentialFormData();
        if (!formData) return;
        
        const isEdit = vaultState.selectedCredential !== null;
        const url = isEdit 
            ? `/api/v1/vault/credentials/${vaultState.selectedCredential.id}`
            : '/api/v1/vault/credentials';
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            const result = await response.json();
            
            closeCredentialModal();
            await loadCredentials();
            
            const action = isEdit ? 'updated' : 'created';
            showNotification(`Credential ${action} successfully`, 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory(`credential_${action}`, {
                action: `credential_${action}`,
                credential_id: result.id,
                credential_type: formData.credential_type,
                environment: formData.environment,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || `Failed to ${isEdit ? 'update' : 'create'} credential`, 'error');
        }
    } catch (error) {
        console.error('Error saving credential:', error);
        showNotification('Failed to save credential', 'error');
    }
}

/**
 * Collect credential form data
 */
function collectCredentialFormData() {
    const name = document.getElementById('credentialName')?.value;
    const type = document.getElementById('credentialType')?.value;
    const environment = document.getElementById('credentialEnvironment')?.value;
    const service = document.getElementById('credentialService')?.value;
    
    if (!name || !type || !environment || !service) {
        showNotification('Please fill in all required fields', 'error');
        return null;
    }
    
    const formData = {
        name: name,
        credential_type: type,
        environment: environment,
        service: service,
        description: document.getElementById('credentialDescription')?.value || '',
        project: document.getElementById('credentialProject')?.value || '',
        tags: document.getElementById('credentialTags')?.value.split(',').map(tag => tag.trim()).filter(tag => tag),
        expires_at: document.getElementById('credentialExpires')?.value || null,
        rotation_interval_days: parseInt(document.getElementById('rotationInterval')?.value) || 90,
        auto_rotate: document.getElementById('autoRotate')?.checked || false,
        audit_required: document.getElementById('auditRequired')?.checked || false,
        credential_data: collectCredentialTypeData(type)
    };
    
    return formData;
}

/**
 * Collect credential type specific data
 */
function collectCredentialTypeData(type) {
    switch (type) {
        case 'password':
            return {
                username: document.getElementById('username')?.value,
                password: document.getElementById('password')?.value
            };
            
        case 'api_key':
            return {
                api_key: document.getElementById('apiKey')?.value,
                api_url: document.getElementById('apiUrl')?.value,
                api_version: document.getElementById('apiVersion')?.value
            };
            
        case 'certificate':
            return {
                certificate: document.getElementById('certificate')?.value,
                private_key: document.getElementById('privateKey')?.value,
                password: document.getElementById('certPassword')?.value,
                format: document.getElementById('certFormat')?.value
            };
            
        case 'ssh_key':
            return {
                private_key: document.getElementById('sshPrivateKey')?.value,
                public_key: document.getElementById('sshPublicKey')?.value,
                passphrase: document.getElementById('sshPassphrase')?.value,
                key_type: document.getElementById('sshKeyType')?.value
            };
            
        case 'database_connection':
            return {
                host: document.getElementById('dbHost')?.value,
                port: parseInt(document.getElementById('dbPort')?.value) || null,
                database: document.getElementById('dbName')?.value,
                username: document.getElementById('dbUsername')?.value,
                password: document.getElementById('dbPassword')?.value,
                database_type: document.getElementById('dbType')?.value,
                connection_string: document.getElementById('dbConnectionString')?.value
            };
            
        case 'oauth_credentials':
            return {
                client_id: document.getElementById('clientId')?.value,
                client_secret: document.getElementById('clientSecret')?.value,
                scope: document.getElementById('oauthScope')?.value,
                redirect_uri: document.getElementById('redirectUri')?.value,
                auth_url: document.getElementById('authUrl')?.value,
                token_url: document.getElementById('tokenUrl')?.value
            };
            
        case 'token':
            return {
                token: document.getElementById('tokenValue')?.value,
                token_type: document.getElementById('tokenType')?.value,
                header_name: document.getElementById('tokenHeader')?.value
            };
            
        default:
            return {
                value: document.getElementById('credentialValue')?.value
            };
    }
}

/**
 * Close credential modal
 */
function closeCredentialModal() {
    const modal = document.getElementById('credentialModal');
    if (modal) {
        modal.classList.remove('show');
        vaultState.selectedCredential = null;
    }
}

/**
 * View credential details
 */
async function viewCredential(credentialId) {
    if (!vaultState.isUnlocked) {
        showNotification('Vault is locked', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/vault/credentials/${credentialId}`, {
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            const credential = await response.json();
            showCredentialViewModal(credential);
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('credential_viewed', {
                action: 'credential_viewed',
                credential_id: credentialId,
                timestamp: new Date().toISOString()
            });
        } else {
            showNotification('Failed to load credential details', 'error');
        }
    } catch (error) {
        console.error('Error viewing credential:', error);
        showNotification('Failed to load credential details', 'error');
    }
}

/**
 * Show credential view modal
 */
function showCredentialViewModal(credential) {
    const modal = document.getElementById('credentialViewModal');
    const title = document.getElementById('viewCredentialTitle');
    const content = document.getElementById('credentialViewContent');
    
    if (!modal || !title || !content) return;
    
    title.textContent = credential.name;
    content.innerHTML = renderCredentialDetails(credential);
    
    vaultState.selectedCredential = credential;
    modal.classList.add('show');
}

/**
 * Render credential details
 */
function renderCredentialDetails(credential) {
    const status = getCredentialStatus(credential);
    const typeIcon = getCredentialTypeIcon(credential.credential_type);
    
    return `
        <div class="credential-details">
            <div class="detail-section">
                <h4><i class="fas fa-info-circle"></i> Basic Information</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Name:</label>
                        <span>${escapeHtml(credential.name)}</span>
                    </div>
                    <div class="detail-item">
                        <label>Type:</label>
                        <span><i class="${typeIcon}"></i> ${credential.credential_type.replace('_', ' ').toUpperCase()}</span>
                    </div>
                    <div class="detail-item">
                        <label>Environment:</label>
                        <span>${getEnvironmentBadge(credential.environment)}</span>
                    </div>
                    <div class="detail-item">
                        <label>Service:</label>
                        <span>${escapeHtml(credential.service)}</span>
                    </div>
                    <div class="detail-item">
                        <label>Status:</label>
                        <span class="credential-status ${status.toLowerCase().replace(' ', '-')}">
                            <i class="fas ${getStatusIcon(status)}"></i> ${status}
                        </span>
                    </div>
                    ${credential.project ? `
                    <div class="detail-item">
                        <label>Project:</label>
                        <span>${escapeHtml(credential.project)}</span>
                    </div>
                    ` : ''}
                </div>
                ${credential.description ? `
                <div class="detail-item full-width">
                    <label>Description:</label>
                    <p>${escapeHtml(credential.description)}</p>
                </div>
                ` : ''}
            </div>
            
            ${credential.tags && credential.tags.length > 0 ? `
            <div class="detail-section">
                <h4><i class="fas fa-tags"></i> Tags</h4>
                <div class="credential-tags">
                    ${credential.tags.map(tag => `<span class="credential-tag">${escapeHtml(tag)}</span>`).join('')}
                </div>
            </div>
            ` : ''}
            
            <div class="detail-section">
                <h4><i class="fas fa-shield-alt"></i> Security Information</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Created:</label>
                        <span>${formatDateTime(credential.created_at)}</span>
                    </div>
                    <div class="detail-item">
                        <label>Last Modified:</label>
                        <span>${formatDateTime(credential.updated_at)}</span>
                    </div>
                    ${credential.expires_at ? `
                    <div class="detail-item">
                        <label>Expires:</label>
                        <span>${formatDateTime(credential.expires_at)}</span>
                    </div>
                    ` : ''}
                    <div class="detail-item">
                        <label>Auto Rotate:</label>
                        <span>${credential.auto_rotate ? 'Enabled' : 'Disabled'}</span>
                    </div>
                    <div class="detail-item">
                        <label>Rotation Interval:</label>
                        <span>${credential.rotation_interval_days} days</span>
                    </div>
                    <div class="detail-item">
                        <label>Audit Required:</label>
                        <span>${credential.audit_required ? 'Yes' : 'No'}</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4><i class="fas fa-key"></i> Credential Data</h4>
                <div class="credential-data-container">
                    ${renderCredentialData(credential)}
                </div>
            </div>
            
            <div class="detail-actions">
                <button class="btn btn-primary" onclick="copyCredentialData('${credential.id}')">
                    <i class="fas fa-copy"></i> Copy to Clipboard
                </button>
                <button class="btn btn-secondary" onclick="editCredential('${credential.id}')">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn btn-warning" onclick="rotateCredential('${credential.id}')">
                    <i class="fas fa-sync"></i> Rotate
                </button>
            </div>
        </div>
    `;
}

/**
 * Render credential data based on type
 */
function renderCredentialData(credential) {
    const data = credential.credential_data;
    if (!data) return '<p>No credential data available</p>';
    
    switch (credential.credential_type) {
        case 'password':
            return `
                <div class="credential-field">
                    <label>Username:</label>
                    <div class="credential-value">
                        <span class="value-display">${escapeHtml(data.username || '')}</span>
                        <button class="copy-btn" onclick="copyToClipboard('${data.username || ''}', 'Username')">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
                <div class="credential-field">
                    <label>Password:</label>
                    <div class="credential-value">
                        <span class="value-display password-hidden" id="password-${credential.id}">••••••••••••</span>
                        <button class="reveal-btn" onclick="toggleCredentialVisibility('password-${credential.id}', '${data.password || ''}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="copy-btn" onclick="copyToClipboard('${data.password || ''}', 'Password')">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
            `;
            
        case 'api_key':
            return `
                <div class="credential-field">
                    <label>API Key:</label>
                    <div class="credential-value">
                        <span class="value-display password-hidden" id="apikey-${credential.id}">••••••••••••••••••••••••••••••••</span>
                        <button class="reveal-btn" onclick="toggleCredentialVisibility('apikey-${credential.id}', '${data.api_key || ''}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="copy-btn" onclick="copyToClipboard('${data.api_key || ''}', 'API Key')">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
                ${data.api_url ? `
                <div class="credential-field">
                    <label>API URL:</label>
                    <div class="credential-value">
                        <span class="value-display">${escapeHtml(data.api_url)}</span>
                        <button class="copy-btn" onclick="copyToClipboard('${data.api_url}', 'API URL')">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
                ` : ''}
                ${data.api_version ? `
                <div class="credential-field">
                    <label>API Version:</label>
                    <span class="value-display">${escapeHtml(data.api_version)}</span>
                </div>
                ` : ''}
            `;
            
        // Add more credential types as needed...
        default:
            return `
                <div class="credential-field">
                    <label>Value:</label>
                    <div class="credential-value">
                        <span class="value-display password-hidden" id="value-${credential.id}">••••••••••••••••••••••••••••••••</span>
                        <button class="reveal-btn" onclick="toggleCredentialVisibility('value-${credential.id}', '${JSON.stringify(data)}')">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="copy-btn" onclick="copyToClipboard('${JSON.stringify(data)}', 'Credential Data')">
                            <i class="fas fa-copy"></i>
                        </button>
                    </div>
                </div>
            `;
    }
}

/**
 * Toggle credential visibility
 */
function toggleCredentialVisibility(elementId, value) {
    const element = document.getElementById(elementId);
    const button = element?.nextElementSibling;
    
    if (!element || !button) return;
    
    if (element.classList.contains('password-hidden')) {
        element.textContent = value;
        element.classList.remove('password-hidden');
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (!element.classList.contains('password-hidden')) {
                element.textContent = '••••••••••••••••••••••••••••••••';
                element.classList.add('password-hidden');
                button.innerHTML = '<i class="fas fa-eye"></i>';
            }
        }, 10000);
    } else {
        element.textContent = '••••••••••••••••••••••••••••••••';
        element.classList.add('password-hidden');
        button.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

/**
 * Copy to clipboard with security measures
 */
async function copyToClipboard(text, label) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification(`${label} copied to clipboard`, 'success');
        
        // Clear clipboard after 30 seconds for security
        setTimeout(async () => {
            try {
                await navigator.clipboard.writeText('');
            } catch (e) {
                // Ignore errors when clearing clipboard
            }
        }, 30000);
        
        // Store hAIveMind memory
        await storeHAIveMindMemory('credential_copied', {
            action: 'credential_copied',
            label: label,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        console.error('Failed to copy to clipboard:', error);
        showNotification('Failed to copy to clipboard', 'error');
    }
}

/**
 * Close credential view modal
 */
function closeCredentialViewModal() {
    const modal = document.getElementById('credentialViewModal');
    if (modal) {
        modal.classList.remove('show');
        vaultState.selectedCredential = null;
    }
}

/**
 * Utility functions
 */

// Get credential status
function getCredentialStatus(credential) {
    if (!credential.expires_at) return 'Active';
    
    const now = new Date();
    const expiresAt = new Date(credential.expires_at);
    const daysUntilExpiry = Math.ceil((expiresAt - now) / (1000 * 60 * 60 * 24));
    
    if (daysUntilExpiry < 0) return 'Expired';
    if (daysUntilExpiry <= 7) return 'Expiring Soon';
    return 'Active';
}

// Get credential type icon
function getCredentialTypeIcon(type) {
    const icons = {
        password: 'fas fa-key',
        api_key: 'fas fa-code',
        certificate: 'fas fa-certificate',
        ssh_key: 'fas fa-terminal',
        token: 'fas fa-coins',
        database_connection: 'fas fa-database',
        oauth_credentials: 'fas fa-shield-alt'
    };
    return icons[type] || 'fas fa-lock';
}

// Get status icon
function getStatusIcon(status) {
    const icons = {
        'Active': 'fa-check-circle',
        'Expiring Soon': 'fa-exclamation-triangle',
        'Expired': 'fa-times-circle',
        'Disabled': 'fa-ban'
    };
    return icons[status] || 'fa-question-circle';
}

// Get environment badge
function getEnvironmentBadge(environment) {
    const badges = {
        production: '<span class="env-badge prod">PROD</span>',
        staging: '<span class="env-badge staging">STAGING</span>',
        development: '<span class="env-badge dev">DEV</span>',
        testing: '<span class="env-badge test">TEST</span>'
    };
    return badges[environment] || `<span class="env-badge">${environment.toUpperCase()}</span>`;
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
}

// Format date and time
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
}

// Escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Get auth headers
function getAuthHeaders() {
    const token = localStorage.getItem('haivemind_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Get notification icon
function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

// Toggle dark mode
function toggleDarkMode() {
    vaultState.darkMode = !vaultState.darkMode;
    localStorage.setItem('vault_dark_mode', vaultState.darkMode.toString());
    
    if (vaultState.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    
    updateDarkModeIcon();
}

// Update dark mode icon
function updateDarkModeIcon() {
    const darkModeBtn = document.querySelector('.dark-mode-toggle i');
    if (darkModeBtn) {
        darkModeBtn.className = vaultState.darkMode ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const button = input?.nextElementSibling;
    
    if (!input || !button) return;
    
    if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        button.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

// Store hAIveMind memory
async function storeHAIveMindMemory(category, data) {
    try {
        await fetch('/api/v1/memory/store', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                content: JSON.stringify(data),
                category: `vault_${category}`,
                context: 'vault_dashboard',
                tags: ['vault', 'dashboard', category]
            })
        });
    } catch (error) {
        console.error('Failed to store hAIveMind memory:', error);
    }
}

// Show loading state
function showLoadingState() {
    const credentialsGrid = document.getElementById('credentialsGrid');
    if (credentialsGrid) {
        credentialsGrid.innerHTML = `
            <div class="loading-placeholder">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Loading credentials...</p>
            </div>
        `;
    }
}

// Show error state
function showErrorState() {
    const credentialsGrid = document.getElementById('credentialsGrid');
    if (credentialsGrid) {
        credentialsGrid.innerHTML = `
            <div class="loading-placeholder">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Failed to load credentials</p>
                <button class="btn btn-primary" onclick="loadCredentials()">
                    <i class="fas fa-refresh"></i> Retry
                </button>
            </div>
        `;
    }
}

// Update vault status bar
function updateVaultStatusBar(status) {
    // Update total credentials
    const totalElement = document.getElementById('totalCredentials');
    if (totalElement) {
        totalElement.textContent = status.total_credentials || 0;
    }
    
    // Update expiring credentials
    const expiringElement = document.getElementById('expiringCredentials');
    if (expiringElement) {
        expiringElement.textContent = status.expiring_credentials || 0;
    }
}

// Update vault status indicator
function updateVaultStatusIndicator(isUnlocked) {
    const indicator = document.querySelector('.vault-status-indicator');
    if (indicator) {
        if (isUnlocked) {
            indicator.className = 'vault-status-indicator unlocked';
            indicator.innerHTML = '<i class="fas fa-unlock"></i><span>Vault Unlocked</span>';
        } else {
            indicator.className = 'vault-status-indicator locked';
            indicator.innerHTML = '<i class="fas fa-lock"></i><span>Vault Locked</span>';
        }
    }
}

// Update vault stats
function updateVaultStats() {
    const totalElement = document.getElementById('totalCredentials');
    const expiringElement = document.getElementById('expiringCredentials');
    
    if (totalElement) {
        totalElement.textContent = vaultState.currentCredentials.length;
    }
    
    if (expiringElement) {
        const expiring = vaultState.currentCredentials.filter(cred => 
            getCredentialStatus(cred) === 'Expiring Soon'
        ).length;
        expiringElement.textContent = expiring;
    }
}

// Update pagination
function updatePagination() {
    const totalItems = vaultState.filteredCredentials.length;
    const totalPages = Math.ceil(totalItems / vaultState.itemsPerPage);
    
    // Update pagination info
    const startIndex = (vaultState.currentPage - 1) * vaultState.itemsPerPage;
    const endIndex = Math.min(startIndex + vaultState.itemsPerPage, totalItems);
    
    const startElement = document.getElementById('paginationStart');
    const endElement = document.getElementById('paginationEnd');
    const totalElement = document.getElementById('paginationTotal');
    
    if (startElement) startElement.textContent = totalItems > 0 ? startIndex + 1 : 0;
    if (endElement) endElement.textContent = endIndex;
    if (totalElement) totalElement.textContent = totalItems;
    
    // Update pagination controls
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    
    if (prevBtn) {
        prevBtn.disabled = vaultState.currentPage <= 1;
    }
    
    if (nextBtn) {
        nextBtn.disabled = vaultState.currentPage >= totalPages;
    }
    
    // Update page numbers
    const pageNumbers = document.getElementById('pageNumbers');
    if (pageNumbers) {
        pageNumbers.innerHTML = generatePageNumbers(vaultState.currentPage, totalPages);
    }
}

// Generate page numbers
function generatePageNumbers(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    
    let pages = [];
    const maxVisible = 5;
    
    if (totalPages <= maxVisible) {
        for (let i = 1; i <= totalPages; i++) {
            pages.push(i);
        }
    } else {
        if (currentPage <= 3) {
            pages = [1, 2, 3, 4, '...', totalPages];
        } else if (currentPage >= totalPages - 2) {
            pages = [1, '...', totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
        } else {
            pages = [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
        }
    }
    
    return pages.map(page => {
        if (page === '...') {
            return '<span class="page-ellipsis">...</span>';
        } else {
            const isActive = page === currentPage ? 'active' : '';
            return `<button class="page-number ${isActive}" onclick="goToPage(${page})">${page}</button>`;
        }
    }).join('');
}

// Go to page
function goToPage(page) {
    vaultState.currentPage = page;
    renderCredentials();
    updatePagination();
}

// Previous page
function previousPage() {
    if (vaultState.currentPage > 1) {
        vaultState.currentPage--;
        renderCredentials();
        updatePagination();
    }
}

// Next page
function nextPage() {
    const totalPages = Math.ceil(vaultState.filteredCredentials.length / vaultState.itemsPerPage);
    if (vaultState.currentPage < totalPages) {
        vaultState.currentPage++;
        renderCredentials();
        updatePagination();
    }
}

// Handle keyboard shortcuts
function handleKeyboardShortcuts(event) {
    if (!vaultState.isUnlocked) return;
    
    // Ctrl/Cmd + K for search
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        const searchInput = document.getElementById('credentialSearch');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Ctrl/Cmd + N for new credential
    if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
        event.preventDefault();
        showCreateCredentialModal();
    }
    
    // Escape to close modals
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            modal.classList.remove('show');
        });
    }
}

// Handle clipboard security
function handleClipboardSecurity(event) {
    // Add watermark to copied sensitive data
    const selection = window.getSelection().toString();
    if (selection && selection.length > 10) {
        // This is a basic implementation - in production, you'd want more sophisticated detection
        console.log('Sensitive data copied to clipboard');
    }
}

// Detect screen recording (basic implementation)
function detectScreenRecording() {
    // This is a basic detection method - more sophisticated methods would be needed for production
    let isRecording = false;
    
    const checkRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
            stream.getTracks().forEach(track => track.stop());
            
            if (!isRecording) {
                isRecording = true;
                showNotification('Screen recording detected - vault access logged', 'warning');
                
                // Store security event
                await storeHAIveMindMemory('security_event', {
                    action: 'screen_recording_detected',
                    timestamp: new Date().toISOString(),
                    severity: 'medium'
                });
            }
        } catch (error) {
            isRecording = false;
        }
    };
    
    // Check periodically (this is just a demo - real implementation would be different)
    setInterval(checkRecording, 30000);
}

// Load vault stats
async function loadVaultStats() {
    try {
        const response = await fetch('/api/v1/vault/stats', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const stats = await response.json();
            updateVaultStatusBar(stats);
        }
    } catch (error) {
        console.error('Error loading vault stats:', error);
    }
}