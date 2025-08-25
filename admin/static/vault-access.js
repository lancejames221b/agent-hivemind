/**
 * hAIveMind Vault Access Control - JavaScript Functions
 * Author: Lance James, Unit 221B
 * User permissions, sharing, and access control management
 */

// Global state for access control
let accessControlState = {
    currentTab: 'users',
    users: [],
    filteredUsers: [],
    roles: [],
    sharedCredentials: [],
    accessRequests: [],
    auditLog: [],
    selectedUser: null,
    selectedRequest: null,
    darkMode: localStorage.getItem('vault_dark_mode') === 'true'
};

// Initialize access control interface
document.addEventListener('DOMContentLoaded', function() {
    initializeAccessControl();
    loadOverviewData();
    loadUsers();
    setupEventListeners();
});

/**
 * Initialize access control interface
 */
function initializeAccessControl() {
    // Apply dark mode if enabled
    if (accessControlState.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
        updateDarkModeIcon();
    }
    
    // Show default tab
    showTab('users');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // User search
    const userSearch = document.getElementById('userSearch');
    if (userSearch) {
        userSearch.addEventListener('input', debounce(searchUsers, 300));
    }
    
    // User filters
    const userFilters = ['userRoleFilter', 'userStatusFilter'];
    userFilters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.addEventListener('change', filterUsers);
        }
    });
    
    // Request filters
    const requestFilters = ['requestStatusFilter', 'requestTypeFilter'];
    requestFilters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.addEventListener('change', filterRequests);
        }
    });
}

/**
 * Show tab
 */
function showTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
    
    accessControlState.currentTab = tabName;
    
    // Load tab-specific data
    switch (tabName) {
        case 'users':
            loadUsers();
            break;
        case 'permissions':
            loadRoles();
            break;
        case 'sharing':
            loadSharedCredentials();
            break;
        case 'requests':
            loadAccessRequests();
            break;
        case 'audit':
            loadAuditUsers();
            break;
    }
}

/**
 * Load overview data
 */
async function loadOverviewData() {
    try {
        const response = await fetch('/api/v1/vault/access/overview', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const overview = await response.json();
            updateOverviewCards(overview);
        }
    } catch (error) {
        console.error('Error loading overview data:', error);
        showNotification('Failed to load overview data', 'error');
    }
}

/**
 * Update overview cards
 */
