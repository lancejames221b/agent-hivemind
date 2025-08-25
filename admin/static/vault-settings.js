/**
 * hAIveMind Vault Settings - JavaScript Functions
 * Author: Lance James, Unit 221B
 * Admin panel integration for vault configuration and management
 */

// Global state for vault settings
let vaultSettingsState = {
    currentSettings: {},
    isDirty: false,
    emergencyAdmins: [],
    passwordPolicy: {},
    darkMode: localStorage.getItem('vault_dark_mode') === 'true'
};

// Initialize vault settings
document.addEventListener('DOMContentLoaded', function() {
    initializeVaultSettings();
    loadVaultStatus();
    loadCurrentSettings();
    setupEventListeners();
});

/**
 * Initialize vault settings interface
 */
function initializeVaultSettings() {
    // Apply dark mode if enabled
    if (vaultSettingsState.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
        updateDarkModeIcon();
    }
    
    // Setup form validation
    setupFormValidation();
    
    // Load emergency administrators
    loadEmergencyAdministrators();
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // HSM toggle
    const hsmToggle = document.getElementById('enableHSM');
    if (hsmToggle) {
        hsmToggle.addEventListener('change', function() {
            const hsmConfig = document.getElementById('hsmConfig');
            if (hsmConfig) {
                hsmConfig.style.display = this.checked ? 'block' : 'none';
            }
        });
    }
    
    // Shamir sharing toggle
    const shamirToggle = document.getElementById('enableShamirSharing');
    if (shamirToggle) {
        shamirToggle.addEventListener('change', function() {
            const shamirConfig = document.getElementById('shamirConfig');
            if (shamirConfig) {
                shamirConfig.style.display = this.checked ? 'block' : 'none';
            }
        });
    }
    
    // Mark form as dirty when settings change
    const settingInputs = document.querySelectorAll('input, select, textarea');
    settingInputs.forEach(input => {
        input.addEventListener('change', () => {
            vaultSettingsState.isDirty = true;
        });
    });
    
    // Warn before leaving with unsaved changes
    window.addEventListener('beforeunload', function(e) {
        if (vaultSettingsState.isDirty) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        }
    });
}

/**
 * Load vault status
 */
async function loadVaultStatus() {
    try {
        const response = await fetch('/api/v1/vault/admin/status', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const status = await response.json();
            updateVaultStatusIndicators(status);
        }
    } catch (error) {
        console.error('Error loading vault status:', error);
        showNotification('Failed to load vault status', 'error');
    }
}

/**
 * Update vault status indicators
 */
function updateVaultStatusIndicators(status) {
    const indicators = {
        vaultInitialized: status.vault_initialized || false,
        masterPasswordSet: status.master_password_set || false,
        encryptionEnabled: status.encryption_enabled || false,
        auditingEnabled: status.auditing_enabled || false
    };
    
    Object.entries(indicators).forEach(([id, isActive]) => {
        const indicator = document.getElementById(id);
        if (indicator) {
            indicator.className = `indicator ${isActive ? 'active' : 'inactive'}`;
            const icon = indicator.querySelector('i');
            if (icon) {
                icon.className = isActive ? 'fas fa-check-circle' : 'fas fa-times-circle';
            }
        }
    });
}

/**
 * Load current settings
 */
async function loadCurrentSettings() {
    try {
        const response = await fetch('/api/v1/vault/admin/settings', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const settings = await response.json();
            vaultSettingsState.currentSettings = settings;
            populateSettingsForm(settings);
        }
    } catch (error) {
        console.error('Error loading current settings:', error);
        showNotification('Failed to load current settings', 'error');
    }
}

/**
 * Populate settings form with current values
 */
