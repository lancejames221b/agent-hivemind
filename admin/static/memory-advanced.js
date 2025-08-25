// Advanced Memory Browser JavaScript
// Enhancements for memory management with advanced features

let currentMemories = [];
let selectedMemories = [];

// Advanced search functionality
async function performAdvancedSearch() {
    const searchForm = document.getElementById('advanced-search-form');
    const formData = new FormData(searchForm);
    
    const params = new URLSearchParams();
    params.append('query', formData.get('query') || '');
    if (formData.get('category')) params.append('category', formData.get('category'));
    if (formData.get('machine_id')) params.append('machine_id', formData.get('machine_id'));
    if (formData.get('date_from')) params.append('date_from', formData.get('date_from'));
    if (formData.get('date_to')) params.append('date_to', formData.get('date_to'));
    if (formData.get('tags')) params.append('tags', formData.get('tags'));
    params.append('limit', formData.get('limit') || '50');
    params.append('semantic', formData.get('semantic') === 'on' ? 'true' : 'false');
    
    try {
        const response = await authenticatedFetch(`/admin/api/memory/advanced-search?${params}`);
        if (response.ok) {
            const data = await response.json();
            displayAdvancedSearchResults(data);
            showNotification(`Found ${data.memories.length} memories`, 'success');
        } else {
            showNotification('Advanced search failed', 'error');
        }
    } catch (error) {
        console.error('Advanced search error:', error);
        showNotification('Search error occurred', 'error');
    }
}

// Display advanced search results with enhanced features
function displayAdvancedSearchResults(data) {
    const container = document.getElementById('search-results-container');
    currentMemories = data.memories;
    
    if (currentMemories.length === 0) {
        container.innerHTML = '<div class="empty-state">No memories found matching your criteria</div>';
        return;
    }
    
    container.innerHTML = `
        <div class="results-header">
            <div class="results-stats">
                Found ${data.memories.length} memories
                ${data.filters_applied ? `<small>Filters: ${Object.values(data.filters_applied).filter(f => f).join(', ')}</small>` : ''}
            </div>
            <div class="results-actions">
                <button class="btn btn-small" onclick="selectAllMemories()">Select All</button>
                <button class="btn btn-small" onclick="clearSelection()">Clear Selection</button>
                <button class="btn btn-small btn-primary" onclick="showBulkOperations()" ${selectedMemories.length === 0 ? 'disabled' : ''}>
                    Bulk Actions (${selectedMemories.length})
                </button>
            </div>
        </div>
        <div class="memories-grid">
            ${currentMemories.map(memory => createMemoryCard(memory)).join('')}
        </div>
    `;
}

