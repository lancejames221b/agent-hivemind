/**
 * hAIveMind Credential Vault Dashboard - Advanced Actions
 * Author: Lance James, Unit 221B
 * DELETE operations, bulk actions, and advanced vault management features
 */

/**
 * Delete credential with safety checks
 */
async function deleteCredential(credentialId) {
    if (!vaultState.isUnlocked) {
        showNotification('Vault is locked', 'error');
        return;
    }
    
    // Find the credential
    const credential = vaultState.currentCredentials.find(c => c.id === credentialId);
    if (!credential) {
        showNotification('Credential not found', 'error');
        return;
    }
    
    // Show confirmation dialog
    const confirmed = await showDeleteConfirmationDialog(credential);
    if (!confirmed) return;
    
    try {
        const response = await fetch(`/api/v1/vault/credentials/${credentialId}`, {
            method: 'DELETE',
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            await loadCredentials();
            showNotification('Credential deleted successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('credential_deleted', {
                action: 'credential_deleted',
                credential_id: credentialId,
                credential_name: credential.name,
                credential_type: credential.credential_type,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to delete credential', 'error');
        }
    } catch (error) {
        console.error('Error deleting credential:', error);
        showNotification('Failed to delete credential', 'error');
    }
}

/**
 * Show delete confirmation dialog
 */
function showDeleteConfirmationDialog(credential) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal delete-confirmation-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2><i class="fas fa-exclamation-triangle"></i> Confirm Deletion</h2>
                </div>
                <div class="modal-body">
                    <div class="delete-warning">
                        <p><strong>You are about to permanently delete this credential:</strong></p>
                        <div class="credential-summary">
                            <div class="summary-item">
                                <label>Name:</label>
                                <span>${escapeHtml(credential.name)}</span>
                            </div>
                            <div class="summary-item">
                                <label>Type:</label>
                                <span>${credential.credential_type.replace('_', ' ').toUpperCase()}</span>
                            </div>
                            <div class="summary-item">
                                <label>Environment:</label>
                                <span>${credential.environment.toUpperCase()}</span>
                            </div>
                            <div class="summary-item">
                                <label>Service:</label>
                                <span>${escapeHtml(credential.service)}</span>
                            </div>
                        </div>
                        <div class="delete-impact">
                            <h4><i class="fas fa-exclamation-circle"></i> Impact Analysis</h4>
                            <ul id="deleteImpactList">
                                <li>This action cannot be undone</li>
                                <li>All credential data will be permanently removed</li>
                                <li>Access history will be preserved for audit purposes</li>
                            </ul>
                        </div>
                        <div class="delete-options">
                            <label class="checkbox-label">
                                <input type="checkbox" id="confirmDeletion">
                                I understand this action is permanent and cannot be undone
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" id="notifyUsers">
                                Notify users with access to this credential
                            </label>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeDeleteModal()">Cancel</button>
                    <button type="button" class="btn btn-danger" onclick="confirmDeletion()" id="confirmDeleteBtn" disabled>
                        <i class="fas fa-trash"></i> Delete Credential
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.classList.add('show');
        
        // Enable/disable confirm button based on checkbox
        const confirmCheckbox = modal.querySelector('#confirmDeletion');
        const confirmBtn = modal.querySelector('#confirmDeleteBtn');
        
        confirmCheckbox.addEventListener('change', () => {
            confirmBtn.disabled = !confirmCheckbox.checked;
        });
        
        // Handle modal actions
        window.closeDeleteModal = () => {
            modal.remove();
            resolve(false);
        };
        
        window.confirmDeletion = () => {
            const notifyUsers = modal.querySelector('#notifyUsers').checked;
            modal.remove();
            resolve({ confirmed: true, notifyUsers });
        };
        
        // Load impact analysis
        loadDeleteImpactAnalysis(credential.id);
    });
}

/**
 * Load delete impact analysis
 */