function populateSettingsForm(settings) {
    // Password policy
    if (settings.password_policy) {
        const policy = settings.password_policy;
        document.getElementById('minPasswordLength').value = policy.min_length || 12;
        document.getElementById('requireUppercase').checked = policy.require_uppercase !== false;
        document.getElementById('requireLowercase').checked = policy.require_lowercase !== false;
        document.getElementById('requireNumbers').checked = policy.require_numbers !== false;
        document.getElementById('requireSpecialChars').checked = policy.require_special_chars !== false;
        document.getElementById('passwordExpiration').value = policy.expiration_days || 90;
    }
    
    // Encryption settings
    if (settings.encryption) {
        const encryption = settings.encryption;
        const algorithmRadio = document.querySelector(`input[name="encryptionAlgorithm"][value="${encryption.algorithm}"]`);
        if (algorithmRadio) algorithmRadio.checked = true;
        
        document.getElementById('kdfAlgorithm').value = encryption.kdf_algorithm || 'argon2id';
        document.getElementById('kdfIterations').value = encryption.kdf_iterations || 100000;
        document.getElementById('kdfMemory').value = encryption.kdf_memory || 64;
        
        document.getElementById('enableHSM').checked = encryption.hsm_enabled || false;
        if (encryption.hsm_enabled) {
            document.getElementById('hsmConfig').style.display = 'block';
            document.getElementById('hsmProvider').value = encryption.hsm_provider || '';
            document.getElementById('hsmEndpoint').value = encryption.hsm_endpoint || '';
        }
    }
    
    // Security settings
    if (settings.security) {
        const security = settings.security;
        document.getElementById('sessionTimeout').value = security.session_timeout || 30;
        document.getElementById('maxConcurrentSessions').value = security.max_concurrent_sessions || 3;
        document.getElementById('requireReauth').checked = security.require_reauth !== false;
        document.getElementById('enableMFA').checked = security.mfa_enabled !== false;
        document.getElementById('enableIPWhitelist').checked = security.ip_whitelist_enabled || false;
        document.getElementById('maxFailedAttempts').value = security.max_failed_attempts || 5;
        document.getElementById('lockoutDuration').value = security.lockout_duration || 15;
        document.getElementById('enableDetailedLogging').checked = security.detailed_logging !== false;
        document.getElementById('enableRealTimeAlerts').checked = security.realtime_alerts !== false;
        document.getElementById('logRetentionDays').value = security.log_retention_days || 365;
    }
    
    // Backup settings
    if (settings.backup) {
        const backup = settings.backup;
        document.getElementById('enableAutoBackup').checked = backup.auto_backup !== false;
        document.getElementById('backupFrequency').value = backup.frequency || 'daily';
        document.getElementById('backupRetention').value = backup.retention_days || 30;
        
        const storageRadio = document.querySelector(`input[name="backupStorage"][value="${backup.storage_type}"]`);
        if (storageRadio) storageRadio.checked = true;
    }
    
    // Emergency settings
    if (settings.emergency) {
        const emergency = settings.emergency;
        document.getElementById('enableBreakGlass').checked = emergency.break_glass_enabled !== false;
        document.getElementById('breakGlassApprovals').value = emergency.break_glass_approvals || 2;
        document.getElementById('breakGlassTimeout').value = emergency.break_glass_timeout || 4;
        document.getElementById('enableShamirSharing').checked = emergency.shamir_sharing_enabled || false;
        
        if (emergency.shamir_sharing_enabled) {
            document.getElementById('shamirConfig').style.display = 'block';
            document.getElementById('shamirShares').value = emergency.shamir_shares || 5;
            document.getElementById('shamirThreshold').value = emergency.shamir_threshold || 3;
        }
    }
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    // Password strength checking
    const newPasswordInput = document.getElementById('newMasterPassword');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', checkPasswordStrength);
    }
    
    // Password confirmation matching
    const confirmPasswordInput = document.getElementById('confirmMasterPassword');
    if (confirmPasswordInput) {
        confirmPasswordInput.addEventListener('input', checkPasswordMatch);
    }
}

/**
 * Check password strength
 */
