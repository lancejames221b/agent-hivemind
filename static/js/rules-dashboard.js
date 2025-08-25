/**
 * Rules Dashboard JavaScript
 * Comprehensive CRUD operations for hAIveMind Rules Management
 * 
 * Author: Lance James, Unit 221B Inc
 */

class RulesDashboard {
    constructor() {
        this.rules = [];
        this.templates = [];
        this.conflicts = [];
        this.stats = {};
        this.filters = {};
        this.currentTab = 'overview';
        this.conditionCounter = 0;
        this.actionCounter = 0;
        
        this.init();
    }
    
    async init() {
        console.log('Initializing Rules Dashboard...');
        
        // Load initial data
        await this.loadDashboardData();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Start periodic refresh
        setInterval(() => this.refreshData(), 30000); // Refresh every 30 seconds
    }
    
    async loadDashboardData() {
        try {
            // Load all data in parallel
            const [statsResponse, rulesResponse, templatesResponse, conflictsResponse] = await Promise.all([
                fetch('/api/v1/rules/analytics/dashboard'),
                fetch('/api/v1/rules/'),
                fetch('/api/v1/rules/templates'),
                fetch('/api/v1/rules/conflicts')
            ]);
            
            this.stats = await statsResponse.json();
            this.rules = (await rulesResponse.json()).rules || [];
            this.templates = (await templatesResponse.json()).templates || [];
            
            // Handle conflicts response
            if (conflictsResponse.ok) {
                this.conflicts = await conflictsResponse.json();
            }
            
            // Render all components
            this.renderStats();
            this.renderRules();
            this.renderTemplates();
            this.renderConflicts();
            this.renderRecentActivity();
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showNotification('Error loading dashboard data', 'error');
        }
    }
    