async function loadDeleteImpactAnalysis(credentialId) {
    try {
        const response = await fetch(`/api/v1/vault/credentials/${credentialId}/impact`, {
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            const impact = await response.json();
            updateDeleteImpactList(impact);
        }
    } catch (error) {
        console.error('Error loading impact analysis:', error);
    }
}

/**
 * Update delete impact list
 */
function updateDeleteImpactList(impact) {
    const impactList = document.getElementById('deleteImpactList');
    if (!impactList) return;
    
    const additionalImpacts = [];
    
    if (impact.shared_with_users > 0) {
        additionalImpacts.push(`${impact.shared_with_users} users will lose access`);
    }
    
    if (impact.dependent_services > 0) {
        additionalImpacts.push(`${impact.dependent_services} services may be affected`);
    }
    
    if (impact.automation_scripts > 0) {
        additionalImpacts.push(`${impact.automation_scripts} automation scripts may fail`);
    }
    
    if (impact.last_accessed_days < 7) {
        additionalImpacts.push(`Recently accessed (${impact.last_accessed_days} days ago)`);
    }
    
    additionalImpacts.forEach(impactText => {
        const li = document.createElement('li');
        li.textContent = impactText;
        li.style.color = 'var(--vault-warning)';
        impactList.appendChild(li);
    });
}

/**
 * Edit credential
 */
async function editCredential(credentialId) {
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
            showEditCredentialModal(credential);
        } else {
            showNotification('Failed to load credential for editing', 'error');
        }
    } catch (error) {
        console.error('Error loading credential for editing:', error);
        showNotification('Failed to load credential for editing', 'error');
    }
}

/**
 * Show edit credential modal
 */
function showEditCredentialModal(credential) {
    const modal = document.getElementById('credentialModal');
    const title = document.getElementById('credentialModalTitle');
    const form = document.getElementById('credentialForm');
    
    if (!modal || !title || !form) return;
    
    title.textContent = 'Edit Credential';
    vaultState.selectedCredential = credential;
    
    // Populate form fields
    populateCredentialForm(credential);
    
    modal.classList.add('show');
    
    // Close view modal if open
    const viewModal = document.getElementById('credentialViewModal');
    if (viewModal) {
        viewModal.classList.remove('show');
    }
}

/**
 * Populate credential form with existing data
 */
function populateCredentialForm(credential) {
    // Basic fields
    document.getElementById('credentialName').value = credential.name || '';
    document.getElementById('credentialType').value = credential.credential_type || '';
    document.getElementById('credentialEnvironment').value = credential.environment || '';
    document.getElementById('credentialService').value = credential.service || '';
    document.getElementById('credentialDescription').value = credential.description || '';
    document.getElementById('credentialProject').value = credential.project || '';
    document.getElementById('credentialTags').value = credential.tags ? credential.tags.join(', ') : '';
    
    // Dates and settings
    if (credential.expires_at) {
        const expiresAt = new Date(credential.expires_at);
        document.getElementById('credentialExpires').value = expiresAt.toISOString().slice(0, 16);
    }
    
    document.getElementById('rotationInterval').value = credential.rotation_interval_days || 90;
    document.getElementById('autoRotate').checked = credential.auto_rotate || false;
    document.getElementById('auditRequired').checked = credential.audit_required || false;
    
    // Update credential type fields
    updateCredentialFields();
    
    // Populate credential-specific data
    setTimeout(() => {
        populateCredentialTypeData(credential.credential_type, credential.credential_data);
    }, 100);
}

/**
 * Populate credential type specific data
 */
