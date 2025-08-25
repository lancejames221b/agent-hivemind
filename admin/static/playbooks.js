/**
 * Playbook Management JavaScript
 * Handles all playbook creation, editing, execution, and management functionality
 */

let currentPlaybooks = [];
let currentTemplates = [];
let currentPlaybook = null;

// Initialize playbook management interface
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('/admin/playbooks')) {
        initializePlaybookInterface();
        loadPlaybooks();
        loadTemplates();
    }
});

/**
 * Initialize the playbook management interface
 */
function initializePlaybookInterface() {
    // Replace placeholder feature cards with real functionality
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;
    
    // Enhanced playbook management interface
    const playbookInterface = `
        <div class="playbook-header">
            <div class="header-actions">
                <button class="btn btn-primary" onclick="showCreatePlaybookModal()">
                    <i class="fas fa-plus"></i> New Playbook
                </button>
                <button class="btn btn-secondary" onclick="refreshPlaybooks()">
                    <i class="fas fa-refresh"></i> Refresh
                </button>
                <div class="search-container">
                    <input type="text" id="playbook-search" placeholder="Search playbooks..." onkeyup="filterPlaybooks()">
                    <i class="fas fa-search"></i>
                </div>
            </div>
        </div>

        <div class="playbook-stats">
            <div class="stat-card">
                <span class="stat-label">Total Playbooks</span>
                <span class="stat-value" id="total-playbooks">0</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Draft</span>
                <span class="stat-value" id="draft-playbooks">0</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Published</span>
                <span class="stat-value" id="published-playbooks">0</span>
            </div>
            <div class="stat-card">
                <span class="stat-label">Total Executions</span>
                <span class="stat-value" id="total-executions">0</span>
            </div>
        </div>

        <div class="playbook-content">
            <div class="playbook-list">
                <div class="list-header">
                    <h3><i class="fas fa-book"></i> Playbooks</h3>
                    <div class="list-filters">
                        <select id="type-filter" onchange="filterPlaybooks()">
                            <option value="">All Types</option>
                            <option value="ansible">Ansible</option>
                            <option value="terraform">Terraform</option>
                            <option value="kubernetes">Kubernetes</option>
                            <option value="shell">Shell Script</option>
                        </select>
                        <select id="status-filter" onchange="filterPlaybooks()">
                            <option value="">All Status</option>
                            <option value="draft">Draft</option>
                            <option value="published">Published</option>
                        </select>
                    </div>
                </div>
                <div id="playbooks-container" class="playbooks-grid">
                    <div class="loading">Loading playbooks...</div>
                </div>
            </div>
        </div>

        <!-- Create/Edit Playbook Modal -->
        <div id="playbook-modal" class="modal" style="display: none;">
            <div class="modal-content playbook-editor">
                <div class="modal-header">
                    <h2 id="modal-title">Create New Playbook</h2>
                    <span class="close" onclick="closePlaybookModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <div class="editor-tabs">
                        <button class="tab-btn active" onclick="switchTab('details')">Details</button>
                        <button class="tab-btn" onclick="switchTab('content')">Content</button>
                        <button class="tab-btn" onclick="switchTab('variables')">Variables</button>
                        <button class="tab-btn" onclick="switchTab('targets')">Targets</button>
                    </div>

                    <!-- Details Tab -->
                    <div id="details-tab" class="tab-content active">
                        <div class="form-group">
                            <label for="playbook-name">Name *</label>
                            <input type="text" id="playbook-name" required placeholder="Enter playbook name">
                        </div>
                        <div class="form-group">
                            <label for="playbook-description">Description</label>
                            <textarea id="playbook-description" placeholder="Describe what this playbook does" rows="3"></textarea>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="playbook-type">Type</label>
                                <select id="playbook-type" onchange="updateContentTemplate()">
                                    <option value="ansible">Ansible</option>
                                    <option value="terraform">Terraform</option>
                                    <option value="kubernetes">Kubernetes</option>
                                    <option value="shell">Shell Script</option>
                                    <option value="python">Python</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="playbook-status">Status</label>
                                <select id="playbook-status">
                                    <option value="draft">Draft</option>
                                    <option value="published">Published</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="playbook-tags">Tags (comma-separated)</label>
                            <input type="text" id="playbook-tags" placeholder="infrastructure, automation, deployment">
                        </div>
                        <div class="template-selection">
                            <label>Start from Template</label>
                            <div class="template-buttons" id="template-buttons">
                                <!-- Template buttons will be populated here -->
                            </div>
                        </div>
                    </div>

                    <!-- Content Tab -->
                    <div id="content-tab" class="tab-content">
                        <div class="editor-toolbar">
                            <button type="button" onclick="formatPlaybookContent()">
                                <i class="fas fa-code"></i> Format
                            </button>
                            <button type="button" onclick="validatePlaybookContent()">
                                <i class="fas fa-check-circle"></i> Validate
                            </button>
                            <button type="button" onclick="previewPlaybook()">
                                <i class="fas fa-eye"></i> Preview
                            </button>
                        </div>
                        <div class="form-group">
                            <label for="playbook-content">Playbook Content</label>
                            <textarea id="playbook-content" rows="20" placeholder="Enter your playbook content here..."></textarea>
                        </div>
                    </div>

                    <!-- Variables Tab -->
                    <div id="variables-tab" class="tab-content">
                        <div class="variables-header">
                            <h4>Playbook Variables</h4>
                            <button type="button" onclick="addVariable()" class="btn btn-small">
                                <i class="fas fa-plus"></i> Add Variable
                            </button>
                        </div>
                        <div id="variables-container">
                            <!-- Variables will be added here -->
                        </div>
                    </div>

                    <!-- Targets Tab -->
                    <div id="targets-tab" class="tab-content">
                        <div class="targets-header">
                            <h4>Execution Targets</h4>
                            <button type="button" onclick="addTarget()" class="btn btn-small">
                                <i class="fas fa-plus"></i> Add Target
                            </button>
                        </div>
                        <div id="targets-container">
                            <!-- Targets will be added here -->
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" onclick="closePlaybookModal()" class="btn btn-secondary">Cancel</button>
                    <button type="button" onclick="savePlaybook()" class="btn btn-primary" id="save-playbook-btn">Save Playbook</button>
                </div>
            </div>
        </div>

        <!-- Execute Playbook Modal -->
        <div id="execute-modal" class="modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Execute Playbook</h2>
                    <span class="close" onclick="closeExecuteModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <div class="execution-form">
                        <h4 id="exec-playbook-name">Playbook Name</h4>
                        <p id="exec-playbook-description">Playbook description</p>
                        
                        <div class="form-group">
                            <label>Execution Variables</label>
                            <div id="exec-variables-container">
                                <!-- Variables will be populated here -->
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Target Servers</label>
                            <div id="exec-targets-container">
                                <!-- Targets will be populated here -->
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" onclick="closeExecuteModal()" class="btn btn-secondary">Cancel</button>
                    <button type="button" onclick="executePlaybook()" class="btn btn-success">
                        <i class="fas fa-play"></i> Execute Now
                    </button>
                </div>
            </div>
        </div>

        <!-- Execution Results Modal -->
        <div id="execution-results-modal" class="modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Execution Results</h2>
                    <span class="close" onclick="closeExecutionResultsModal()">&times;</span>
                </div>
                <div class="modal-body">
                    <div class="execution-status">
                        <div class="status-indicator" id="exec-status-indicator">
                            <i class="fas fa-spinner fa-spin"></i>
                            <span id="exec-status-text">Running...</span>
                        </div>
                        <div class="execution-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" id="exec-progress-fill" style="width: 0%"></div>
                            </div>
                            <span class="progress-text" id="exec-progress-text">0%</span>
                        </div>
                    </div>
                    <div class="execution-logs">
                        <h4>Execution Logs</h4>
                        <div id="execution-logs-content" class="logs-container">
                            <!-- Logs will be populated here -->
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" onclick="closeExecutionResultsModal()" class="btn btn-secondary">Close</button>
                    <button type="button" onclick="downloadExecutionLogs()" class="btn btn-info">
                        <i class="fas fa-download"></i> Download Logs
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Replace the existing card with the new interface
    const existingCard = mainContent.querySelector('.card');
    if (existingCard) {
        existingCard.innerHTML = `
            <h2><i class="fas fa-book"></i> Playbook Management</h2>
            <p>Create, manage, and execute automated playbooks for DevOps operations.</p>
            ${playbookInterface}
        `;
    }
}

/**
 * Load all playbooks from the backend
 */
async function loadPlaybooks() {
    try {
        const response = await apiRequest('/admin/api/playbooks');
        currentPlaybooks = response.playbooks || [];
        
        updatePlaybookStats();
        displayPlaybooks(currentPlaybooks);
        
    } catch (error) {
        console.error('Error loading playbooks:', error);
        showNotification('Failed to load playbooks', 'error');
        document.getElementById('playbooks-container').innerHTML = 
            '<div class="error">Failed to load playbooks. Please try again.</div>';
    }
}

/**
 * Load available templates
 */
async function loadTemplates() {
    try {
        const response = await apiRequest('/admin/api/playbooks/templates');
        currentTemplates = response.templates || [];
        updateTemplateButtons();
        
    } catch (error) {
        console.error('Error loading templates:', error);
        currentTemplates = [];
    }
}

/**
 * Update playbook statistics
 */
function updatePlaybookStats() {
    const draftCount = currentPlaybooks.filter(p => p.status === 'draft').length;
    const publishedCount = currentPlaybooks.filter(p => p.status === 'published').length;
    const totalExecutions = currentPlaybooks.reduce((sum, p) => sum + (p.execution_count || 0), 0);
    
    document.getElementById('total-playbooks').textContent = currentPlaybooks.length;
    document.getElementById('draft-playbooks').textContent = draftCount;
    document.getElementById('published-playbooks').textContent = publishedCount;
    document.getElementById('total-executions').textContent = totalExecutions;
}

/**
 * Display playbooks in the grid
 */
function displayPlaybooks(playbooks) {
    const container = document.getElementById('playbooks-container');
    
    if (playbooks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-book fa-3x"></i>
                <h3>No Playbooks Found</h3>
                <p>Create your first playbook to get started with automation.</p>
                <button class="btn btn-primary" onclick="showCreatePlaybookModal()">
                    <i class="fas fa-plus"></i> Create Playbook
                </button>
            </div>
        `;
        return;
    }
    
    const playbookCards = playbooks.map(playbook => `
        <div class="playbook-card" data-type="${playbook.type}" data-status="${playbook.status}">
            <div class="playbook-header">
                <div class="playbook-title">
                    <h4>${escapeHtml(playbook.name)}</h4>
                    <span class="playbook-type type-${playbook.type}">${playbook.type}</span>
                </div>
                <div class="playbook-actions">
                    <button class="btn btn-small" onclick="editPlaybook('${playbook.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-small btn-success" onclick="showExecuteModal('${playbook.id}')" title="Execute">
                        <i class="fas fa-play"></i>
                    </button>
                    <button class="btn btn-small btn-danger" onclick="deletePlaybook('${playbook.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="playbook-body">
                <p class="playbook-description">${escapeHtml(playbook.description || 'No description')}</p>
                <div class="playbook-meta">
                    <div class="meta-item">
                        <i class="fas fa-calendar"></i>
                        <span>Created: ${formatDate(playbook.created_at)}</span>
                    </div>
                    <div class="meta-item">
                        <i class="fas fa-play-circle"></i>
                        <span>${playbook.execution_count || 0} executions</span>
                    </div>
                    <div class="meta-item">
                        <span class="status-badge status-${playbook.status}">${playbook.status}</span>
                    </div>
                </div>
                ${playbook.tags && playbook.tags.length > 0 ? `
                    <div class="playbook-tags">
                        ${playbook.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
            <div class="playbook-footer">
                <button class="btn btn-secondary btn-small" onclick="viewExecutionHistory('${playbook.id}')">
                    <i class="fas fa-history"></i> View History
                </button>
                <button class="btn btn-info btn-small" onclick="duplicatePlaybook('${playbook.id}')">
                    <i class="fas fa-copy"></i> Duplicate
                </button>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = playbookCards;
}

/**
 * Filter playbooks based on search and filters
 */
function filterPlaybooks() {
    const searchTerm = document.getElementById('playbook-search').value.toLowerCase();
    const typeFilter = document.getElementById('type-filter').value;
    const statusFilter = document.getElementById('status-filter').value;
    
    const filtered = currentPlaybooks.filter(playbook => {
        const matchesSearch = !searchTerm || 
            playbook.name.toLowerCase().includes(searchTerm) ||
            (playbook.description && playbook.description.toLowerCase().includes(searchTerm)) ||
            (playbook.tags && playbook.tags.some(tag => tag.toLowerCase().includes(searchTerm)));
            
        const matchesType = !typeFilter || playbook.type === typeFilter;
        const matchesStatus = !statusFilter || playbook.status === statusFilter;
        
        return matchesSearch && matchesType && matchesStatus;
    });
    
    displayPlaybooks(filtered);
}

/**
 * Show create playbook modal
 */
function showCreatePlaybookModal() {
    currentPlaybook = null;
    document.getElementById('modal-title').textContent = 'Create New Playbook';
    document.getElementById('save-playbook-btn').textContent = 'Create Playbook';
    
    // Reset form
    resetPlaybookForm();
    
    document.getElementById('playbook-modal').style.display = 'block';
    switchTab('details');
}

/**
 * Edit existing playbook
 */
async function editPlaybook(playbookId) {
    try {
        const response = await apiRequest(`/admin/api/playbooks/${playbookId}`);
        currentPlaybook = response;
        
        document.getElementById('modal-title').textContent = 'Edit Playbook';
        document.getElementById('save-playbook-btn').textContent = 'Update Playbook';
        
        // Populate form with existing data
        populatePlaybookForm(currentPlaybook);
        
        document.getElementById('playbook-modal').style.display = 'block';
        switchTab('details');
        
    } catch (error) {
        console.error('Error loading playbook:', error);
        showNotification('Failed to load playbook for editing', 'error');
    }
}

/**
 * Save playbook (create or update)
 */
async function savePlaybook() {
    try {
        const formData = collectPlaybookFormData();
        
        // Validate required fields
        if (!formData.name.trim()) {
            showNotification('Playbook name is required', 'error');
            return;
        }
        
        let response;
        if (currentPlaybook) {
            // Update existing playbook
            response = await apiRequest(`/admin/api/playbooks/${currentPlaybook.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
        } else {
            // Create new playbook
            response = await apiRequest('/admin/api/playbooks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
        }
        
        showNotification(response.message, 'success');
        closePlaybookModal();
        loadPlaybooks(); // Refresh the list
        
    } catch (error) {
        console.error('Error saving playbook:', error);
        showNotification('Failed to save playbook', 'error');
    }
}

/**
 * Delete playbook
 */
async function deletePlaybook(playbookId) {
    if (!confirm('Are you sure you want to delete this playbook? This action cannot be undone.')) {
        return;
    }
    
    try {
        await apiRequest(`/admin/api/playbooks/${playbookId}`, {
            method: 'DELETE'
        });
        
        showNotification('Playbook deleted successfully', 'success');
        loadPlaybooks(); // Refresh the list
        
    } catch (error) {
        console.error('Error deleting playbook:', error);
        showNotification('Failed to delete playbook', 'error');
    }
}

/**
 * Show execute playbook modal
 */
async function showExecuteModal(playbookId) {
    try {
        const response = await apiRequest(`/admin/api/playbooks/${playbookId}`);
        currentPlaybook = response;
        
        document.getElementById('exec-playbook-name').textContent = currentPlaybook.name;
        document.getElementById('exec-playbook-description').textContent = 
            currentPlaybook.description || 'No description available';
        
        // Populate variables and targets
        populateExecutionForm(currentPlaybook);
        
        document.getElementById('execute-modal').style.display = 'block';
        
    } catch (error) {
        console.error('Error loading playbook for execution:', error);
        showNotification('Failed to load playbook', 'error');
    }
}

/**
 * Execute playbook
 */
async function executePlaybook() {
    if (!currentPlaybook) return;
    
    try {
        const executionData = {
            variables: collectExecutionVariables(),
            targets: collectExecutionTargets()
        };
        
        closeExecuteModal();
        
        // Show execution results modal
        showExecutionResultsModal();
        
        const response = await apiRequest(`/admin/api/playbooks/${currentPlaybook.id}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(executionData)
        });
        
        // Update execution results
        updateExecutionResults(response.execution);
        
        showNotification('Playbook executed successfully', 'success');
        loadPlaybooks(); // Refresh to update execution counts
        
    } catch (error) {
        console.error('Error executing playbook:', error);
        showNotification('Failed to execute playbook', 'error');
        closeExecutionResultsModal();
    }
}

/**
 * Utility functions
 */

function refreshPlaybooks() {
    loadPlaybooks();
    showNotification('Playbooks refreshed', 'info');
}

function closePlaybookModal() {
    document.getElementById('playbook-modal').style.display = 'none';
    currentPlaybook = null;
}

function closeExecuteModal() {
    document.getElementById('execute-modal').style.display = 'none';
}

function closeExecutionResultsModal() {
    document.getElementById('execution-results-modal').style.display = 'none';
}

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Additional functions for form handling, templates, variables, targets, etc.
// would continue here...

// Export functions for global access
window.showCreatePlaybookModal = showCreatePlaybookModal;
window.editPlaybook = editPlaybook;
window.deletePlaybook = deletePlaybook;
window.showExecuteModal = showExecuteModal;
window.filterPlaybooks = filterPlaybooks;
window.refreshPlaybooks = refreshPlaybooks;
window.switchTab = switchTab;
window.closePlaybookModal = closePlaybookModal;
window.closeExecuteModal = closeExecuteModal;
window.closeExecutionResultsModal = closeExecutionResultsModal;
window.savePlaybook = savePlaybook;
window.executePlaybook = executePlaybook;