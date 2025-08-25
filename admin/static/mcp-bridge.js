// MCP Bridge JavaScript
// Comprehensive bridge management functionality

// Global state
let currentBridges = [];
let discoveredServers = [];

// Utility functions
function formatBridgeEndpoint(serverId) {
    return `/mcp-bridge/${serverId}`;
}

function getBridgeStatusColor(status) {
    switch (status) {
        case 'running': return '#28a745';
        case 'stopped': return '#6c757d';
        case 'error': return '#dc3545';
        case 'starting': return '#ffc107';
        default: return '#6c757d';
    }
}

function getBridgeTypeIcon(type) {
    switch (type) {
        case 'stdio': return '⌨️';
        case 'http': return '🌐';
        case 'sse': return '📡';
        default: return '🔧';
    }
}

// Bridge discovery and management
async function discoverAllMCPSources() {
    try {
        showToast('Comprehensive MCP discovery starting...', 'info');
        
        // First discover from config files
        const configResponse = await authenticatedFetch('/admin/api/mcp-bridge/discover');
        const configData = configResponse.ok ? await configResponse.json() : { servers: [] };
        
        // Check for running services
        const runningServers = await detectRunningMCPServers();
        
        // Combine discoveries
        const allDiscovered = [
            ...configData.servers,
            ...runningServers
        ];
        
        // Remove duplicates
        const uniqueServers = allDiscovered.reduce((unique, server) => {
            const exists = unique.find(s => s.name === server.name);
            if (!exists) unique.push(server);
            return unique;
        }, []);
        
        discoveredServers = uniqueServers;
        displayDiscoveredServers(uniqueServers);
        document.getElementById('discovered-servers').textContent = uniqueServers.length;
        
        showToast(`Discovered ${uniqueServers.length} MCP servers`, 'success');
        
    } catch (error) {
        console.error('Comprehensive discovery error:', error);
        showToast('Error during MCP discovery', 'error');
    }
}

async function detectRunningMCPServers() {
    // This would detect running MCP servers on common ports
    const commonPorts = [8900, 8901, 8902, 3000, 3001, 5000, 5001];
    const runningServers = [];
    
    for (const port of commonPorts) {
        try {
            // Try to detect MCP server on this port
            const response = await fetch(`http://localhost:${port}/mcp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: 'discover',
                    method: 'initialize',
                    params: { capabilities: {} }
                })
            });
            
            if (response.ok) {
                runningServers.push({
                    name: `MCP Server (Port ${port})`,
                    type: 'http',
                    local_host: 'localhost',
                    local_port: port,
                    config_file: 'detected_running',
                    command: null,
                    args: []
                });
            }
        } catch (error) {
            // Server not running on this port, continue
        }
    }
    
    return runningServers;
}

// Enhanced bridge registration
async function registerBridgeWithValidation(config) {
    try {
        // Pre-registration validation
        if (config.type === 'http' && config.local_port) {
            const isReachable = await testServerReachability(config.local_host, config.local_port);
            if (!isReachable) {
                throw new Error(`Server not reachable at ${config.local_host}:${config.local_port}`);
            }
        }
        
        // Register the bridge
        const response = await authenticatedFetch('/admin/api/mcp-bridge/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Post-registration testing
            setTimeout(async () => {
                await performPostRegistrationTests(result.server_id);
            }, 2000);
            
            return result;
        } else {
            throw new Error(`Registration failed: ${response.status}`);
        }
        
    } catch (error) {
        console.error('Bridge registration error:', error);
        throw error;
    }
}

async function testServerReachability(host, port) {
    try {
        const response = await fetch(`http://${host}:${port}/health`, {
            method: 'GET',
            timeout: 5000
        });
        return response.ok;
    } catch (error) {
        return false;
    }
}