function populateCredentialTypeData(type, data) {
    if (!data) return;
    
    switch (type) {
        case 'password':
            if (document.getElementById('username')) document.getElementById('username').value = data.username || '';
            if (document.getElementById('password')) document.getElementById('password').value = data.password || '';
            break;
            
        case 'api_key':
            if (document.getElementById('apiKey')) document.getElementById('apiKey').value = data.api_key || '';
            if (document.getElementById('apiUrl')) document.getElementById('apiUrl').value = data.api_url || '';
            if (document.getElementById('apiVersion')) document.getElementById('apiVersion').value = data.api_version || '';
            break;
            
        case 'certificate':
            if (document.getElementById('certificate')) document.getElementById('certificate').value = data.certificate || '';
            if (document.getElementById('privateKey')) document.getElementById('privateKey').value = data.private_key || '';
            if (document.getElementById('certPassword')) document.getElementById('certPassword').value = data.password || '';
            if (document.getElementById('certFormat')) document.getElementById('certFormat').value = data.format || 'pem';
            break;
            
        case 'ssh_key':
            if (document.getElementById('sshPrivateKey')) document.getElementById('sshPrivateKey').value = data.private_key || '';
            if (document.getElementById('sshPublicKey')) document.getElementById('sshPublicKey').value = data.public_key || '';
            if (document.getElementById('sshPassphrase')) document.getElementById('sshPassphrase').value = data.passphrase || '';
            if (document.getElementById('sshKeyType')) document.getElementById('sshKeyType').value = data.key_type || 'rsa';
            break;
            
        case 'database_connection':
            if (document.getElementById('dbHost')) document.getElementById('dbHost').value = data.host || '';
            if (document.getElementById('dbPort')) document.getElementById('dbPort').value = data.port || '';
            if (document.getElementById('dbName')) document.getElementById('dbName').value = data.database || '';
            if (document.getElementById('dbUsername')) document.getElementById('dbUsername').value = data.username || '';
            if (document.getElementById('dbPassword')) document.getElementById('dbPassword').value = data.password || '';
            if (document.getElementById('dbType')) document.getElementById('dbType').value = data.database_type || 'postgresql';
            if (document.getElementById('dbConnectionString')) document.getElementById('dbConnectionString').value = data.connection_string || '';
            break;
            
        case 'oauth_credentials':
            if (document.getElementById('clientId')) document.getElementById('clientId').value = data.client_id || '';
            if (document.getElementById('clientSecret')) document.getElementById('clientSecret').value = data.client_secret || '';
            if (document.getElementById('oauthScope')) document.getElementById('oauthScope').value = data.scope || '';
            if (document.getElementById('redirectUri')) document.getElementById('redirectUri').value = data.redirect_uri || '';
            if (document.getElementById('authUrl')) document.getElementById('authUrl').value = data.auth_url || '';
            if (document.getElementById('tokenUrl')) document.getElementById('tokenUrl').value = data.token_url || '';
            break;
            
        case 'token':
            if (document.getElementById('tokenValue')) document.getElementById('tokenValue').value = data.token || '';
            if (document.getElementById('tokenType')) document.getElementById('tokenType').value = data.token_type || 'bearer';
            if (document.getElementById('tokenHeader')) document.getElementById('tokenHeader').value = data.header_name || '';
            break;
            
        default:
            if (document.getElementById('credentialValue')) {
                document.getElementById('credentialValue').value = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
            }
            break;
    }
}

/**
 * Copy credential data
 */
async function copyCredential(credentialId) {
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
            showCopyCredentialModal(credential);
        } else {
            showNotification('Failed to load credential data', 'error');
        }
    } catch (error) {
        console.error('Error loading credential data:', error);
        showNotification('Failed to load credential data', 'error');
    }
}

/**
 * Show copy credential modal
 */
function showCopyCredentialModal(credential) {
    const modal = document.createElement('div');
    modal.className = 'modal copy-credential-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2><i class="fas fa-copy"></i> Copy Credential Data</h2>
                <button class="modal-close" onclick="this.closest('.modal').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <div class="copy-options">
                    <h4>Select data to copy:</h4>
                    <div class="copy-option-grid">
                        ${generateCopyOptions(credential)}
                    </div>
                </div>
                <div class="security-notice">
                    <i class="fas fa-shield-alt"></i>
                    <p>Copied data will be automatically cleared from clipboard after 30 seconds for security.</p>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.classList.add('show');
}

/**
 * Generate copy options based on credential type
 */