function checkPasswordStrength() {
    const password = document.getElementById('newMasterPassword').value;
    const strengthBar = document.getElementById('strengthFill');
    const strengthText = document.getElementById('strengthText');
    const changeBtn = document.getElementById('changeMasterPasswordBtn');
    
    if (!password) {
        strengthBar.style.width = '0%';
        strengthBar.className = 'strength-fill';
        strengthText.textContent = 'Enter password to check strength';
        changeBtn.disabled = true;
        return;
    }
    
    let score = 0;
    let feedback = [];
    
    // Length check
    if (password.length >= 12) score += 20;
    else feedback.push('Use at least 12 characters');
    
    // Character variety checks
    if (/[a-z]/.test(password)) score += 15;
    else feedback.push('Include lowercase letters');
    
    if (/[A-Z]/.test(password)) score += 15;
    else feedback.push('Include uppercase letters');
    
    if (/[0-9]/.test(password)) score += 15;
    else feedback.push('Include numbers');
    
    if (/[^A-Za-z0-9]/.test(password)) score += 15;
    else feedback.push('Include special characters');
    
    // Complexity bonuses
    if (password.length >= 16) score += 10;
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\?]/.test(password)) score += 5;
    if (!/(.)\1{2,}/.test(password)) score += 5; // No repeated characters
    
    // Update UI
    let level, color, text;
    if (score < 40) {
        level = 'weak';
        color = '#dc2626';
        text = 'Weak';
    } else if (score < 70) {
        level = 'medium';
        color = '#d97706';
        text = 'Medium';
    } else if (score < 90) {
        level = 'strong';
        color = '#059669';
        text = 'Strong';
    } else {
        level = 'very-strong';
        color = '#10b981';
        text = 'Very Strong';
    }
    
    strengthBar.style.width = `${Math.min(score, 100)}%`;
    strengthBar.style.backgroundColor = color;
    strengthText.textContent = `${text}${feedback.length > 0 ? ' - ' + feedback.join(', ') : ''}`;
    
    // Enable/disable change button
    changeBtn.disabled = score < 70 || !checkPasswordMatch();
}

/**
 * Check password match
 */
function checkPasswordMatch() {
    const newPassword = document.getElementById('newMasterPassword').value;
    const confirmPassword = document.getElementById('confirmMasterPassword').value;
    const matchIndicator = document.getElementById('passwordMatch');
    const changeBtn = document.getElementById('changeMasterPasswordBtn');
    
    if (!confirmPassword) {
        matchIndicator.textContent = '';
        return false;
    }
    
    const matches = newPassword === confirmPassword;
    matchIndicator.textContent = matches ? '✓ Passwords match' : '✗ Passwords do not match';
    matchIndicator.style.color = matches ? 'var(--vault-success)' : 'var(--vault-danger)';
    
    // Update button state
    const passwordStrong = document.getElementById('strengthFill').style.width === '100%' || 
                          parseInt(document.getElementById('strengthFill').style.width) >= 70;
    changeBtn.disabled = !matches || !passwordStrong;
    
    return matches;
}

/**
 * Generate strong password
 */
function generateStrongPassword() {
    const length = 20;
    const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
    let password = '';
    
    // Ensure at least one character from each required set
    const lowercase = 'abcdefghijklmnopqrstuvwxyz';
    const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const numbers = '0123456789';
    const special = '!@#$%^&*()_+-=[]{}|;:,.<>?';
    
    password += lowercase[Math.floor(Math.random() * lowercase.length)];
    password += uppercase[Math.floor(Math.random() * uppercase.length)];
    password += numbers[Math.floor(Math.random() * numbers.length)];
    password += special[Math.floor(Math.random() * special.length)];
    
    // Fill the rest randomly
    for (let i = 4; i < length; i++) {
        password += charset[Math.floor(Math.random() * charset.length)];
    }
    
    // Shuffle the password
    password = password.split('').sort(() => Math.random() - 0.5).join('');
    
    // Set the password and show it temporarily
    const newPasswordInput = document.getElementById('newMasterPassword');
    const confirmPasswordInput = document.getElementById('confirmMasterPassword');
    
    if (newPasswordInput && confirmPasswordInput) {
        newPasswordInput.value = password;
        confirmPasswordInput.value = password;
        
        // Show password temporarily
        newPasswordInput.type = 'text';
        confirmPasswordInput.type = 'text';
        
        // Check strength
        checkPasswordStrength();
        checkPasswordMatch();
        
        // Hide password after 10 seconds
        setTimeout(() => {
            newPasswordInput.type = 'password';
            confirmPasswordInput.type = 'password';
        }, 10000);
        
        showNotification('Strong password generated and filled in both fields', 'success');
    }
}

/**
 * Change master password
 */