// Create enhanced memory card with selection and actions
function createMemoryCard(memory) {
    const isSelected = selectedMemories.includes(memory.id);
    return `
        <div class="memory-card ${isSelected ? 'selected' : ''}" data-memory-id="${memory.id}">
            <div class="memory-header">
                <input type="checkbox" class="memory-checkbox" ${isSelected ? 'checked' : ''} 
                       onchange="toggleMemorySelection('${memory.id}')">
                <span class="memory-category">${memory.category || 'global'}</span>
                <span class="memory-date">${formatTime(memory.created_at)}</span>
            </div>
            <div class="memory-content">
                ${memory.content.length > 200 ? memory.content.substring(0, 200) + '...' : memory.content}
            </div>
            ${memory.tags && memory.tags.length > 0 ? `
                <div class="memory-tags">
                    ${memory.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
            ` : ''}
            <div class="memory-actions">
                <button class="btn btn-small" onclick="viewMemoryDetails('${memory.id}')">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn btn-small" onclick="showRelatedMemories('${memory.id}')">
                    <i class="fas fa-link"></i> Related
                </button>
                <button class="btn btn-small" onclick="editMemory('${memory.id}')">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn btn-small btn-danger" onclick="deleteMemory('${memory.id}')">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `;
}

// Memory selection management
function toggleMemorySelection(memoryId) {
    const index = selectedMemories.indexOf(memoryId);
    if (index > -1) {
        selectedMemories.splice(index, 1);
    } else {
        selectedMemories.push(memoryId);
    }
    updateSelectionUI();
}

function selectAllMemories() {
    selectedMemories = currentMemories.map(m => m.id);
    document.querySelectorAll('.memory-checkbox').forEach(cb => cb.checked = true);
    document.querySelectorAll('.memory-card').forEach(card => card.classList.add('selected'));
    updateSelectionUI();
}

function clearSelection() {
    selectedMemories = [];
    document.querySelectorAll('.memory-checkbox').forEach(cb => cb.checked = false);
    document.querySelectorAll('.memory-card').forEach(card => card.classList.remove('selected'));
    updateSelectionUI();
}

function updateSelectionUI() {
    const bulkBtn = document.querySelector('.results-actions button[onclick="showBulkOperations()"]');
    if (bulkBtn) {
        bulkBtn.disabled = selectedMemories.length === 0;
        bulkBtn.textContent = `Bulk Actions (${selectedMemories.length})`;
    }
}

// Bulk operations modal
function showBulkOperations() {
    if (selectedMemories.length === 0) {
        showNotification('Please select memories first', 'warning');
        return;
    }
    
    const modal = createModal('Bulk Operations', `
        <div class="bulk-operations">
            <p>Selected ${selectedMemories.length} memories</p>
            <div class="operation-buttons">
                <button class="btn btn-danger" onclick="performBulkOperation('delete')">
                    <i class="fas fa-trash"></i> Delete Selected
                </button>
                <button class="btn btn-primary" onclick="showBulkCategorize()">
                    <i class="fas fa-folder"></i> Change Category
                </button>
                <button class="btn btn-info" onclick="showBulkTag()">
                    <i class="fas fa-tags"></i> Add Tags
                </button>
                <button class="btn btn-success" onclick="performBulkOperation('export')">
                    <i class="fas fa-download"></i> Export
                </button>
            </div>
        </div>
    `);
}

function showBulkCategorize() {
    const modal = createModal('Change Category', `
        <form id="bulk-categorize-form">
            <div class="form-group">
                <label>New Category:</label>
                <select name="category" required>
                    <option value="global">Global</option>
                    <option value="project">Project</option>
                    <option value="infrastructure">Infrastructure</option>
                    <option value="incidents">Incidents</option>
                    <option value="deployments">Deployments</option>
                    <option value="monitoring">Monitoring</option>
                    <option value="runbooks">Runbooks</option>
                    <option value="security">Security</option>
                </select>
            </div>
            <div class="form-actions">
                <button type="button" onclick="closeModal()" class="btn btn-secondary">Cancel</button>
                <button type="button" onclick="performBulkCategorize()" class="btn btn-primary">Update Category</button>
            </div>
        </form>
    `);
}

function showBulkTag() {
    const modal = createModal('Add Tags', `
        <form id="bulk-tag-form">
            <div class="form-group">
                <label>Tags (comma-separated):</label>
                <input type="text" name="tags" placeholder="tag1, tag2, tag3" required>
                <small>These tags will be added to all selected memories</small>
            </div>
            <div class="form-actions">
                <button type="button" onclick="closeModal()" class="btn btn-secondary">Cancel</button>
                <button type="button" onclick="performBulkTag()" class="btn btn-primary">Add Tags</button>
            </div>
        </form>
    `);
}

// Perform bulk operations
async function performBulkOperation(operation) {
    if (selectedMemories.length === 0) return;
    
    const confirmMessage = operation === 'delete' ? 
        `Are you sure you want to delete ${selectedMemories.length} memories? This cannot be undone.` :
        `Perform ${operation} on ${selectedMemories.length} memories?`;
    
    if (!confirm(confirmMessage)) return;
    
    try {
        const response = await authenticatedFetch('/admin/api/memory/bulk-operations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                operation: operation,
                memory_ids: selectedMemories
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`${operation} completed: ${result.successful} successful, ${result.failed} failed`, 'success');
            closeModal();
            clearSelection();
            performAdvancedSearch(); // Refresh results
        } else {
            showNotification(`Bulk ${operation} failed`, 'error');
        }
    } catch (error) {
        console.error(`Bulk ${operation} error:`, error);
        showNotification(`Error during bulk ${operation}`, 'error');
    }
}