function generateCopyOptions(credential) {
    const data = credential.credential_data;
    if (!data) return '<p>No data available to copy</p>';
    
    let options = [];
    
    switch (credential.credential_type) {
        case 'password':
            if (data.username) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.username}', 'Username')">
                        <i class="fas fa-user"></i>
                        <span>Username</span>
                        <small>${data.username}</small>
                    </button>
                `);
            }
            if (data.password) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.password}', 'Password')">
                        <i class="fas fa-key"></i>
                        <span>Password</span>
                        <small>••••••••••••</small>
                    </button>
                `);
            }
            break;
            
        case 'api_key':
            if (data.api_key) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.api_key}', 'API Key')">
                        <i class="fas fa-code"></i>
                        <span>API Key</span>
                        <small>••••••••••••••••••••••••••••••••</small>
                    </button>
                `);
            }
            if (data.api_url) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.api_url}', 'API URL')">
                        <i class="fas fa-link"></i>
                        <span>API URL</span>
                        <small>${data.api_url}</small>
                    </button>
                `);
            }
            break;
            
        case 'database_connection':
            if (data.host) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.host}', 'Host')">
                        <i class="fas fa-server"></i>
                        <span>Host</span>
                        <small>${data.host}</small>
                    </button>
                `);
            }
            if (data.username) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.username}', 'Username')">
                        <i class="fas fa-user"></i>
                        <span>Username</span>
                        <small>${data.username}</small>
                    </button>
                `);
            }
            if (data.password) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.password}', 'Password')">
                        <i class="fas fa-key"></i>
                        <span>Password</span>
                        <small>••••••••••••</small>
                    </button>
                `);
            }
            if (data.connection_string) {
                options.push(`
                    <button class="copy-option-btn" onclick="copyToClipboard('${data.connection_string}', 'Connection String')">
                        <i class="fas fa-link"></i>
                        <span>Connection String</span>
                        <small>••••••••••••••••••••••••••••••••</small>
                    </button>
                `);
            }
            break;
            
        // Add more credential types as needed...
        default:
            const jsonData = JSON.stringify(data, null, 2);
            options.push(`
                <button class="copy-option-btn" onclick="copyToClipboard('${jsonData.replace(/'/g, "\\'")}', 'Credential Data')">
                    <i class="fas fa-file-code"></i>
                    <span>All Data (JSON)</span>
                    <small>Complete credential data</small>
                </button>
            `);
            break;
    }
    
    return options.join('');
}

/**
 * Rotate credential
 */
async function rotateCredential(credentialId) {
    if (!vaultState.isUnlocked) {
        showNotification('Vault is locked', 'error');
        return;
    }
    
    const confirmed = await showRotationConfirmationDialog();
    if (!confirmed) return;
    
    try {
        showNotification('Rotating credential...', 'info');
        
        const response = await fetch(`/api/v1/vault/credentials/${credentialId}/rotate`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            await loadCredentials();
            showNotification('Credential rotated successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('credential_rotated', {
                action: 'credential_rotated',
                credential_id: credentialId,
                rotation_method: result.rotation_method,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to rotate credential', 'error');
        }
    } catch (error) {
        console.error('Error rotating credential:', error);
        showNotification('Failed to rotate credential', 'error');
    }
}

/**
 * Show rotation confirmation dialog
 */
function showRotationConfirmationDialog() {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal rotation-confirmation-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2><i class="fas fa-sync"></i> Confirm Credential Rotation</h2>
                </div>
                <div class="modal-body">
                    <div class="rotation-info">
                        <p>Credential rotation will:</p>
                        <ul>
                            <li>Generate new credential values</li>
                            <li>Update the credential in the vault</li>
                            <li>Maintain access history</li>
                            <li>Notify users with access (if enabled)</li>
                        </ul>
                        <div class="rotation-options">
                            <label class="checkbox-label">
                                <input type="checkbox" id="notifyUsersRotation" checked>
                                Notify users with access to this credential
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" id="updateDependentServices">
                                Attempt to update dependent services automatically
                            </label>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeRotationModal()">Cancel</button>
                    <button type="button" class="btn btn-warning" onclick="confirmRotation()">
                        <i class="fas fa-sync"></i> Rotate Credential
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.classList.add('show');
        
        window.closeRotationModal = () => {
            modal.remove();
            resolve(false);
        };
        
        window.confirmRotation = () => {
            const notifyUsers = modal.querySelector('#notifyUsersRotation').checked;
            const updateServices = modal.querySelector('#updateDependentServices').checked;
            modal.remove();
            resolve({ confirmed: true, notifyUsers, updateServices });
        };
    });
}

/**
 * Show bulk import modal
 */
function showBulkImportModal() {
    const modal = document.getElementById('bulkImportModal');
    if (modal) {
        modal.classList.add('show');
    }
}

/**
 * Close bulk import modal
 */
function closeBulkImportModal() {
    const modal = document.getElementById('bulkImportModal');
    if (modal) {
        modal.classList.remove('show');
        
        // Reset form
        const form = modal.querySelector('form');
        if (form) {
            form.reset();
        }
        
        // Clear preview
        const preview = document.getElementById('importPreview');
        if (preview) {
            preview.style.display = 'none';
        }
        
        // Disable import button
        const importBtn = document.getElementById('importBtn');
        if (importBtn) {
            importBtn.disabled = true;
        }
    }
}

/**
 * Validate import file
 */
function validateImportFile() {
    const fileInput = document.getElementById('importFile');
    const preview = document.getElementById('importPreview');
    const previewContent = document.getElementById('previewContent');
    const importBtn = document.getElementById('importBtn');
    
    if (!fileInput || !fileInput.files.length) {
        preview.style.display = 'none';
        importBtn.disabled = true;
        return;
    }
    
    const file = fileInput.files[0];
    const reader = new FileReader();
    
    reader.onload = function(e) {
        try {
            let data;
            const content = e.target.result;
            
            if (file.name.endsWith('.json')) {
                data = JSON.parse(content);
            } else if (file.name.endsWith('.csv')) {
                data = parseCSV(content);
            } else {
                throw new Error('Unsupported file format');
            }
            
            // Validate data structure
            const validationResult = validateImportData(data);
            if (!validationResult.valid) {
                showNotification(validationResult.error, 'error');
                importBtn.disabled = true;
                return;
            }
            
            // Show preview
            previewContent.innerHTML = generateImportPreview(data);
            preview.style.display = 'block';
            importBtn.disabled = false;
            
        } catch (error) {
            showNotification('Invalid file format: ' + error.message, 'error');
            preview.style.display = 'none';
            importBtn.disabled = true;
        }
    };
    
    reader.readAsText(file);
}

/**
 * Parse CSV content
 */
function parseCSV(content) {
    const lines = content.split('\n').filter(line => line.trim());
    if (lines.length < 2) throw new Error('CSV must have header and at least one data row');
    
    const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
    const data = [];
    
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim().replace(/"/g, ''));
        const row = {};
        
        headers.forEach((header, index) => {
            row[header] = values[index] || '';
        });
        
        data.push(row);
    }
    
    return data;
}

/**
 * Validate import data
 */
function validateImportData(data) {
    if (!Array.isArray(data)) {
        return { valid: false, error: 'Data must be an array of credentials' };
    }
    
    if (data.length === 0) {
        return { valid: false, error: 'No credentials found in file' };
    }
    
    const requiredFields = ['name', 'credential_type', 'environment', 'service'];
    
    for (let i = 0; i < data.length; i++) {
        const credential = data[i];
        
        for (const field of requiredFields) {
            if (!credential[field]) {
                return { 
                    valid: false, 
                    error: `Missing required field '${field}' in row ${i + 1}` 
                };
            }
        }
        
        // Validate credential type
        const validTypes = ['password', 'api_key', 'certificate', 'ssh_key', 'token', 'database_connection', 'oauth_credentials'];
        if (!validTypes.includes(credential.credential_type)) {
            return { 
                valid: false, 
                error: `Invalid credential type '${credential.credential_type}' in row ${i + 1}` 
            };
        }
    }
    
    return { valid: true };
}

/**
 * Generate import preview
 */
function generateImportPreview(data) {
    const maxPreview = 5;
    const previewData = data.slice(0, maxPreview);
    
    let html = `
        <div class="import-summary">
            <p><strong>Found ${data.length} credentials to import</strong></p>
            ${data.length > maxPreview ? `<p>Showing first ${maxPreview} entries:</p>` : ''}
        </div>
        <div class="import-preview-table">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Environment</th>
                        <th>Service</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    previewData.forEach(credential => {
        html += `
            <tr>
                <td>${escapeHtml(credential.name)}</td>
                <td>${escapeHtml(credential.credential_type)}</td>
                <td>${escapeHtml(credential.environment)}</td>
                <td>${escapeHtml(credential.service)}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    return html;
}

/**
 * Process bulk import
 */
async function processBulkImport() {
    if (!vaultState.isUnlocked) {
        showNotification('Vault is locked', 'error');
        return;
    }
    
    const fileInput = document.getElementById('importFile');
    if (!fileInput || !fileInput.files.length) {
        showNotification('Please select a file to import', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const reader = new FileReader();
    
    reader.onload = async function(e) {
        try {
            let data;
            const content = e.target.result;
            
            if (file.name.endsWith('.json')) {
                data = JSON.parse(content);
            } else if (file.name.endsWith('.csv')) {
                data = parseCSV(content);
            }
            
            // Process import
            await performBulkImport(data);
            
        } catch (error) {
            showNotification('Import failed: ' + error.message, 'error');
        }
    };
    
    reader.readAsText(file);
}

/**
 * Perform bulk import
 */
async function performBulkImport(data) {
    const importBtn = document.getElementById('importBtn');
    const originalText = importBtn.innerHTML;
    
    try {
        importBtn.disabled = true;
        importBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';
        
        const response = await fetch('/api/v1/vault/credentials/bulk-import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            },
            body: JSON.stringify({ credentials: data })
        });
        
        if (response.ok) {
            const result = await response.json();
            closeBulkImportModal();
            await loadCredentials();
            
            showNotification(
                `Successfully imported ${result.imported} credentials${result.failed > 0 ? `, ${result.failed} failed` : ''}`, 
                'success'
            );
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('bulk_import', {
                action: 'bulk_import_completed',
                imported_count: result.imported,
                failed_count: result.failed,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Bulk import failed', 'error');
        }
    } catch (error) {
        console.error('Error during bulk import:', error);
        showNotification('Bulk import failed', 'error');
    } finally {
        importBtn.disabled = false;
        importBtn.innerHTML = originalText;
    }
}

/**
 * Export credentials
 */
async function exportCredentials() {
    if (!vaultState.isUnlocked) {
        showNotification('Vault is locked', 'error');
        return;
    }
    
    const format = await showExportFormatDialog();
    if (!format) return;
    
    try {
        const response = await fetch(`/api/v1/vault/credentials/export?format=${format}`, {
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `credentials-export-${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showNotification('Credentials exported successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('credentials_exported', {
                action: 'credentials_exported',
                format: format,
                timestamp: new Date().toISOString()
            });
        } else {
            showNotification('Export failed', 'error');
        }
    } catch (error) {
        console.error('Error exporting credentials:', error);
        showNotification('Export failed', 'error');
    }
}

