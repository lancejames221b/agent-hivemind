// Confluence Integration Dashboard JavaScript

// Global state
let confluenceConfig = null;
let confluenceStatus = null;
let spaces = [];
let selectedPages = [];

// Load initial data when page loads
document.addEventListener('DOMContentLoaded', async () => {
    await loadConfluenceStatus();
});

// Load Confluence status and configuration
async function loadConfluenceStatus() {
    try {
        const [configResponse, statusResponse] = await Promise.all([
            apiRequest('/admin/api/confluence/config'),
            apiRequest('/admin/api/confluence/status')
        ]);
        
        confluenceConfig = configResponse;
        confluenceStatus = statusResponse;
        
        updateStatusDisplay();
        
    } catch (error) {
        console.error('Error loading Confluence status:', error);
        showErrorStatus();
    }
}

// Update status display with real data
function updateStatusDisplay() {
    if (confluenceStatus) {
        document.getElementById('connectionStatus').textContent = 
            confluenceStatus.connection_status || 'Not Configured';
        document.getElementById('lastSync').textContent = 
            confluenceStatus.last_sync ? new Date(confluenceStatus.last_sync * 1000).toLocaleString() : 'Never';
        document.getElementById('monitoredSpaces').textContent = 
            confluenceStatus.monitored_spaces || '0';
        document.getElementById('syncedPages').textContent = 
            confluenceStatus.synced_pages || '0';
            
        // Update status colors
        const statusElement = document.getElementById('connectionStatus');
        statusElement.className = 'status-value';
        if (confluenceStatus.connection_status === 'connected') {
            statusElement.classList.add('status-success');
        } else if (confluenceStatus.connection_status === 'configured') {
            statusElement.classList.add('status-warning');
        } else {
            statusElement.classList.add('status-error');
        }
    }
}

// Show error status when loading fails
function showErrorStatus() {
    document.getElementById('connectionStatus').textContent = 'Error Loading';
    document.getElementById('lastSync').textContent = 'Error';
    document.getElementById('monitoredSpaces').textContent = 'Error';
    document.getElementById('syncedPages').textContent = 'Error';
}

// Configuration modal
async function showConfig() {
    const modal = createModal('Configure Confluence Connection', `
        <form id="confluenceConfigForm">
            <div class="form-group">
                <label for="serverUrl">Confluence Server URL:</label>
                <input type="url" id="serverUrl" required placeholder="https://your-domain.atlassian.net">
            </div>
            <div class="form-group">
                <label for="username">Username/Email:</label>
                <input type="text" id="username" required placeholder="your-email@domain.com">
            </div>
            <div class="form-group">
                <label for="apiToken">API Token:</label>
                <input type="password" id="apiToken" required placeholder="Your Confluence API token">
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Save & Test Connection</button>
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
            </div>
        </form>
    `);
    
    // Pre-fill with existing configuration
    if (confluenceConfig) {
        document.getElementById('serverUrl').value = confluenceConfig.server_url || '';
        document.getElementById('username').value = confluenceConfig.username || '';
    }
    
    document.getElementById('confluenceConfigForm').addEventListener('submit', saveConfig);
}