function updateOverviewCards(overview) {
    const elements = {
        totalUsers: overview.total_users || 0,
        activeUsers: overview.active_users || 0,
        sharedCredentials: overview.shared_credentials || 0,
        pendingRequests: overview.pending_requests || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
}

/**
 * Load users
 */
async function loadUsers() {
    try {
        const response = await fetch('/api/v1/vault/access/users', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const users = await response.json();
            accessControlState.users = users;
            accessControlState.filteredUsers = users;
            renderUsersTable();
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showNotification('Failed to load users', 'error');
    }
}

/**
 * Render users table
 */
function renderUsersTable() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;
    
    if (accessControlState.filteredUsers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">No users found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = accessControlState.filteredUsers.map(user => `
        <tr>
            <td>
                <div class="user-info">
                    <div class="user-avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="user-details">
                        <div class="user-name">${escapeHtml(user.name || user.email)}</div>
                        <div class="user-email">${escapeHtml(user.email)}</div>
                    </div>
                </div>
            </td>
            <td>
                <span class="role-badge ${user.role}">${user.role.toUpperCase()}</span>
            </td>
            <td>
                <span class="status-badge ${user.status}">${user.status.toUpperCase()}</span>
            </td>
            <td>
                <span class="last-access">${formatDateTime(user.last_access)}</span>
            </td>
            <td>
                <span class="credential-count">${user.credential_access_count || 0}</span>
            </td>
            <td>
                <div class="user-actions">
                    <button class="btn btn-sm btn-outline" onclick="viewUserDetails('${user.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline" onclick="editUserPermissions('${user.id}')" title="Edit Permissions">
                        <i class="fas fa-key"></i>
                    </button>
                    <button class="btn btn-sm btn-outline" onclick="toggleUserStatus('${user.id}')" title="Toggle Status">
                        <i class="fas ${user.status === 'active' ? 'fa-pause' : 'fa-play'}"></i>
                    </button>
                    ${user.status !== 'active' ? `
                    <button class="btn btn-sm btn-danger" onclick="removeUser('${user.id}')" title="Remove User">
                        <i class="fas fa-trash"></i>
                    </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * Search users
 */
function searchUsers() {
    const searchTerm = document.getElementById('userSearch').value.toLowerCase();
    
    if (!searchTerm) {
        accessControlState.filteredUsers = accessControlState.users;
    } else {
        accessControlState.filteredUsers = accessControlState.users.filter(user =>
            user.name?.toLowerCase().includes(searchTerm) ||
            user.email.toLowerCase().includes(searchTerm) ||
            user.role.toLowerCase().includes(searchTerm)
        );
    }
    
    renderUsersTable();
}

/**
 * Filter users
 */
function filterUsers() {
    const roleFilter = document.getElementById('userRoleFilter').value;
    const statusFilter = document.getElementById('userStatusFilter').value;
    const searchTerm = document.getElementById('userSearch').value.toLowerCase();
    
    let filtered = accessControlState.users;
    
    // Apply search
    if (searchTerm) {
        filtered = filtered.filter(user =>
            user.name?.toLowerCase().includes(searchTerm) ||
            user.email.toLowerCase().includes(searchTerm) ||
            user.role.toLowerCase().includes(searchTerm)
        );
    }
    
    // Apply role filter
    if (roleFilter) {
        filtered = filtered.filter(user => user.role === roleFilter);
    }
    
    // Apply status filter
    if (statusFilter) {
        filtered = filtered.filter(user => user.status === statusFilter);
    }
    
    accessControlState.filteredUsers = filtered;
    renderUsersTable();
}

/**
 * Show invite user modal
 */
function showInviteUserModal() {
    const modal = document.getElementById('inviteUserModal');
    if (modal) {
        document.getElementById('inviteUserForm').reset();
        modal.classList.add('show');
    }
}

/**
 * Close invite user modal
 */
function closeInviteUserModal() {
    const modal = document.getElementById('inviteUserModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * Invite user
 */
async function inviteUser(event) {
    event.preventDefault();
    
    const inviteData = {
        email: document.getElementById('inviteEmail').value,
        role: document.getElementById('inviteRole').value,
        message: document.getElementById('inviteMessage').value,
        require_mfa: document.getElementById('inviteRequireMFA').checked
    };
    
    try {
        const response = await fetch('/api/v1/vault/access/users/invite', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(inviteData)
        });
        
        if (response.ok) {
            closeInviteUserModal();
            await loadUsers();
            await loadOverviewData();
            showNotification('User invitation sent successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('user_invited', {
                action: 'user_invited',
                email: inviteData.email,
                role: inviteData.role,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to send invitation', 'error');
        }
    } catch (error) {
        console.error('Error inviting user:', error);
        showNotification('Failed to send invitation', 'error');
    }
}

/**
 * View user details
 */
async function viewUserDetails(userId) {
    try {
        const response = await fetch(`/api/v1/vault/access/users/${userId}`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const user = await response.json();
            showUserDetailsModal(user);
        } else {
            showNotification('Failed to load user details', 'error');
        }
    } catch (error) {
        console.error('Error loading user details:', error);
        showNotification('Failed to load user details', 'error');
    }
}

/**
 * Show user details modal
 */
function showUserDetailsModal(user) {
    const modal = document.getElementById('userDetailsModal');
    const title = document.getElementById('userDetailsTitle');
    const content = document.getElementById('userDetailsContent');
    
    if (!modal || !title || !content) return;
    
    title.textContent = `${user.name || user.email} - Details`;
    content.innerHTML = renderUserDetails(user);
    
    accessControlState.selectedUser = user;
    modal.classList.add('show');
}

/**
 * Render user details
 */
function renderUserDetails(user) {
    return `
        <div class="user-details-container">
            <div class="detail-section">
                <h4><i class="fas fa-user"></i> Basic Information</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Name:</label>
                        <span>${escapeHtml(user.name || 'Not provided')}</span>
                    </div>
                    <div class="detail-item">
                        <label>Email:</label>
                        <span>${escapeHtml(user.email)}</span>
                    </div>
                    <div class="detail-item">
                        <label>Role:</label>
                        <span class="role-badge ${user.role}">${user.role.toUpperCase()}</span>
                    </div>
                    <div class="detail-item">
                        <label>Status:</label>
                        <span class="status-badge ${user.status}">${user.status.toUpperCase()}</span>
                    </div>
                    <div class="detail-item">
                        <label>Created:</label>
                        <span>${formatDateTime(user.created_at)}</span>
                    </div>
                    <div class="detail-item">
                        <label>Last Access:</label>
                        <span>${formatDateTime(user.last_access)}</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4><i class="fas fa-shield-alt"></i> Security Information</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>MFA Enabled:</label>
                        <span class="${user.mfa_enabled ? 'text-success' : 'text-warning'}">
                            <i class="fas ${user.mfa_enabled ? 'fa-check' : 'fa-times'}"></i>
                            ${user.mfa_enabled ? 'Yes' : 'No'}
                        </span>
                    </div>
                    <div class="detail-item">
                        <label>Failed Login Attempts:</label>
                        <span>${user.failed_login_attempts || 0}</span>
                    </div>
                    <div class="detail-item">
                        <label>Account Locked:</label>
                        <span class="${user.locked ? 'text-danger' : 'text-success'}">
                            ${user.locked ? 'Yes' : 'No'}
                        </span>
                    </div>
                    <div class="detail-item">
                        <label>Last IP Address:</label>
                        <span>${user.last_ip_address || 'Unknown'}</span>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4><i class="fas fa-key"></i> Credential Access</h4>
                <div class="credential-access-stats">
                    <div class="access-stat">
                        <span class="stat-value">${user.credential_access_count || 0}</span>
                        <span class="stat-label">Total Access</span>
                    </div>
                    <div class="access-stat">
                        <span class="stat-value">${user.owned_credentials_count || 0}</span>
                        <span class="stat-label">Owned Credentials</span>
                    </div>
                    <div class="access-stat">
                        <span class="stat-value">${user.shared_credentials_count || 0}</span>
                        <span class="stat-label">Shared With User</span>
                    </div>
                </div>
            </div>
            
            ${user.recent_activity && user.recent_activity.length > 0 ? `
            <div class="detail-section">
                <h4><i class="fas fa-history"></i> Recent Activity</h4>
                <div class="activity-list">
                    ${user.recent_activity.map(activity => `
                        <div class="activity-item">
                            <div class="activity-icon">
                                <i class="fas ${getActivityIcon(activity.action)}"></i>
                            </div>
                            <div class="activity-details">
                                <div class="activity-description">${activity.description}</div>
                                <div class="activity-timestamp">${formatDateTime(activity.timestamp)}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

/**
 * Close user details modal
 */
function closeUserDetailsModal() {
    const modal = document.getElementById('userDetailsModal');
    if (modal) {
        modal.classList.remove('show');
        accessControlState.selectedUser = null;
    }
}

/**
 * Toggle user status
 */
async function toggleUserStatus(userId) {
    const user = accessControlState.users.find(u => u.id === userId);
    if (!user) return;
    
    const newStatus = user.status === 'active' ? 'inactive' : 'active';
    const action = newStatus === 'active' ? 'activate' : 'deactivate';
    
    if (!confirm(`Are you sure you want to ${action} this user?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/vault/access/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (response.ok) {
            await loadUsers();
            await loadOverviewData();
            showNotification(`User ${action}d successfully`, 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('user_status_changed', {
                action: 'user_status_changed',
                user_id: userId,
                old_status: user.status,
                new_status: newStatus,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || `Failed to ${action} user`, 'error');
        }
    } catch (error) {
        console.error(`Error ${action}ing user:`, error);
        showNotification(`Failed to ${action} user`, 'error');
    }
}

/**
 * Load roles
 */
async function loadRoles() {
    try {
        const response = await fetch('/api/v1/vault/access/roles', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const roles = await response.json();
            accessControlState.roles = roles;
            renderRolesGrid();
        }
    } catch (error) {
        console.error('Error loading roles:', error);
        showNotification('Failed to load roles', 'error');
    }
}

/**
 * Render roles grid
 */
function renderRolesGrid() {
    const rolesGrid = document.getElementById('rolesGrid');
    if (!rolesGrid) return;
    
    rolesGrid.innerHTML = accessControlState.roles.map(role => `
        <div class="role-card">
            <div class="role-header">
                <h4>${role.name.toUpperCase()}</h4>
                <div class="role-actions">
                    <button class="btn btn-sm btn-outline" onclick="editRole('${role.id}')" title="Edit Role">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${role.name !== 'admin' ? `
                    <button class="btn btn-sm btn-danger" onclick="deleteRole('${role.id}')" title="Delete Role">
                        <i class="fas fa-trash"></i>
                    </button>
                    ` : ''}
                </div>
            </div>
            <div class="role-description">
                ${escapeHtml(role.description || 'No description provided')}
            </div>
            <div class="role-permissions">
                <h5>Permissions:</h5>
                <div class="permission-list">
                    ${role.permissions.map(permission => `
                        <span class="permission-badge">${permission}</span>
                    `).join('')}
                </div>
            </div>
            <div class="role-stats">
                <div class="stat-item">
                    <i class="fas fa-users"></i>
                    <span>${role.user_count || 0} users</span>
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Load shared credentials
 */
async function loadSharedCredentials() {
    try {
        const response = await fetch('/api/v1/vault/access/shared-credentials', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const sharedCredentials = await response.json();
            accessControlState.sharedCredentials = sharedCredentials;
            renderSharedCredentialsTable();
            updateSharingStats();
        }
    } catch (error) {
        console.error('Error loading shared credentials:', error);
        showNotification('Failed to load shared credentials', 'error');
    }
}

/**
 * Render shared credentials table
 */
function renderSharedCredentialsTable() {
    const tbody = document.getElementById('sharedCredentialsBody');
    if (!tbody) return;
    
    if (accessControlState.sharedCredentials.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center">No shared credentials found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = accessControlState.sharedCredentials.map(share => `
        <tr>
            <td>
                <div class="credential-info">
                    <div class="credential-name">${escapeHtml(share.credential_name)}</div>
                    <div class="credential-type">${share.credential_type.replace('_', ' ').toUpperCase()}</div>
                </div>
            </td>
            <td>
                <div class="user-info">
                    <div class="user-name">${escapeHtml(share.shared_with_name || share.shared_with_email)}</div>
                    <div class="user-email">${escapeHtml(share.shared_with_email)}</div>
                </div>
            </td>
            <td>
                <span class="permission-badge ${share.permission_level}">${share.permission_level.toUpperCase()}</span>
            </td>
            <td>
                <span class="share-date">${formatDate(share.shared_at)}</span>
            </td>
            <td>
                <span class="expires-date ${share.expires_at && new Date(share.expires_at) < new Date() ? 'expired' : ''}">
                    ${share.expires_at ? formatDate(share.expires_at) : 'Never'}
                </span>
            </td>
            <td>
                <div class="share-actions">
                    <button class="btn btn-sm btn-outline" onclick="editShare('${share.id}')" title="Edit Share">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="revokeShare('${share.id}')" title="Revoke Share">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * Update sharing stats
 */
function updateSharingStats() {
    const totalShares = accessControlState.sharedCredentials.length;
    const temporaryShares = accessControlState.sharedCredentials.filter(share => share.expires_at).length;
    const expiringShares = accessControlState.sharedCredentials.filter(share => {
        if (!share.expires_at) return false;
        const expiresAt = new Date(share.expires_at);
        const now = new Date();
        const daysUntilExpiry = Math.ceil((expiresAt - now) / (1000 * 60 * 60 * 24));
        return daysUntilExpiry <= 7 && daysUntilExpiry > 0;
    }).length;
    
    document.getElementById('totalShares').textContent = totalShares;
    document.getElementById('temporaryShares').textContent = temporaryShares;
    document.getElementById('expiringShares').textContent = expiringShares;
}

/**
 * Show share credential modal
 */
async function showShareCredentialModal() {
    const modal = document.getElementById('shareCredentialModal');
    if (!modal) return;
    
    // Load credentials and users for dropdowns
    await loadCredentialsForSharing();
    await loadUsersForSharing();
    
    document.getElementById('shareCredentialForm').reset();
    modal.classList.add('show');
}

/**
 * Load credentials for sharing dropdown
 */
async function loadCredentialsForSharing() {
    try {
        const response = await fetch('/api/v1/vault/credentials', {
            headers: {
                ...getAuthHeaders(),
                'X-Vault-Token': sessionStorage.getItem('vault_token')
            }
        });
        
        if (response.ok) {
            const credentials = await response.json();
            const select = document.getElementById('shareCredentialSelect');
            if (select) {
                select.innerHTML = '<option value="">Select Credential</option>' +
                    credentials.map(cred => `
                        <option value="${cred.id}">${escapeHtml(cred.name)} (${cred.credential_type})</option>
                    `).join('');
            }
        }
    } catch (error) {
        console.error('Error loading credentials for sharing:', error);
    }
}

/**
 * Load users for sharing dropdown
 */
async function loadUsersForSharing() {
    try {
        const response = await fetch('/api/v1/vault/access/users', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const users = await response.json();
            const select = document.getElementById('shareUserSelect');
            if (select) {
                select.innerHTML = '<option value="">Select User</option>' +
                    users.filter(user => user.status === 'active').map(user => `
                        <option value="${user.id}">${escapeHtml(user.name || user.email)} (${user.email})</option>
                    `).join('');
            }
        }
    } catch (error) {
        console.error('Error loading users for sharing:', error);
    }
}

/**
 * Close share credential modal
 */
function closeShareCredentialModal() {
    const modal = document.getElementById('shareCredentialModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * Share credential
 */
async function shareCredential(event) {
    event.preventDefault();
    
    const shareData = {
        credential_id: document.getElementById('shareCredentialSelect').value,
        user_id: document.getElementById('shareUserSelect').value,
        permission_level: document.getElementById('sharePermissionLevel').value,
        expires_at: document.getElementById('shareExpiresAt').value || null,
        reason: document.getElementById('shareReason').value,
        notify_user: document.getElementById('shareNotifyUser').checked
    };
    
    try {
        const response = await fetch('/api/v1/vault/access/share-credential', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(shareData)
        });
        
        if (response.ok) {
            closeShareCredentialModal();
            await loadSharedCredentials();
            showNotification('Credential shared successfully', 'success');
            
            // Store hAIveMind memory
            await storeHAIveMindMemory('credential_shared', {
                action: 'credential_shared',
                credential_id: shareData.credential_id,
                user_id: shareData.user_id,
                permission_level: shareData.permission_level,
                timestamp: new Date().toISOString()
            });
        } else {
            const error = await response.json();
            showNotification(error.detail || 'Failed to share credential', 'error');
        }
    } catch (error) {
        console.error('Error sharing credential:', error);
        showNotification('Failed to share credential', 'error');
    }
}

/**
 * Load access requests
 */
async function loadAccessRequests() {
    try {
        const response = await fetch('/api/v1/vault/access/requests', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const requests = await response.json();
            accessControlState.accessRequests = requests;
            renderAccessRequestsList();
        }
    } catch (error) {
        console.error('Error loading access requests:', error);
        showNotification('Failed to load access requests', 'error');
    }
}

/**
 * Render access requests list
 */
function renderAccessRequestsList() {
    const requestsList = document.getElementById('requestsList');
    if (!requestsList) return;
    
    if (accessControlState.accessRequests.length === 0) {
        requestsList.innerHTML = '<p class="text-center">No access requests found</p>';
        return;
    }
    
    requestsList.innerHTML = accessControlState.accessRequests.map(request => `
        <div class="request-item ${request.status}" onclick="viewRequestDetails('${request.id}')">
            <div class="request-header">
                <div class="request-type">
                    <i class="fas ${getRequestTypeIcon(request.type)}"></i>
                    <span>${request.type.replace('_', ' ').toUpperCase()}</span>
                </div>
                <div class="request-status">
                    <span class="status-badge ${request.status}">${request.status.toUpperCase()}</span>
                </div>
            </div>
            <div class="request-details">
                <div class="request-user">
                    <strong>Requested by:</strong> ${escapeHtml(request.requester_name || request.requester_email)}
                </div>
                <div class="request-description">
                    ${escapeHtml(request.description)}
                </div>
                <div class="request-meta">
                    <span class="request-date">
                        <i class="fas fa-calendar"></i>
                        ${formatDateTime(request.created_at)}
                    </span>
                    ${request.expires_at ? `
                    <span class="request-expires">
                        <i class="fas fa-clock"></i>
                        Expires: ${formatDateTime(request.expires_at)}
                    </span>
                    ` : ''}
                </div>
            </div>
            ${request.status === 'pending' ? `
            <div class="request-actions" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-success" onclick="approveRequest('${request.id}')">
                    <i class="fas fa-check"></i> Approve
                </button>
                <button class="btn btn-sm btn-danger" onclick="denyRequest('${request.id}')">
                    <i class="fas fa-times"></i> Deny
                </button>
            </div>
            ` : ''}
        </div>
    `).join('');
}

/**
 * Filter requests
 */
function filterRequests() {
    const statusFilter = document.getElementById('requestStatusFilter').value;
    const typeFilter = document.getElementById('requestTypeFilter').value;
    
    // This would filter the requests and re-render
    // For now, just reload all requests
    loadAccessRequests();
}

/**
 * Refresh requests
 */
function refreshRequests() {
    loadAccessRequests();
}

/**
 * Load audit users for filter dropdown
 */
async function loadAuditUsers() {
    try {
        const response = await fetch('/api/v1/vault/access/users', {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const users = await response.json();
            const select = document.getElementById('auditUserFilter');
            if (select) {
                select.innerHTML = '<option value="">All Users</option>' +
                    users.map(user => `
                        <option value="${user.id}">${escapeHtml(user.name || user.email)}</option>
                    `).join('');
            }
        }
    } catch (error) {
        console.error('Error loading users for audit filter:', error);
    }
}

/**
 * Load audit log
 */
async function loadAuditLog() {
    const dateFrom = document.getElementById('auditDateFrom').value;
    const dateTo = document.getElementById('auditDateTo').value;
    const userFilter = document.getElementById('auditUserFilter').value;
    const actionFilter = document.getElementById('auditActionFilter').value;
    
    const params = new URLSearchParams();
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (userFilter) params.append('user_id', userFilter);
    if (actionFilter) params.append('action', actionFilter);
    
    try {
        const response = await fetch(`/api/v1/vault/access/audit-log?${params}`, {
            headers: getAuthHeaders()
        });
        
        if (response.ok) {
            const auditLog = await response.json();
            accessControlState.auditLog = auditLog;
            renderAuditLog();
        }
    } catch (error) {
        console.error('Error loading audit log:', error);
        showNotification('Failed to load audit log', 'error');
    }
}

/**
 * Render audit log
 */
function renderAuditLog() {
    const container = document.getElementById('auditLogContainer');
    if (!container) return;
    
    if (accessControlState.auditLog.length === 0) {
        container.innerHTML = '<p class="text-center">No audit entries found</p>';
        return;
    }
    
    container.innerHTML = accessControlState.auditLog.map(entry => `
        <div class="audit-entry">
            <div class="audit-icon">
                <i class="fas ${getAuditActionIcon(entry.action)}"></i>
            </div>
            <div class="audit-details">
                <div class="audit-action">${entry.action.replace('_', ' ').toUpperCase()}</div>
                <div class="audit-description">${escapeHtml(entry.description)}</div>
                <div class="audit-meta">
                    <span class="audit-user">${escapeHtml(entry.user_name || entry.user_email)}</span>
                    <span class="audit-timestamp">${formatDateTime(entry.timestamp)}</span>
                    <span class="audit-ip">${entry.ip_address}</span>
                </div>
            </div>
        </div>
    `).join('');
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

function getActivityIcon(action) {
    const icons = {
        login: 'fa-sign-in-alt',
        logout: 'fa-sign-out-alt',
        credential_access: 'fa-key',
        permission_change: 'fa-user-cog',
        share_credential: 'fa-share'
    };
    return icons[action] || 'fa-circle';
}

function getRequestTypeIcon(type) {
    const icons = {
        credential_access: 'fa-key',
        role_elevation: 'fa-arrow-up',
        emergency_access: 'fa-exclamation-triangle'
    };
    return icons[type] || 'fa-question';
}

function getAuditActionIcon(action) {
    const icons = {
        login: 'fa-sign-in-alt',
        logout: 'fa-sign-out-alt',
        credential_access: 'fa-key',
        permission_change: 'fa-user-cog',
        share_credential: 'fa-share'
    };
    return icons[action] || 'fa-circle';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

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

function toggleDarkMode() {
    accessControlState.darkMode = !accessControlState.darkMode;
    localStorage.setItem('vault_dark_mode', accessControlState.darkMode.toString());
    
    if (accessControlState.darkMode) {
        document.documentElement.setAttribute('data-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    
    updateDarkModeIcon();
}

function updateDarkModeIcon() {
    const darkModeBtn = document.querySelector('.dark-mode-toggle i');
    if (darkModeBtn) {
        darkModeBtn.className = accessControlState.darkMode ? 'fas fa-sun' : 'fas fa-moon';
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
                category: `vault_access_${category}`,
                context: 'vault_access_control',
                tags: ['vault', 'access', category]
            })
        });
    } catch (error) {
        console.error('Failed to store hAIveMind memory:', error);
    }
}