async function performBulkCategorize() {
    const form = document.getElementById('bulk-categorize-form');
    const formData = new FormData(form);
    
    try {
        const response = await authenticatedFetch('/admin/api/memory/bulk-operations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                operation: 'categorize',
                memory_ids: selectedMemories,
                parameters: { category: formData.get('category') }
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`Category updated for ${result.successful} memories`, 'success');
            closeModal();
            clearSelection();
            performAdvancedSearch();
        } else {
            showNotification('Bulk categorization failed', 'error');
        }
    } catch (error) {
        console.error('Bulk categorize error:', error);
        showNotification('Error during categorization', 'error');
    }
}

async function performBulkTag() {
    const form = document.getElementById('bulk-tag-form');
    const formData = new FormData(form);
    const tags = formData.get('tags').split(',').map(t => t.trim()).filter(t => t);
    
    if (tags.length === 0) {
        showNotification('Please enter at least one tag', 'warning');
        return;
    }
    
    try {
        const response = await authenticatedFetch('/admin/api/memory/bulk-operations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                operation: 'tag',
                memory_ids: selectedMemories,
                parameters: { tags: tags }
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(`Tags added to ${result.successful} memories`, 'success');
            closeModal();
            clearSelection();
            performAdvancedSearch();
        } else {
            showNotification('Bulk tagging failed', 'error');
        }
    } catch (error) {
        console.error('Bulk tag error:', error);
        showNotification('Error during tagging', 'error');
    }
}

// Show related memories
async function showRelatedMemories(memoryId) {
    try {
        const response = await authenticatedFetch(`/admin/api/memory/relationships?memory_id=${memoryId}`);
        if (response.ok) {
            const data = await response.json();
            displayRelatedMemories(memoryId, data);
        } else {
            showNotification('Failed to load related memories', 'error');
        }
    } catch (error) {
        console.error('Related memories error:', error);
        showNotification('Error loading relationships', 'error');
    }
}

function displayRelatedMemories(memoryId, data) {
    const content = `
        <div class="related-memories">
            <h4>Related Memories (${data.relationships.length})</h4>
            ${data.relationships.length === 0 ? '<p>No related memories found</p>' : 
                data.relationships.map(rel => `
                    <div class="related-memory">
                        <div class="relationship-strength">
                            <div class="strength-bar">
                                <div class="strength-fill" style="width: ${rel.relationship_strength * 100}%"></div>
                            </div>
                            <span>${(rel.relationship_strength * 100).toFixed(0)}% ${rel.relationship_type}</span>
                        </div>
                        <div class="memory-preview">
                            <strong>${rel.category}</strong><br>
                            ${rel.content_preview}
                        </div>
                        ${rel.shared_tags.length > 0 ? `
                            <div class="shared-tags">
                                Shared tags: ${rel.shared_tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                            </div>
                        ` : ''}
                        <div class="memory-actions">
                            <button class="btn btn-small" onclick="viewMemoryDetails('${rel.memory_id}')">View</button>
                        </div>
                    </div>
                `).join('')
            }
        </div>
    `;
    
    createModal('Related Memories', content);
}

// Memory analytics dashboard
async function showMemoryAnalytics() {
    try {
        const response = await authenticatedFetch('/admin/api/memory/analytics');
        if (response.ok) {
            const analytics = await response.json();
            displayAnalyticsDashboard(analytics);
        } else {
            showNotification('Failed to load analytics', 'error');
        }
    } catch (error) {
        console.error('Analytics error:', error);
        showNotification('Error loading analytics', 'error');
    }
}