async function performPostRegistrationTests(serverId) {
    try {
        // Test basic connectivity
        const statusResponse = await authenticatedFetch(`/admin/api/mcp-bridge/${serverId}/status`);
        if (!statusResponse.ok) {
            showToast(`Bridge ${serverId}: Status check failed`, 'warning');
            return;
        }
        
        // Test MCP protocol
        const testResponse = await authenticatedFetch(`/admin/api/mcp-bridge/${serverId}/proxy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                method: 'tools/list',
                params: {}
            })
        });
        
        if (testResponse.ok) {
            const result = await testResponse.json();
            showToast(`Bridge ${serverId}: Protocol test passed (${result.tools ? result.tools.length : 0} tools)`, 'success');
        } else {
            showToast(`Bridge ${serverId}: Protocol test failed`, 'warning');
        }
        
    } catch (error) {
        console.error('Post-registration test error:', error);
        showToast(`Bridge ${serverId}: Post-registration tests failed`, 'warning');
    }
}

// Advanced bridge operations
async function performBridgeHealthCheck(serverId) {
    try {
        const checks = [
            { name: 'Status Check', test: () => authenticatedFetch(`/admin/api/mcp-bridge/${serverId}/status`) },
            { name: 'Tools List', test: () => testBridgeMethod(serverId, 'tools/list', {}) },
            { name: 'Resources List', test: () => testBridgeMethod(serverId, 'resources/list', {}) },
        ];
        
        const results = [];
        for (const check of checks) {
            try {
                const response = await check.test();
                results.push({
                    name: check.name,
                    status: response.ok ? 'pass' : 'fail',
                    details: response.ok ? 'OK' : `Status ${response.status}`
                });
            } catch (error) {
                results.push({
                    name: check.name,
                    status: 'error',
                    details: error.message
                });
            }
        }
        
        displayHealthCheckResults(serverId, results);
        
    } catch (error) {
        console.error('Health check error:', error);
        showToast('Error performing health check', 'error');
    }
}

async function testBridgeMethod(serverId, method, params) {
    return await authenticatedFetch(`/admin/api/mcp-bridge/${serverId}/proxy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method, params })
    });
}

function displayHealthCheckResults(serverId, results) {
    const modal = createModal('Bridge Health Check Results', `
        <div class="health-check-results">
            <h4>Bridge: ${serverId}</h4>
            <div class="check-results" style="margin-top: 20px;">
                ${results.map(result => `
                    <div class="check-result" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; margin-bottom: 10px; border-radius: 4px; background: ${getCheckStatusColor(result.status)};">
                        <span><strong>${result.name}</strong></span>
                        <span style="display: flex; align-items: center; gap: 10px;">
                            <span class="check-status">${result.status.toUpperCase()}</span>
                            <span class="check-details" style="font-size: 12px;">${result.details}</span>
                        </span>
                    </div>
                `).join('')}
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <button class="btn btn-primary" onclick="closeModal(); performBridgeHealthCheck('${serverId}')">Re-run Checks</button>
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>
        </div>
    `);
}

function getCheckStatusColor(status) {
    switch (status) {
        case 'pass': return '#d4edda';
        case 'fail': return '#f8d7da';
        case 'error': return '#fff3cd';
        default: return '#e2e3e5';
    }
}

// Bridge monitoring and analytics
class BridgeMonitor {
    constructor() {
        this.metrics = {
            requests: {},
            errors: {},
            latency: {},
            uptime: {}
        };
        this.startTime = Date.now();
    }
    
    recordRequest(serverId, success, latency) {
        if (!this.metrics.requests[serverId]) {
            this.metrics.requests[serverId] = 0;
            this.metrics.errors[serverId] = 0;
            this.metrics.latency[serverId] = [];
        }
        
        this.metrics.requests[serverId]++;
        if (!success) this.metrics.errors[serverId]++;
        if (latency) this.metrics.latency[serverId].push(latency);
    }
    
    getMetrics(serverId) {
        const requests = this.metrics.requests[serverId] || 0;
        const errors = this.metrics.errors[serverId] || 0;
        const latencies = this.metrics.latency[serverId] || [];
        
        return {
            total_requests: requests,
            error_rate: requests > 0 ? (errors / requests * 100).toFixed(2) + '%' : '0%',
            success_rate: requests > 0 ? ((requests - errors) / requests * 100).toFixed(2) + '%' : '0%',
            avg_latency: latencies.length > 0 ? (latencies.reduce((a, b) => a + b, 0) / latencies.length).toFixed(2) + 'ms' : 'N/A',
            uptime: this.calculateUptime()
        };
    }
    
    calculateUptime() {
        const uptimeMs = Date.now() - this.startTime;
        const hours = Math.floor(uptimeMs / (1000 * 60 * 60));
        const minutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60));
        return `${hours}h ${minutes}m`;
    }
}

// Global bridge monitor instance
const bridgeMonitor = new BridgeMonitor();