    setupEventListeners() {
        // Filter inputs
        const filterInputs = ['filterRuleType', 'filterScope', 'filterStatus', 'filterTags', 'searchQuery'];
        filterInputs.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.applyFilters());
                element.addEventListener('input', this.debounce(() => this.applyFilters(), 300));
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'n':
                        e.preventDefault();
                        this.showCreateRuleModal();
                        break;
                    case 'i':
                        e.preventDefault();
                        this.showImportModal();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.refreshDashboard();
                        break;
                }
            }
        });
    }
    
    renderStats() {
        const statsGrid = document.getElementById('statsGrid');
        if (!statsGrid || !this.stats.statistics) return;
        
        const stats = this.stats.statistics;
        statsGrid.innerHTML = `
            <div class="stat-card">
                <h3>${stats.total_rules || 0}</h3>
                <p>Total Rules</p>
            </div>
            <div class="stat-card">
                <h3>${stats.by_status?.active || 0}</h3>
                <p>Active Rules</p>
            </div>
            <div class="stat-card">
                <h3>${stats.by_status?.inactive || 0}</h3>
                <p>Inactive Rules</p>
            </div>
            <div class="stat-card">
                <h3>${stats.recent_changes || 0}</h3>
                <p>Recent Changes</p>
            </div>
            <div class="stat-card">
                <h3>${this.conflicts.length || 0}</h3>
                <p>Conflicts</p>
            </div>
            <div class="stat-card">
                <h3>${this.templates.length || 0}</h3>
                <p>Templates</p>
            </div>
        `;
    }
    
    renderRules() {
        const rulesGrid = document.getElementById('rulesGrid');
        if (!rulesGrid) return;
        
        if (this.rules.length === 0) {
            rulesGrid.innerHTML = `
                <div class="empty-state">
                    <h3>No Rules Found</h3>
                    <p>Create your first rule to get started.</p>
                    <button class="btn btn-primary" onclick="dashboard.showCreateRuleModal()">
                        <i class="fas fa-plus"></i> Create Rule
                    </button>
                </div>
            `;
            return;
        }
        
        rulesGrid.innerHTML = this.rules.map(rule => this.renderRuleCard(rule)).join('');
    }
    
    renderRuleCard(rule) {
        const statusClass = `status-${rule.status}`;
        const tags = rule.tags.map(tag => `<span class="tag">${tag}</span>`).join('');
        
        return `
            <div class="rule-card" data-rule-id="${rule.id}">
                <div class="rule-header">
                    <div class="rule-title">
                        <h4>${rule.name}</h4>
                        <span class="rule-status ${statusClass}">${rule.status}</span>
                    </div>
                    <div class="rule-meta">
                        <span><i class="fas fa-tag"></i> ${rule.rule_type}</span>
                        <span><i class="fas fa-globe"></i> ${rule.scope}</span>
                        <span><i class="fas fa-sort-numeric-up"></i> ${rule.priority}</span>
                        <span><i class="fas fa-calendar"></i> ${new Date(rule.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="rule-description">${rule.description}</div>
                    <div class="rule-tags">${tags}</div>
                </div>
                <div class="rule-actions">
                    <div class="rule-actions-left">
                        <button class="btn btn-sm btn-secondary" onclick="dashboard.viewRuleDetails('${rule.id}')">
                            <i class="fas fa-eye"></i> Details
                        </button>
                        <button class="btn btn-sm btn-primary" onclick="dashboard.editRule('${rule.id}')">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-success" onclick="dashboard.cloneRule('${rule.id}')">
                            <i class="fas fa-copy"></i> Clone
                        </button>
                    </div>
                    <div class="rule-actions-right">
                        ${rule.status === 'active' 
                            ? `<button class="btn btn-sm btn-warning" onclick="dashboard.deactivateRule('${rule.id}')">
                                <i class="fas fa-pause"></i> Deactivate
                               </button>`
                            : `<button class="btn btn-sm btn-success" onclick="dashboard.activateRule('${rule.id}')">
                                <i class="fas fa-play"></i> Activate
                               </button>`
                        }
                        <button class="btn btn-sm btn-danger" onclick="dashboard.deleteRule('${rule.id}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderTemplates() {
        const templatesGrid = document.getElementById('templatesGrid');
        if (!templatesGrid) return;
        
        if (this.templates.length === 0) {
            templatesGrid.innerHTML = `
                <div class="empty-state">
                    <h3>No Templates Found</h3>
                    <p>Create your first template to get started.</p>
                    <button class="btn btn-primary" onclick="dashboard.showCreateTemplateModal()">
                        <i class="fas fa-plus"></i> Create Template
                    </button>
                </div>
            `;
            return;
        }
        
        templatesGrid.innerHTML = this.templates.map(template => this.renderTemplateCard(template)).join('');
    }
    
    renderTemplateCard(template) {
        const tags = template.tags.map(tag => `<span class="tag">${tag}</span>`).join('');
        
        return `
            <div class="template-card" onclick="dashboard.useTemplate('${template.id}')">
                <div class="template-header">
                    <h4>${template.name}</h4>
                    <span class="rule-status">${template.rule_type}</span>
                </div>
                <div class="template-body">
                    <div class="template-meta">
                        <span>${template.category}</span>
                        <span>${new Date(template.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="rule-description">${template.description}</div>
                    <div class="rule-tags">${tags}</div>
                </div>
            </div>
        `;
    }
    
    renderConflicts() {
        const conflictsContainer = document.getElementById('conflictsContainer');
        if (!conflictsContainer) return;
        
        if (!this.conflicts || this.conflicts.length === 0) {
            conflictsContainer.innerHTML = `
                <div class="empty-state">
                    <h3>No Conflicts Detected</h3>
                    <p>All rules are compatible with each other.</p>
                </div>
            `;
            return;
        }
        
        conflictsContainer.innerHTML = this.conflicts.map(conflict => this.renderConflictItem(conflict)).join('');
    }
    
    renderConflictItem(conflict) {
        return `
            <div class="conflict-item">
                <div class="conflict-header">
                    <h5>Conflict: ${conflict.type}</h5>
                    <span class="conflict-type">${conflict.severity}</span>
                </div>
                <p>${conflict.description}</p>
                <div class="conflict-rules">
                    <strong>Conflicting Rules:</strong>
                    ${conflict.rule_ids.map(id => `<span class="tag">${id}</span>`).join(' ')}
                </div>
                <div style="margin-top: 1rem;">
                    <button class="btn btn-sm btn-primary" onclick="dashboard.resolveConflict('${conflict.id}')">
                        <i class="fas fa-check"></i> Resolve
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="dashboard.viewConflictDetails('${conflict.id}')">
                        <i class="fas fa-eye"></i> Details
                    </button>
                </div>
            </div>
        `;
    }
    
    renderRecentActivity() {
        const recentActivity = document.getElementById('recentActivity');
        if (!recentActivity || !this.stats.recent_activity) return;
        
        const activities = this.stats.recent_activity.slice(0, 10); // Show last 10 activities
        
        if (activities.length === 0) {
            recentActivity.innerHTML = `
                <div class="empty-state">
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }
        
        recentActivity.innerHTML = activities.map(activity => `
            <div style="padding: 0.5rem 0; border-bottom: 1px solid #eee;">
                <div style="font-weight: 500;">${activity.action}</div>
                <div style="font-size: 0.85rem; color: #666;">
                    ${activity.rule_name} • ${new Date(activity.timestamp).toLocaleString()}
                </div>
            </div>
        `).join('');
    }
    
    // Tab Management
    showTab(tabName) {
        // Update nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
        document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(tabName).classList.add('active');
        
        this.currentTab = tabName;
        
        // Load tab-specific data if needed
        if (tabName === 'analytics') {
            this.loadAnalytics();
        }
    }
    
    // Filter Management
    applyFilters() {
        this.filters = {
            rule_type: document.getElementById('filterRuleType')?.value || '',
            scope: document.getElementById('filterScope')?.value || '',
            status: document.getElementById('filterStatus')?.value || '',
            tags: document.getElementById('filterTags')?.value || '',
            search: document.getElementById('searchQuery')?.value || ''
        };
        
        this.loadRulesWithFilters();
    }
    
    clearFilters() {
        document.getElementById('filterRuleType').value = '';
        document.getElementById('filterScope').value = '';
        document.getElementById('filterStatus').value = '';
        document.getElementById('filterTags').value = '';
        document.getElementById('searchQuery').value = '';
        
        this.filters = {};
        this.loadRulesWithFilters();
    }
    
    async loadRulesWithFilters() {
        try {
            const params = new URLSearchParams();
            Object.entries(this.filters).forEach(([key, value]) => {
                if (value) params.append(key, value);
            });
            
            const response = await fetch(`/api/v1/rules/?${params}`);
            const data = await response.json();
            this.rules = data.rules || [];
            this.renderRules();
            
        } catch (error) {
            console.error('Error loading filtered rules:', error);
            this.showNotification('Error loading rules', 'error');
        }
    }
    
    // Visual Builder
    addCondition() {
        const container = document.getElementById('conditionsContainer');
        const conditionId = `condition-${this.conditionCounter++}`;
        
        // Clear the "no conditions" message
        if (container.querySelector('.text-muted')) {
            container.innerHTML = '';
        }
        
        const conditionHtml = `
            <div class="condition-item" id="${conditionId}">
                <select class="form-control" style="flex: 1;">
                    <option value="project">Project</option>
                    <option value="agent_role">Agent Role</option>
                    <option value="machine_id">Machine ID</option>
                    <option value="task_type">Task Type</option>
                    <option value="user_id">User ID</option>
                </select>
                <select class="form-control" style="flex: 1;">
                    <option value="eq">Equals</option>
                    <option value="ne">Not Equals</option>
                    <option value="in">In</option>
                    <option value="regex">Regex</option>
                    <option value="contains">Contains</option>
                    <option value="startswith">Starts With</option>
                    <option value="endswith">Ends With</option>
                </select>
                <input type="text" class="form-control" placeholder="Value" style="flex: 2;">
                <button class="btn btn-danger btn-sm" onclick="dashboard.removeCondition('${conditionId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', conditionHtml);
    }
    
    removeCondition(conditionId) {
        const element = document.getElementById(conditionId);
        if (element) {
            element.remove();
        }
        
        // Check if no conditions remain
        const container = document.getElementById('conditionsContainer');
        if (container.children.length === 0) {
            container.innerHTML = '<p class="text-muted">No conditions added. Click "Add Condition" to start.</p>';
        }
    }
    
    addAction() {
        const container = document.getElementById('actionsContainer');
        const actionId = `action-${this.actionCounter++}`;
        
        // Clear the "no actions" message
        if (container.querySelector('.text-muted')) {
            container.innerHTML = '';
        }
        
        const actionHtml = `
            <div class="action-item" id="${actionId}">
                <select class="form-control" style="flex: 1;">
                    <option value="set">Set</option>
                    <option value="append">Append</option>
                    <option value="merge">Merge</option>
                    <option value="validate">Validate</option>
                    <option value="block">Block</option>
                </select>
                <input type="text" class="form-control" placeholder="Target" style="flex: 1;">
                <input type="text" class="form-control" placeholder="Value" style="flex: 2;">
                <button class="btn btn-danger btn-sm" onclick="dashboard.removeAction('${actionId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', actionHtml);
    }
    
    removeAction(actionId) {
        const element = document.getElementById(actionId);
        if (element) {
            element.remove();
        }
        
        // Check if no actions remain
        const container = document.getElementById('actionsContainer');
        if (container.children.length === 0) {
            container.innerHTML = '<p class="text-muted">No actions added. Click "Add Action" to start.</p>';
        }
    }
    
    async saveBuiltRule() {
        try {
            const ruleData = this.collectBuilderData();
            
            if (!this.validateBuilderData(ruleData)) {
                return;
            }
            
            const response = await fetch('/api/v1/rules/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ruleData)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showNotification('Rule created successfully!', 'success');
                this.clearBuilder();
                this.loadDashboardData(); // Refresh data
            } else {
                const error = await response.json();
                this.showNotification(`Error creating rule: ${error.detail}`, 'error');
            }
            
        } catch (error) {
            console.error('Error saving rule:', error);
            this.showNotification('Error saving rule', 'error');
        }
    }
    
    collectBuilderData() {
        const conditions = Array.from(document.querySelectorAll('#conditionsContainer .condition-item')).map(item => {
            const selects = item.querySelectorAll('select');
            const input = item.querySelector('input');
            return {
                field: selects[0].value,
                operator: selects[1].value,
                value: input.value,
                case_sensitive: true
            };
        });
        
        const actions = Array.from(document.querySelectorAll('#actionsContainer .action-item')).map(item => {
            const select = item.querySelector('select');
            const inputs = item.querySelectorAll('input');
            return {
                action_type: select.value,
                target: inputs[0].value,
                value: inputs[1].value,
                parameters: {}
            };
        });
        
        const tags = document.getElementById('builderTags').value
            .split(',')
            .map(tag => tag.trim())
            .filter(tag => tag.length > 0);
        
        return {
            name: document.getElementById('builderRuleName').value,
            description: document.getElementById('builderDescription').value,
            rule_type: document.getElementById('builderRuleType').value,
            scope: document.getElementById('builderScope').value,
            priority: parseInt(document.getElementById('builderPriority').value),
            conditions: conditions,
            actions: actions,
            tags: tags
        };
    }
    
    validateBuilderData(data) {
        if (!data.name.trim()) {
            this.showNotification('Rule name is required', 'error');
            return false;
        }
        
        if (!data.description.trim()) {
            this.showNotification('Rule description is required', 'error');
            return false;
        }
        
        if (data.actions.length === 0) {
            this.showNotification('At least one action is required', 'error');
            return false;
        }
        
        return true;
    }
    
    clearBuilder() {
        document.getElementById('builderRuleName').value = '';
        document.getElementById('builderDescription').value = '';
        document.getElementById('builderRuleType').value = 'authorship';
        document.getElementById('builderScope').value = 'global';
        document.getElementById('builderPriority').value = '500';
        document.getElementById('builderTags').value = '';
        
        document.getElementById('conditionsContainer').innerHTML = '<p class="text-muted">No conditions added. Click "Add Condition" to start.</p>';
        document.getElementById('actionsContainer').innerHTML = '<p class="text-muted">No actions added. Click "Add Action" to start.</p>';
        
        this.conditionCounter = 0;
        this.actionCounter = 0;
    }
    
    async validateBuiltRule() {
        const ruleData = this.collectBuilderData();
        
        if (!this.validateBuilderData(ruleData)) {
            return;
        }
        
        try {
            const response = await fetch('/api/v1/rules/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ruleData)
            });
            
            const result = await response.json();
            
            if (result.is_valid) {
                this.showNotification('Rule validation passed!', 'success');
            } else {
                this.showNotification(`Validation failed: ${result.errors.join(', ')}`, 'error');
            }
            
        } catch (error) {
            console.error('Error validating rule:', error);
            this.showNotification('Error validating rule', 'error');
        }
    }
    
    // Rule Operations
    async activateRule(ruleId) {
        try {
            const response = await fetch(`/api/v1/rules/${ruleId}/activate`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.showNotification('Rule activated successfully!', 'success');
                this.loadDashboardData();
            } else {
                const error = await response.json();
                this.showNotification(`Error activating rule: ${error.detail}`, 'error');
            }
            
        } catch (error) {
            console.error('Error activating rule:', error);
            this.showNotification('Error activating rule', 'error');
        }
    }
    
    async deactivateRule(ruleId) {
        try {
            const response = await fetch(`/api/v1/rules/${ruleId}/deactivate`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.showNotification('Rule deactivated successfully!', 'success');
                this.loadDashboardData();
            } else {
                const error = await response.json();
                this.showNotification(`Error deactivating rule: ${error.detail}`, 'error');
            }
            
        } catch (error) {
            console.error('Error deactivating rule:', error);
            this.showNotification('Error deactivating rule', 'error');
        }
    }
    
    async deleteRule(ruleId) {
        if (!confirm('Are you sure you want to delete this rule?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/rules/${ruleId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showNotification('Rule deleted successfully!', 'success');
                this.loadDashboardData();
            } else {
                const error = await response.json();
                this.showNotification(`Error deleting rule: ${error.detail}`, 'error');
            }
            
        } catch (error) {
            console.error('Error deleting rule:', error);
            this.showNotification('Error deleting rule', 'error');
        }
    }
    
    async cloneRule(ruleId) {
        try {
            const response = await fetch(`/api/v1/rules/${ruleId}`);
            const data = await response.json();
            const rule = data.rule;
            
            // Create a copy with modified name
            const clonedRule = {
                ...rule,
                name: `${rule.name} (Copy)`,
                id: undefined // Let the server generate a new ID
            };
            
            const createResponse = await fetch('/api/v1/rules/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(clonedRule)
            });
            
            if (createResponse.ok) {
                this.showNotification('Rule cloned successfully!', 'success');
                this.loadDashboardData();
            } else {
                const error = await createResponse.json();
                this.showNotification(`Error cloning rule: ${error.detail}`, 'error');
            }
            
        } catch (error) {
            console.error('Error cloning rule:', error);
            this.showNotification('Error cloning rule', 'error');
        }
    }
    
    async viewRuleDetails(ruleId) {
        try {
            const response = await fetch(`/api/v1/rules/${ruleId}`);
            const data = await response.json();
            
            // Show detailed view in modal
            this.showRuleDetailsModal(data);
            
        } catch (error) {
            console.error('Error loading rule details:', error);
            this.showNotification('Error loading rule details', 'error');
        }
    }
    
    // Template Operations
    async useTemplate(templateId) {
        try {
            const response = await fetch(`/api/v1/rules/templates/${templateId}`);
            const template = await response.json();
            
            // Show template usage modal
            this.showTemplateUsageModal(template);
            
        } catch (error) {
            console.error('Error loading template:', error);
            this.showNotification('Error loading template', 'error');
        }
    }
    
    // Import/Export Operations
    async importRules() {
        const format = document.getElementById('importFormat').value;
        const content = document.getElementById('importContent').value;
        const overwrite = document.getElementById('importOverwrite').checked;
        
        if (!content.trim()) {
            this.showNotification('Please provide rules content to import', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/v1/rules/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    format: format,
                    content: content,
                    overwrite: overwrite
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showNotification(`Successfully imported ${result.count} rules!`, 'success');
                this.hideModal('importModal');
                this.loadDashboardData();
            } else {
                const error = await response.json();
                this.showNotification(`Error importing rules: ${error.detail}`, 'error');
            }
            
        } catch (error) {
            console.error('Error importing rules:', error);
            this.showNotification('Error importing rules', 'error');
        }
    }
    
    async exportRules() {
        try {
            const response = await fetch('/api/v1/rules/export?format=yaml&include_history=false');
            const data = await response.json();
            
            // Create and download file
            const blob = new Blob([data.data], { type: 'text/yaml' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `rules-export-${new Date().toISOString().split('T')[0]}.yaml`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            this.showNotification('Rules exported successfully!', 'success');
            
        } catch (error) {
            console.error('Error exporting rules:', error);
            this.showNotification('Error exporting rules', 'error');
        }
    }
    
    // Utility Methods
    async refreshDashboard() {
        this.showNotification('Refreshing dashboard...', 'info');
        await this.loadDashboardData();
        this.showNotification('Dashboard refreshed!', 'success');
    }
    
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
        }
    }
    
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
        }
    }
    
    showCreateRuleModal() {
        this.showModal('createRuleModal');
    }
    
    showImportModal() {
        this.showModal('importModal');
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 2rem;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 3000;
            animation: slideIn 0.3s ease;
        `;
        
        // Set background color based on type
        const colors = {
            success: '#28a745',
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }
    
    debounce(func, wait) {
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
}

// Global functions for HTML onclick handlers
window.dashboard = new RulesDashboard();

window.showTab = (tabName) => dashboard.showTab(tabName);
window.refreshDashboard = () => dashboard.refreshDashboard();
window.showCreateRuleModal = () => dashboard.showCreateRuleModal();
window.showImportModal = () => dashboard.showImportModal();
window.exportRules = () => dashboard.exportRules();
window.applyFilters = () => dashboard.applyFilters();
window.clearFilters = () => dashboard.clearFilters();
window.addCondition = () => dashboard.addCondition();
window.addAction = () => dashboard.addAction();
window.saveBuiltRule = () => dashboard.saveBuiltRule();
window.clearBuilder = () => dashboard.clearBuilder();
window.validateBuiltRule = () => dashboard.validateBuiltRule();
window.importRules = () => dashboard.importRules();
window.hideModal = (modalId) => dashboard.hideModal(modalId);

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .notification {
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
`;
document.head.appendChild(style);