/**
 * Show export format dialog
 */
function showExportFormatDialog() {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal export-format-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2><i class="fas fa-download"></i> Export Credentials</h2>
                </div>
                <div class="modal-body">
                    <div class="export-options">
                        <h4>Select export format:</h4>
                        <div class="format-options">
                            <label class="radio-option">
                                <input type="radio" name="exportFormat" value="json" checked>
                                <div class="option-content">
                                    <strong>JSON</strong>
                                    <p>Structured data format, includes all metadata</p>
                                </div>
                            </label>
                            <label class="radio-option">
                                <input type="radio" name="exportFormat" value="csv">
                                <div class="option-content">
                                    <strong>CSV</strong>
                                    <p>Spreadsheet format, basic fields only</p>
                                </div>
                            </label>
                            <label class="radio-option">
                                <input type="radio" name="exportFormat" value="encrypted">
                                <div class="option-content">
                                    <strong>Encrypted Archive</strong>
                                    <p>Password-protected ZIP file with JSON data</p>
                                </div>
                            </label>
                        </div>
                        <div class="export-warning">
                            <i class="fas fa-exclamation-triangle"></i>
                            <p>Exported data contains sensitive information. Handle with care and store securely.</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeExportModal()">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="confirmExport()">
                        <i class="fas fa-download"></i> Export
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.classList.add('show');
        
        window.closeExportModal = () => {
            modal.remove();
            resolve(null);
        };
        
        window.confirmExport = () => {
            const selectedFormat = modal.querySelector('input[name="exportFormat"]:checked').value;
            modal.remove();
            resolve(selectedFormat);
        };
    });
}