function displayAnalyticsDashboard(analytics) {
    const content = `
        <div class="analytics-dashboard">
            <div class="analytics-summary">
                <div class="stat-card">
                    <div class="stat-value">${analytics.total_memories}</div>
                    <div class="stat-label">Total Memories</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${analytics.recent_activity.last_24h}</div>
                    <div class="stat-label">Added Today</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${analytics.quality_metrics.tagged_memories_percentage}%</div>
                    <div class="stat-label">Tagged Memories</div>
                </div>
            </div>
            
            <div class="analytics-charts">
                <div class="chart-section">
                    <h4>Category Distribution</h4>
                    <div class="category-chart">
                        ${Object.entries(analytics.category_distribution).map(([category, data]) => `
                            <div class="category-bar">
                                <span class="category-label">${category}</span>
                                <div class="bar">
                                    <div class="bar-fill" style="width: ${data.percentage}%"></div>
                                </div>
                                <span class="category-count">${data.count}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="chart-section">
                    <h4>Quality Metrics</h4>
                    <div class="quality-metrics">
                        <div class="metric">
                            <span>Average Content Length:</span>
                            <span>${analytics.quality_metrics.avg_content_length} chars</span>
                        </div>
                        <div class="metric">
                            <span>Memories with Context:</span>
                            <span>${analytics.quality_metrics.memories_with_context}%</span>
                        </div>
                        <div class="metric">
                            <span>Duplicate Detection Score:</span>
                            <span>${analytics.quality_metrics.duplicate_detection_score}%</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    createModal('Memory Analytics', content, { size: 'large' });
}

// Duplicate detection
async function runDuplicateDetection() {
    const threshold = prompt('Enter similarity threshold (0.1-1.0, default 0.9):', '0.9');
    if (!threshold) return;
    
    try {
        showNotification('Analyzing memories for duplicates...', 'info');
        
        const response = await authenticatedFetch('/admin/api/memory/deduplicate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                similarity_threshold: parseFloat(threshold)
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            displayDuplicateResults(data);
        } else {
            showNotification('Duplicate detection failed', 'error');
        }
    } catch (error) {
        console.error('Duplicate detection error:', error);
        showNotification('Error during duplicate detection', 'error');
    }
}

function displayDuplicateResults(data) {
    const content = `
        <div class="duplicate-results">
            <div class="duplicate-summary">
                <h4>Duplicate Detection Results</h4>
                <p>Found ${data.duplicates_found} potential duplicates</p>
                <p>Threshold used: ${data.threshold_used}</p>
                <p>Analyzed ${data.analysis_summary.total_memories_analyzed} memories</p>
            </div>
            
            ${data.duplicates.length === 0 ? '<p>No duplicates found!</p>' :
                data.duplicates.map(dup => `
                    <div class="duplicate-pair">
                        <div class="similarity-score">
                            ${(dup.similarity_score * 100).toFixed(1)}% similar
                            <span class="recommended-action">${dup.recommended_action}</span>
                        </div>
                        <div class="duplicate-memories">
                            <div class="memory-preview">
                                <strong>Primary:</strong> ${dup.primary_memory.content}
                                <small>Created: ${formatTime(dup.primary_memory.created_at)}</small>
                            </div>
                            <div class="memory-preview">
                                <strong>Duplicate:</strong> ${dup.duplicate_memory.content}
                                <small>Created: ${formatTime(dup.duplicate_memory.created_at)}</small>
                            </div>
                        </div>
                        <div class="duplicate-actions">
                            <button class="btn btn-small" onclick="viewMemoryDetails('${dup.primary_memory.id}')">View Primary</button>
                            <button class="btn btn-small" onclick="viewMemoryDetails('${dup.duplicate_memory.id}')">View Duplicate</button>
                            ${dup.recommended_action === 'merge' ? 
                                `<button class="btn btn-small btn-primary" onclick="mergeDuplicates('${dup.primary_memory.id}', '${dup.duplicate_memory.id}')">Merge</button>` : 
                                `<button class="btn btn-small btn-warning" onclick="reviewDuplicate('${dup.primary_memory.id}', '${dup.duplicate_memory.id}')">Review</button>`
                            }
                        </div>
                    </div>
                `).join('')
            }
        </div>
    `;
    
    createModal('Duplicate Detection Results', content, { size: 'large' });
}