// Save configuration
async function saveConfig(event) {
    event.preventDefault();
    
    const formData = {
        server_url: document.getElementById('serverUrl').value,
        username: document.getElementById('username').value,
        api_token: document.getElementById('apiToken').value
    };
    
    try {
        const result = await apiRequest('/admin/api/confluence/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        
        showNotification('Configuration saved successfully!', 'success');
        closeModal();
        await loadConfluenceStatus();
        
        // Auto-test connection after saving
        await testConnection();
        
    } catch (error) {
        showNotification('Error saving configuration: ' + error.message, 'error');
    }
}

// Test connection
async function testConnection() {
    try {
        showNotification('Testing Confluence connection...', 'info');
        
        const result = await apiRequest('/admin/api/confluence/test', {
            method: 'POST'
        });
        
        if (result.success) {
            showNotification('Connection successful!', 'success');
        } else {
            showNotification('Connection failed: ' + result.error, 'error');
        }
        
        await loadConfluenceStatus();
        
    } catch (error) {
        showNotification('Error testing connection: ' + error.message, 'error');
    }
}

// Show space mapping
async function showSpaceMapping() {
    try {
        showNotification('Loading Confluence spaces...', 'info');
        
        const spacesData = await apiRequest('/admin/api/confluence/spaces');
        spaces = spacesData.spaces || [];
        
        const modal = createModal('Configure Space Mapping', `
            <div class="spaces-list">
                <h4>Available Spaces (${spaces.length})</h4>
                <div id="spacesList">
                    ${spaces.map(space => `
                        <div class="space-item">
                            <h5><i class="fab fa-confluence"></i> ${space.name}</h5>
                            <p>Key: ${space.key} | Pages: ${space.page_count || 0}</p>
                            <button class="btn btn-small btn-info" onclick="viewSpacePages('${space.key}')">
                                View Pages
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>
        `);
        
    } catch (error) {
        showNotification('Error loading spaces: ' + error.message, 'error');
    }
}

// View pages in a space
async function viewSpacePages(spaceKey) {
    try {
        showNotification(`Loading pages from space ${spaceKey}...`, 'info');
        
        const pagesData = await apiRequest(`/admin/api/confluence/spaces/${spaceKey}/pages`);
        const pages = pagesData.pages || [];
        
        const modal = createModal(`Pages in Space: ${spaceKey}`, `
            <div class="pages-list">
                <h4>${pages.length} pages found</h4>
                <div class="page-selection">
                    <button class="btn btn-small btn-success" onclick="selectAllPages()">Select All</button>
                    <button class="btn btn-small btn-warning" onclick="deselectAllPages()">Deselect All</button>
                </div>
                <div id="pagesList">
                    ${pages.map(page => `
                        <div class="page-item">
                            <input type="checkbox" id="page_${page.id}" value="${page.id}" class="page-checkbox">
                            <label for="page_${page.id}">
                                <h6>${page.title}</h6>
                                <p>ID: ${page.id} | Modified: ${page.last_modified ? new Date(page.last_modified).toLocaleDateString() : 'Unknown'}</p>
                            </label>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="form-actions">
                <button type="button" class="btn btn-primary" onclick="importSelectedPages()">Import Selected Pages</button>
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
            </div>
        `);
        
    } catch (error) {
        showNotification('Error loading pages: ' + error.message, 'error');
    }
}

// Import selected pages
async function importSelectedPages() {
    const checkboxes = document.querySelectorAll('.page-checkbox:checked');
    const pageIds = Array.from(checkboxes).map(cb => cb.value);
    
    if (pageIds.length === 0) {
        showNotification('Please select at least one page to import.', 'warning');
        return;
    }
    
    try {
        showNotification(`Importing ${pageIds.length} pages...`, 'info');
        
        const result = await apiRequest('/admin/api/confluence/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({page_ids: pageIds})
        });
        
        showNotification(`Import completed! ${result.successful} successful, ${result.failed} failed.`, 'success');
        closeModal();
        await loadConfluenceStatus();
        
    } catch (error) {
        showNotification('Error importing pages: ' + error.message, 'error');
    }
}

// Trigger manual sync
async function triggerManualSync() {
    try {
        showNotification('Starting manual sync...', 'info');
        
        const result = await apiRequest('/admin/api/confluence/sync', {
            method: 'POST'
        });
        
        showNotification('Manual sync triggered successfully!', 'success');
        await loadConfluenceStatus();
        
    } catch (error) {
        showNotification('Error triggering sync: ' + error.message, 'error');
    }
}

// Placeholder functions for future features
function showSyncManager() {
    showNotification('Sync manager functionality coming soon!', 'info');
}

function showImportHistory() {
    showNotification('Import history functionality coming soon!', 'info');
}

function viewLogs() {
    showNotification('Sync logs functionality coming soon!', 'info');
}

// Helper functions for page selection
function selectAllPages() {
    document.querySelectorAll('.page-checkbox').forEach(cb => cb.checked = true);
}

function deselectAllPages() {
    document.querySelectorAll('.page-checkbox').forEach(cb => cb.checked = false);
}

// Modal helper functions
function createModal(title, content) {
    // Remove any existing modal
    closeModal();
    
    // Simple modal implementation
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>${title}</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                ${content}
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    return modal;
}

function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) modal.remove();
}

// Notification helper (fallback if admin.js doesn't have it)
function showNotification(message, type) {
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // Try to use existing notification system from admin.js
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
        return;
    }
    
    // Fallback: simple alert for now
    if (type === 'error') {
        alert('Error: ' + message);
    } else if (type === 'success') {
        alert('Success: ' + message);
    } else {
        console.log(message);
    }
}