async function changeMasterPassword(event) {
    event.preventDefault();
    
    const currentPassword = document.getElementById('currentMasterPassword').value;
    const newPassword = document.getElementById('newMasterPassword').value;
    const confirmPassword = document.getElementById('confirmMasterPassword').value;
    
    if (newPassword !== confirmPassword) {
        showNotification('New passwords do not match', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/v1/vault/admin/change-master-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        if (response.ok) {
            // Clear form
            document.getElementById('changeMasterPasswordForm').reset();
            document.getElementById('passwordStrength').style.display = 'none';
            document.getElementById('passwordMatch').textContent = '';
            
            showNotification('Master password changed successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('master_password_changed', {
                action: 'master_password_changed',
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to change master password', 'error');
        }
    } catch (error) {
        console.error('Error changing master password:', error);
        showNotification('Failed to change master password', 'error');
    }
}

/**
 * Save password policy
 */
async function savePasswordPolicy() {
    const policy = {
        min_length: parseInt(document.getElementById('minPasswordLength').value),
        require_uppercase: document.getElementById('requireUppercase').checked,
        require_lowercase: document.getElementById('requireLowercase').checked,
        require_numbers: document.getElementById('requireNumbers').checked,
        require_special_chars: document.getElementById('requireSpecialChars').checked,
        expiration_days: parseInt(document.getElementById('passwordExpiration').value)
    };
    
    try {
        const response = await fetch('/api/v1/vault/admin/password-policy', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(policy)
        });
        
        if (response.ok) {
            vaultSettingsState.passwordPolicy = policy;
            vaultSettingsState.isDirty = false;
            showNotification('Password policy saved successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('password_policy_updated', {
                action: 'password_policy_updated',
                policy: policy,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to save password policy', 'error');
        }
    } catch (error) {
        console.error('Error saving password policy:', error);
        showNotification('Failed to save password policy', 'error');
    }
}

/**
 * Save encryption settings
 */
async function saveEncryptionSettings() {
    const settings = {
        algorithm: document.querySelector('input[name="encryptionAlgorithm"]:checked').value,
        kdf_algorithm: document.getElementById('kdfAlgorithm').value,
        kdf_iterations: parseInt(document.getElementById('kdfIterations').value),
        kdf_memory: parseInt(document.getElementById('kdfMemory').value),
        hsm_enabled: document.getElementById('enableHSM').checked,
        hsm_provider: document.getElementById('hsmProvider').value,
        hsm_endpoint: document.getElementById('hsmEndpoint').value
    };
    
    try {
        const response = await fetch('/api/v1/vault/admin/encryption-settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            vaultSettingsState.isDirty = false;
            showNotification('Encryption settings saved successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('encryption_settings_updated', {
                action: 'encryption_settings_updated',
                settings: settings,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to save encryption settings', 'error');
        }
    } catch (error) {
        console.error('Error saving encryption settings:', error);
        showNotification('Failed to save encryption settings', 'error');
    }
}

/**
 * Save security settings
 */
async function saveSecuritySettings() {
    const settings = {
        session_timeout: parseInt(document.getElementById('sessionTimeout').value),
        max_concurrent_sessions: parseInt(document.getElementById('maxConcurrentSessions').value),
        require_reauth: document.getElementById('requireReauth').checked,
        mfa_enabled: document.getElementById('enableMFA').checked,
        ip_whitelist_enabled: document.getElementById('enableIPWhitelist').checked,
        max_failed_attempts: parseInt(document.getElementById('maxFailedAttempts').value),
        lockout_duration: parseInt(document.getElementById('lockoutDuration').value),
        detailed_logging: document.getElementById('enableDetailedLogging').checked,
        realtime_alerts: document.getElementById('enableRealTimeAlerts').checked,
        log_retention_days: parseInt(document.getElementById('logRetentionDays').value)
    };
    
    try {
        const response = await fetch('/api/v1/vault/admin/security-settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            vaultSettingsState.isDirty = false;
            showNotification('Security settings saved successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('security_settings_updated', {
                action: 'security_settings_updated',
                settings: settings,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to save security settings', 'error');
        }
    } catch (error) {
        console.error('Error saving security settings:', error);
        showNotification('Failed to save security settings', 'error');
    }
}

/**
 * Save backup settings
 */
async function saveBackupSettings() {
    const settings = {
        auto_backup: document.getElementById('enableAutoBackup').checked,
        frequency: document.getElementById('backupFrequency').value,
        retention_days: parseInt(document.getElementById('backupRetention').value),
        storage_type: document.querySelector('input[name="backupStorage"]:checked').value
    };
    
    try {
        const response = await fetch('/api/v1/vault/admin/backup-settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            vaultSettingsState.isDirty = false;
            showNotification('Backup settings saved successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('backup_settings_updated', {
                action: 'backup_settings_updated',
                settings: settings,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to save backup settings', 'error');
        }
    } catch (error) {
        console.error('Error saving backup settings:', error);
        showNotification('Failed to save backup settings', 'error');
    }
}

/**
 * Save emergency settings
 */
async function saveEmergencySettings() {
    const settings = {
        break_glass_enabled: document.getElementById('enableBreakGlass').checked,
        break_glass_approvals: parseInt(document.getElementById('breakGlassApprovals').value),
        break_glass_timeout: parseInt(document.getElementById('breakGlassTimeout').value),
        shamir_sharing_enabled: document.getElementById('enableShamirSharing').checked,
        shamir_shares: parseInt(document.getElementById('shamirShares').value),
        shamir_threshold: parseInt(document.getElementById('shamirThreshold').value)
    };
    
    try {
        const response = await fetch('/api/v1/vault/admin/emergency-settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            vaultSettingsState.isDirty = false;
            showNotification('Emergency settings saved successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('emergency_settings_updated', {
                action: 'emergency_settings_updated',
                settings: settings,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to save emergency settings', 'error');
        }
    } catch (error) {
        console.error('Error saving emergency settings:', error);
        showNotification('Failed to save emergency settings', 'error');
    }
}

/**
 * Load emergency administrators
 */
async function loadEmergencyAdministrators() {
    try {
        const response = await fetch('/api/v1/vault/admin/emergency-admins', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const admins = await response.json();
            vaultSettingsState.emergencyAdmins = admins;
            renderEmergencyAdminList(admins);
        }
    } catch (error) {
        console.error('Error loading emergency administrators:', error);
        showNotification('Failed to load emergency administrators', 'error');
    }
}

/**
 * Render emergency admin list
 */
function renderEmergencyAdminList(admins) {
    const container = document.getElementById('emergencyAdminList');
    if (!container) return;
    
    if (admins.length === 0) {
        container.innerHTML = '<p class="text-muted">No emergency administrators configured</p>';
        return;
    }
    
    container.innerHTML = admins.map(admin => `
        <div class="admin-item">
            <div class="admin-info">
                <div class="admin-name">${escapeHtml(admin.name)}</div>
                <div class="admin-email">${escapeHtml(admin.email)}</div>
                <div class="admin-role">${escapeHtml(admin.role)}</div>
            </div>
            <div class="admin-actions">
                <button class="btn btn-sm btn-secondary" onclick="editEmergencyAdmin('${admin.id}')">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn btn-sm btn-danger" onclick="removeEmergencyAdmin('${admin.id}')">
                    <i class="fas fa-trash"></i> Remove
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Add emergency administrator
 */
function addEmergencyAdmin() {
    const modal = document.getElementById('emergencyAdminModal');
    if (modal) {
        // Clear form
        document.getElementById('emergencyAdminForm').reset();
        modal.classList.add('show');
    }
}

/**
 * Close emergency admin modal
 */
function closeEmergencyAdminModal() {
    const modal = document.getElementById('emergencyAdminModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * Save emergency administrator
 */
async function saveEmergencyAdmin(event) {
    event.preventDefault();
    
    const adminData = {
        email: document.getElementById('adminEmail').value,
        name: document.getElementById('adminName').value,
        role: document.getElementById('adminRole').value,
        phone: document.getElementById('adminPhone').value
    };
    
    try {
        const response = await fetch('/api/v1/vault/admin/emergency-admins', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(adminData)
        });
        
        if (response.ok) {
            closeEmergencyAdminModal();
            await loadEmergencyAdministrators();
            showNotification('Emergency administrator added successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('emergency_admin_added', {
                action: 'emergency_admin_added',
                admin_email: adminData.email,
                admin_role: adminData.role,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to add emergency administrator', 'error');
        }
    } catch (error) {
        console.error('Error adding emergency administrator:', error);
        showNotification('Failed to add emergency administrator', 'error');
    }
}

/**
 * Remove emergency administrator
 */
async function removeEmergencyAdmin(adminId) {
    if (!confirm('Are you sure you want to remove this emergency administrator?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/vault/admin/emergency-admins/${adminId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            await loadEmergencyAdministrators();
            showNotification('Emergency administrator removed successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('emergency_admin_removed', {
                action: 'emergency_admin_removed',
                admin_id: adminId,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to remove emergency administrator', 'error');
        }
    } catch (error) {
        console.error('Error removing emergency administrator:', error);
        showNotification('Failed to remove emergency administrator', 'error');
    }
}

/**
 * Create manual backup
 */
async function createManualBackup() {
    try {
        showNotification('Creating backup...', 'info');
        
        const response = await fetch('/api/v1/vault/admin/backup/create', {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`Backup created successfully: ${result.backup_id}`, 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('manual_backup_created', {
                action: 'manual_backup_created',
                backup_id: result.backup_id,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to create backup', 'error');
        }
    } catch (error) {
        console.error('Error creating backup:', error);
        showNotification('Failed to create backup', 'error');
    }
}

/**
 * Test backup restore
 */
async function testBackupRestore() {
    if (!confirm('This will test the backup restore process. Continue?')) {
        return;
    }
    
    try {
        showNotification('Testing backup restore...', 'info');
        
        const response = await fetch('/api/v1/vault/admin/backup/test-restore', {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`Backup restore test completed: ${result.status}`, 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('backup_restore_tested', {
                action: 'backup_restore_tested',
                test_result: result,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Backup restore test failed', 'error');
        }
    } catch (error) {
        console.error('Error testing backup restore:', error);
        showNotification('Backup restore test failed', 'error');
    }
}

/**
 * Show recovery wizard
 */
function showRecoveryWizard() {
    showNotification('Recovery Wizard - Coming Soon', 'info');
}

/**
 * Generate recovery shares
 */
async function generateRecoveryShares() {
    if (!confirm('This will generate new recovery shares and invalidate existing ones. Continue?')) {
        return;
    }
    
    try {
        const shares = parseInt(document.getElementById('shamirShares').value);
        const threshold = parseInt(document.getElementById('shamirThreshold').value);
        
        const response = await fetch('/api/v1/vault/admin/recovery-shares/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({
                total_shares: shares,
                threshold: threshold
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showRecoverySharesModal(result.shares);
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('recovery_shares_generated', {
                action: 'recovery_shares_generated',
                total_shares: shares,
                threshold: threshold,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to generate recovery shares', 'error');
        }
    } catch (error) {
        console.error('Error generating recovery shares:', error);
        showNotification('Failed to generate recovery shares', 'error');
    }
}

/**
 * Show recovery shares modal
 */
function showRecoverySharesModal(shares) {
    const modal = document.createElement('div');
    modal.className = 'modal recovery-shares-modal';
    modal.innerHTML = `
        <div class="modal-content large-modal">
            <div class="modal-header">
                <h2><i class="fas fa-key"></i> Recovery Shares Generated</h2>
                <button class="modal-close" onclick="this.closest('.modal').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="recovery-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p><strong>IMPORTANT:</strong> Store these shares securely and separately. You will need ${document.getElementById('shamirThreshold').value} shares to recover the master password.</p>
                </div>
                <div class="shares-container">
                    ${shares.map((share, index) => `
                        <div class="share-item">
                            <h4>Share ${index + 1}</h4>
                            <div class="share-content">
                                <textarea readonly rows="3">${share}</textarea>
                                <button class="btn btn-sm btn-secondary" onclick="copyToClipboard('${share}', 'Recovery Share ${index + 1}')">
                                    <i class="fas fa-copy"></i> Copy
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div class="recovery-instructions">
                    <h4>Distribution Instructions:</h4>
                    <ol>
                        <li>Print or securely store each share separately</li>
                        <li>Distribute shares to trusted administrators</li>
                        <li>Do not store multiple shares in the same location</li>
                        <li>Keep a record of who has which share</li>
                        <li>Test the recovery process periodically</li>
                    </ol>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-primary" onclick="this.closest('.modal').remove()">
                    <i class="fas fa-check"></i> I have securely stored all shares
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.classList.add('show');
}

// Utility functions
function getAuthHeaders() {
    const token = localStorage.getItem('haivemind_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

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

function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleDarkMode() {
    vaultSettingsState.darkMode = !vaultSettingsState.darkMode;
    localStorage.setItem('vault_dark_mode', vaultSettingsState.darkMode.toString());
    
    if (vaultSettingsState.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    
    updateDarkModeIcon();
}

function updateDarkModeIcon() {
    const darkModeBtn = document.querySelector('.dark-mode-toggle i');
    if (darkModeBtn) {
        darkModeBtn.className = vaultSettingsState.darkMode ? 'fas fa-sun' : 'fas fa-moon';
    }
}

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
                category: `vault_settings_${category}`,
                context: 'vault_settings',
                tags: ['vault', 'settings', category]
            })
        });
    } catch (error) {
        console.error('Failed to store hAIveMind memory:', error);
    }
}