// Memory recommendations
async function showMemoryRecommendations() {
    try {
        const response = await authenticatedFetch('/admin/api/memory/recommendations');
        if (response.ok) {
            const data = await response.json();
            displayRecommendations(data);
        } else {
            showNotification('Failed to load recommendations', 'error');
        }
    } catch (error) {
        console.error('Recommendations error:', error);
        showNotification('Error loading recommendations', 'error');
    }
}

function displayRecommendations(data) {
    const content = `
        <div class="recommendations">
            <h4>Memory Management Recommendations</h4>
            ${data.recommendations.map(rec => `
                <div class="recommendation ${rec.priority}">
                    <div class="rec-header">
                        <h5>${rec.title}</h5>
                        <span class="priority-badge">${rec.priority}</span>
                    </div>
                    <p>${rec.description}</p>
                    <div class="suggested-actions">
                        <strong>Suggested Actions:</strong>
                        <ul>
                            ${rec.suggested_actions.map(action => `<li>${action}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    createModal('Memory Recommendations', content);
}

// Utility functions
function viewMemoryDetails(memoryId) {
    const memory = currentMemories.find(m => m.id === memoryId);
    if (!memory) {
        showNotification('Memory not found', 'error');
        return;
    }
    
    const content = `
        <div class="memory-details">
            <div class="detail-section">
                <h4>Content</h4>
                <div class="content-display">${memory.content}</div>
            </div>
            
            ${memory.context ? `
                <div class="detail-section">
                    <h4>Context</h4>
                    <div class="context-display">${memory.context}</div>
                </div>
            ` : ''}
            
            <div class="detail-section">
                <h4>Metadata</h4>
                <div class="metadata">
                    <div><strong>ID:</strong> ${memory.id}</div>
                    <div><strong>Category:</strong> ${memory.category || 'global'}</div>
                    <div><strong>Created:</strong> ${formatTime(memory.created_at)}</div>
                    <div><strong>Machine:</strong> ${memory.machine_id || 'unknown'}</div>
                    ${memory.similarity_score ? `<div><strong>Similarity Score:</strong> ${(memory.similarity_score * 100).toFixed(1)}%</div>` : ''}
                </div>
            </div>
            
            ${memory.tags && memory.tags.length > 0 ? `
                <div class="detail-section">
                    <h4>Tags</h4>
                    <div class="tags-display">
                        ${memory.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div class="detail-actions">
                <button class="btn btn-primary" onclick="editMemory('${memory.id}')">Edit Memory</button>
                <button class="btn btn-info" onclick="showRelatedMemories('${memory.id}')">Show Related</button>
                <button class="btn btn-danger" onclick="deleteMemory('${memory.id}')">Delete Memory</button>
            </div>
        </div>
    `;
    
    createModal('Memory Details', content, { size: 'large' });
}

function createModal(title, content, options = {}) {
    // Remove existing modal
    const existing = document.querySelector('.modal-overlay');
    if (existing) existing.remove();
    
    const modal = document.createElement('div');
    modal.className = `modal-overlay ${options.size || ''}`;
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

// Utility function for time formatting
function formatTime(timestamp) {
    if (!timestamp) return 'Unknown';
    try {
        return new Date(timestamp).toLocaleString();
    } catch (e) {
        return 'Invalid date';
    }
}

// Notification system (use existing or create simple fallback)
function showNotification(message, type) {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        console.log(`${type.toUpperCase()}: ${message}`);
        if (type === 'error') alert('Error: ' + message);
    }
}