// Enhanced bridge testing
async function performComprehensiveBridgeTest(serverId) {
    const tests = [
        { name: 'Connection Test', method: 'initialize', params: { capabilities: {} } },
        { name: 'Tools Discovery', method: 'tools/list', params: {} },
        { name: 'Resources Discovery', method: 'resources/list', params: {} },
        { name: 'Prompts Discovery', method: 'prompts/list', params: {} }
    ];
    
    const results = [];
    let totalLatency = 0;
    
    showToast('Running comprehensive bridge test...', 'info');
    
    for (const test of tests) {
        const startTime = Date.now();
        try {
            const response = await testBridgeMethod(serverId, test.method, test.params);
            const latency = Date.now() - startTime;
            totalLatency += latency;
            
            if (response.ok) {
                const data = await response.json();
                results.push({
                    name: test.name,
                    status: 'pass',
                    latency: latency,
                    details: `Response received (${latency}ms)`,
                    data: data
                });
                bridgeMonitor.recordRequest(serverId, true, latency);
            } else {
                results.push({
                    name: test.name,
                    status: 'fail',
                    latency: latency,
                    details: `HTTP ${response.status}`,
                    data: null
                });
                bridgeMonitor.recordRequest(serverId, false, latency);
            }
        } catch (error) {
            const latency = Date.now() - startTime;
            results.push({
                name: test.name,
                status: 'error',
                latency: latency,
                details: error.message,
                data: null
            });
            bridgeMonitor.recordRequest(serverId, false, latency);
        }
    }
    
    displayComprehensiveTestResults(serverId, results, totalLatency);
}

function displayComprehensiveTestResults(serverId, results, totalLatency) {
    const passedTests = results.filter(r => r.status === 'pass').length;
    const totalTests = results.length;
    const metrics = bridgeMonitor.getMetrics(serverId);
    
    const modal = createModal('Comprehensive Bridge Test Results', `
        <div class="comprehensive-test-results">
            <div class="test-summary" style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                <h4>Test Summary for ${serverId}</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 15px;">
                    <div class="metric">
                        <strong>Tests Passed:</strong><br>${passedTests}/${totalTests}
                    </div>
                    <div class="metric">
                        <strong>Success Rate:</strong><br>${((passedTests/totalTests)*100).toFixed(1)}%
                    </div>
                    <div class="metric">
                        <strong>Total Latency:</strong><br>${totalLatency}ms
                    </div>
                    <div class="metric">
                        <strong>Avg Latency:</strong><br>${(totalLatency/totalTests).toFixed(1)}ms
                    </div>
                </div>
            </div>
            
            <div class="test-details">
                <h5>Test Details:</h5>
                ${results.map(result => `
                    <div class="test-result" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; margin-bottom: 10px; border-radius: 4px; background: ${getCheckStatusColor(result.status)};">
                        <div>
                            <strong>${result.name}</strong><br>
                            <small>${result.details}</small>
                        </div>
                        <div style="text-align: right;">
                            <span class="status-badge">${result.status.toUpperCase()}</span><br>
                            <small>${result.latency}ms</small>
                        </div>
                    </div>
                `).join('')}
            </div>
            
            <div class="bridge-metrics" style="background: #e3f2fd; padding: 15px; border-radius: 6px; margin-top: 20px;">
                <h5>Bridge Metrics:</h5>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;">
                    <div><strong>Total Requests:</strong><br>${metrics.total_requests}</div>
                    <div><strong>Success Rate:</strong><br>${metrics.success_rate}</div>
                    <div><strong>Error Rate:</strong><br>${metrics.error_rate}</div>
                    <div><strong>Avg Latency:</strong><br>${metrics.avg_latency}</div>
                    <div><strong>Uptime:</strong><br>${metrics.uptime}</div>
                </div>
            </div>
        </div>
    `);
}