/**
 * Show rotation manager
 */
function showRotationManager() {
    // This would open a comprehensive rotation management interface
    showNotification('Rotation Manager - Coming Soon', 'info');
}

/**
 * Show audit log
 */
function showAuditLogModal() {
    const modal = document.getElementById('auditLogModal');
    if (modal) {
        modal.classList.add('show');
        loadAuditLog();
    }
}

/**
 * Close audit log modal
 */
function closeAuditLogModal() {
    const modal = document.getElementById('auditLogModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * Load audit log
 */
async function loadAuditLog() {
    if (!vaultState.isUnlocked) {
        showNotification('Vault is locked', 'error');
        return;
    }
    
    try {
        const dateFrom = document.getElementById('auditDateFrom')?.value;
        const dateTo = document.getElementById('auditDateTo')?.value;
        const action = document.getElementById('auditAction')?.value;
        
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (action) params.append('action', action);
        
        const response = await fetch(`/api/v1/vault/audit-log?${params}`, {
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            const auditLog = await response.json();
            renderAuditLog(auditLog);
        } else {
            showNotification('Failed to load audit log', 'error');
        }
    } catch (error) {
        console.error('Error loading audit log:', error);
        showNotification('Failed to load audit log', 'error');
    }
}

/**
 * Render audit log
 */
function renderAuditLog(auditLog) {
    const container = document.getElementById('auditLogContent');
    if (!container) return;
    
    if (!auditLog || auditLog.length === 0) {
        container.innerHTML = '<p class="text-center">No audit entries found</p>';
        return;
    }
    
    container.innerHTML = auditLog.map(entry => `
        <div class="audit-entry">
            <div class="audit-action">
                <div class="audit-action-icon ${entry.action}">
                    <i class="fas ${getAuditActionIcon(entry.action)}"></i>
                </div>
                <div class="audit-details">
                    <h4>${entry.action.toUpperCase()} - ${escapeHtml(entry.resource_name)}</h4>
                    <p>${escapeHtml(entry.description)}</p>
                    <p><strong>User:</strong> ${escapeHtml(entry.user_id)} | <strong>IP:</strong> ${entry.ip_address}</p>
                </div>
            </div>
            <div class="audit-timestamp">
                ${formatDateTime(entry.timestamp)}
            </div>
        </div>
    `).join('');
}

/**
 * Get audit action icon
 */
function getAuditActionIcon(action) {
    const icons = {
        create: 'fa-plus',
        read: 'fa-eye',
        update: 'fa-edit',
        delete: 'fa-trash',
        rotate: 'fa-sync',
        export: 'fa-download',
        import: 'fa-upload'
    };
    return icons[action] || 'fa-question';
}

/**
 * Generate password
 */
function generatePassword() {
    const length = 16;
    const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?';
    let password = '';
    
    for (let i = 0; i < length; i++) {
        password += charset.charAt(Math.floor(Math.random() * charset.length));
    }
    
    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.value = password;
        passwordInput.type = 'text';
        
        // Hide after 5 seconds
        setTimeout(() => {
            passwordInput.type = 'password';
        }, 5000);
        
        showNotification('Strong password generated', 'success');
    }
}

/**
 * Copy credential data (from action button)
 */
async function copyCredentialData(credentialId) {
    await copyCredential(credentialId);
}