// Bridge configuration import/export
async function exportBridgeConfig(serverId) {
    try {
        const response = await authenticatedFetch(`/admin/api/mcp-bridge/${serverId}/status`);
        if (response.ok) {
            const status = await response.json();
            const config = {
                name: status.status.name,
                type: status.status.bridge_type,
                config: status.status.config,
                export_date: new Date().toISOString(),
                version: '1.0'
            };
            
            const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bridge-config-${serverId}.json`;
            a.click();
            URL.revokeObjectURL(url);
            
            showToast('Bridge configuration exported', 'success');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast('Error exporting bridge configuration', 'error');
    }
}

function showImportBridgeConfigModal() {
    const modal = createModal('Import Bridge Configuration', `
        <div class="import-config">
            <div class="form-group">
                <label>Upload Configuration File:</label>
                <input type="file" id="config-file-input" accept=".json" onchange="handleConfigFileUpload(event)">
                <small>Select a bridge configuration JSON file to import</small>
            </div>
            <div class="form-group" style="margin-top: 20px;">
                <label>Or Paste Configuration:</label>
                <textarea id="config-text-input" rows="10" placeholder="Paste bridge configuration JSON here..."></textarea>
            </div>
            <div class="form-actions">
                <button type="button" onclick="closeModal()" class="btn btn-secondary">Cancel</button>
                <button type="button" onclick="importBridgeConfig()" class="btn btn-primary">Import Bridge</button>
            </div>
        </div>
    `);
}

function handleConfigFileUpload(event) {
    const file = event.target.files[0];
    if (file && file.type === 'application/json') {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('config-text-input').value = e.target.result;
        };
        reader.readAsText(file);
    }
}

async function importBridgeConfig() {
    try {
        const configText = document.getElementById('config-text-input').value;
        if (!configText.trim()) {
            showToast('Please provide configuration JSON', 'warning');
            return;
        }
        
        const config = JSON.parse(configText);
        
        // Validate configuration
        if (!config.name || !config.type) {
            throw new Error('Invalid configuration: name and type are required');
        }
        
        // Register the imported bridge
        const result = await registerBridgeWithValidation(config);
        
        showToast(`Bridge "${config.name}" imported successfully`, 'success');
        closeModal();
        loadBridges();
        
    } catch (error) {
        console.error('Import error:', error);
        showToast(`Error importing configuration: ${error.message}`, 'error');
    }
}

// Bridge batch operations
async function performBatchBridgeOperation(operation, selectedBridges) {
    if (selectedBridges.length === 0) {
        showToast('No bridges selected', 'warning');
        return;
    }
    
    const results = [];
    showToast(`Performing ${operation} on ${selectedBridges.length} bridges...`, 'info');
    
    for (const serverId of selectedBridges) {
        try {
            let response;
            switch (operation) {
                case 'health-check':
                    await performBridgeHealthCheck(serverId);
                    results.push({ serverId, status: 'success', message: 'Health check completed' });
                    break;
                case 'test':
                    await performComprehensiveBridgeTest(serverId);
                    results.push({ serverId, status: 'success', message: 'Test completed' });
                    break;
                case 'restart':
                    // Implementation would depend on bridge restart capability
                    results.push({ serverId, status: 'info', message: 'Restart not yet implemented' });
                    break;
                default:
                    results.push({ serverId, status: 'error', message: 'Unknown operation' });
            }
        } catch (error) {
            results.push({ serverId, status: 'error', message: error.message });
        }
    }
    
    displayBatchOperationResults(operation, results);
}

function displayBatchOperationResults(operation, results) {
    const successCount = results.filter(r => r.status === 'success').length;
    const errorCount = results.filter(r => r.status === 'error').length;
    
    const modal = createModal(`Batch ${operation} Results`, `
        <div class="batch-results">
            <div class="results-summary" style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                <h4>Operation Summary</h4>
                <div style="display: flex; gap: 30px; margin-top: 10px;">
                    <div>✅ <strong>Success:</strong> ${successCount}</div>
                    <div>❌ <strong>Errors:</strong> ${errorCount}</div>
                    <div>📊 <strong>Total:</strong> ${results.length}</div>
                </div>
            </div>
            
            <div class="results-details">
                <h5>Detailed Results:</h5>
                ${results.map(result => `
                    <div class="result-item" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; margin-bottom: 5px; border-radius: 4px; background: ${result.status === 'success' ? '#d4edda' : result.status === 'error' ? '#f8d7da' : '#e2e3e5'};">
                        <span><strong>${result.serverId}</strong></span>
                        <span>${result.message}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `);
}

// Initialize bridge management
document.addEventListener('DOMContentLoaded', function() {
    // Set up periodic bridge status refresh
    setInterval(() => {
        if (currentBridges.length > 0) {
            loadBridges();
        }
    }, 30000); // Refresh every 30 seconds
    
    // Set up keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'r':
                    e.preventDefault();
                    refreshBridges();
                    break;
                case 'd':
                    e.preventDefault();
                    discoverAllMCPSources();
                    break;
            }
        }
    });
});

// Export functions for global access
window.bridgeMonitor = bridgeMonitor;
window.discoverAllMCPSources = discoverAllMCPSources;
window.registerBridgeWithValidation = registerBridgeWithValidation;
window.performComprehensiveBridgeTest = performComprehensiveBridgeTest;
window.performBridgeHealthCheck = performBridgeHealthCheck;
window.exportBridgeConfig = exportBridgeConfig;
window.showImportBridgeConfigModal = showImportBridgeConfigModal;
window.performBatchBridgeOperation = performBatchBridgeOperation;