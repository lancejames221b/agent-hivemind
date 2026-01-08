/**
 * Confidence System UI Components
 *
 * JavaScript utilities for displaying and interacting with
 * the hAIveMind confidence scoring system in the web interface.
 */

// Confidence level colors and icons
const CONFIDENCE_LEVELS = {
    very_high: {
        color: '#22c55e',  // Green
        icon: '🟢',
        label: 'Very High',
        description: 'Highly reliable - use with confidence'
    },
    high: {
        color: '#84cc16',  // Yellow-green
        icon: '🟡',
        label: 'High',
        description: 'Reliable - likely accurate'
    },
    medium: {
        color: '#f59e0b',  // Orange
        icon: '🟠',
        label: 'Medium',
        description: 'Moderately reliable - verify if critical'
    },
    low: {
        color: '#ef4444',  // Red
        icon: '🔴',
        label: 'Low',
        description: 'Low confidence - verify before use'
    },
    very_low: {
        color: '#6b7280',  // Gray
        icon: '⚫',
        label: 'Very Low',
        description: 'Very low confidence - likely outdated'
    },
    unknown: {
        color: '#9ca3af',  // Light gray
        icon: '❓',
        label: 'Unknown',
        description: 'Confidence not yet calculated'
    }
};

/**
 * Create a confidence badge element
 * @param {number} score - Confidence score (0.0-1.0)
 * @param {string} level - Confidence level (very_high, high, medium, low, very_low)
 * @returns {HTMLElement} - Badge element
 */
function createConfidenceBadge(score, level = null) {
    // Determine level from score if not provided
    if (!level) {
        if (score >= 0.85) level = 'very_high';
        else if (score >= 0.70) level = 'high';
        else if (score >= 0.55) level = 'medium';
        else if (score >= 0.40) level = 'low';
        else level = 'very_low';
    }

    const config = CONFIDENCE_LEVELS[level] || CONFIDENCE_LEVELS.unknown;

    const badge = document.createElement('span');
    badge.className = 'confidence-badge';
    badge.style.cssText = `
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        background-color: ${config.color}15;
        border: 1px solid ${config.color};
        color: ${config.color};
        font-size: 0.75rem;
        font-weight: 600;
        cursor: help;
    `;
    badge.title = config.description;
    badge.innerHTML = `${config.icon} ${config.label} (${(score * 100).toFixed(0)}%)`;

    return badge;
}

/**
 * Create a detailed confidence breakdown card
 * @param {Object} confidence - Full confidence object with factor scores
 * @returns {HTMLElement} - Breakdown card element
 */
function createConfidenceBreakdown(confidence) {
    const card = document.createElement('div');
    card.className = 'confidence-breakdown';
    card.style.cssText = `
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        padding: 1rem;
        background: white;
        margin: 0.5rem 0;
    `;

    // Header
    const header = document.createElement('div');
    header.style.cssText = 'margin-bottom: 1rem;';
    header.innerHTML = `
        <h4 style="margin: 0 0 0.5rem 0; font-size: 0.875rem; font-weight: 600;">
            Confidence Breakdown
        </h4>
        <div style="font-size: 0.75rem; color: #6b7280;">
            ${confidence.description || 'Multi-dimensional reliability scoring'}
        </div>
    `;
    card.appendChild(header);

    // Factor bars
    const factors = {
        'Freshness': confidence.freshness_score || confidence.factors?.freshness || 0.5,
        'Source': confidence.source_score || confidence.factors?.source || 0.5,
        'Verification': confidence.verification_score || confidence.factors?.verification || 0.5,
        'Consensus': confidence.consensus_score || confidence.factors?.consensus || 0.5,
        'No Conflicts': confidence.contradiction_score || confidence.factors?.no_contradictions || 0.5,
        'Success Rate': confidence.success_rate_score || confidence.factors?.success_rate || 0.5,
        'Relevance': confidence.context_relevance_score || confidence.factors?.context_relevance || 0.5
    };

    const factorsContainer = document.createElement('div');
    factorsContainer.style.cssText = 'display: flex; flex-direction: column; gap: 0.75rem;';

    for (const [name, score] of Object.entries(factors)) {
        const factorRow = document.createElement('div');

        const label = document.createElement('div');
        label.style.cssText = 'display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.75rem;';
        label.innerHTML = `
            <span style="color: #374151;">${name}</span>
            <span style="color: #6b7280;">${(score * 100).toFixed(0)}%</span>
        `;

        const barContainer = document.createElement('div');
        barContainer.style.cssText = `
            width: 100%;
            height: 0.5rem;
            background-color: #f3f4f6;
            border-radius: 0.25rem;
            overflow: hidden;
        `;

        const bar = document.createElement('div');
        const color = score >= 0.7 ? '#22c55e' : score >= 0.4 ? '#f59e0b' : '#ef4444';
        bar.style.cssText = `
            width: ${(score * 100)}%;
            height: 100%;
            background-color: ${color};
            transition: width 0.3s ease;
        `;

        barContainer.appendChild(bar);
        factorRow.appendChild(label);
        factorRow.appendChild(barContainer);
        factorsContainer.appendChild(factorRow);
    }

    card.appendChild(factorsContainer);

    return card;
}

/**
 * Add confidence indicator to a memory card/row
 * @param {HTMLElement} element - Memory card/row element
 * @param {Object} confidence - Confidence data
 */
function addConfidenceIndicator(element, confidence) {
    if (!confidence || typeof confidence.score === 'undefined') {
        return; // No confidence data available
    }

    // Create container for confidence badge
    const container = document.createElement('div');
    container.className = 'memory-confidence-indicator';
    container.style.cssText = 'margin-top: 0.5rem;';

    // Add badge
    const badge = createConfidenceBadge(confidence.score, confidence.level);
    container.appendChild(badge);

    // Add expand button for details
    const expandBtn = document.createElement('button');
    expandBtn.textContent = '📊 Details';
    expandBtn.style.cssText = `
        margin-left: 0.5rem;
        padding: 0.25rem 0.5rem;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        background: white;
        color: #374151;
        font-size: 0.75rem;
        cursor: pointer;
    `;
    expandBtn.onclick = () => {
        const existing = container.querySelector('.confidence-breakdown');
        if (existing) {
            existing.remove();
        } else {
            const breakdown = createConfidenceBreakdown(confidence);
            container.appendChild(breakdown);
        }
    };
    container.appendChild(expandBtn);

    // Insert into memory element
    element.appendChild(container);
}

/**
 * Filter memories by minimum confidence
 * @param {Array} memories - Array of memory objects with confidence scores
 * @param {number} minConfidence - Minimum confidence threshold (0.0-1.0)
 * @returns {Array} - Filtered memories
 */
function filterByConfidence(memories, minConfidence) {
    return memories.filter(m => {
        const score = m.confidence?.score || 0.5;
        return score >= minConfidence;
    });
}

/**
 * Sort memories by confidence (descending)
 * @param {Array} memories - Array of memory objects with confidence scores
 * @returns {Array} - Sorted memories
 */
function sortByConfidence(memories) {
    return memories.sort((a, b) => {
        const scoreA = a.confidence?.score || 0.5;
        const scoreB = b.confidence?.score || 0.5;
        return scoreB - scoreA;
    });
}

/**
 * Create confidence filter controls
 * @param {Function} onFilterChange - Callback when filter changes
 * @returns {HTMLElement} - Filter controls element
 */
function createConfidenceFilter(onFilterChange) {
    const container = document.createElement('div');
    container.className = 'confidence-filter';
    container.style.cssText = `
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem;
        background: #f9fafb;
        border-radius: 0.5rem;
        margin: 1rem 0;
    `;

    const label = document.createElement('label');
    label.textContent = 'Min Confidence:';
    label.style.cssText = 'font-size: 0.875rem; color: #374151; font-weight: 500;';

    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = '0';
    slider.max = '100';
    slider.value = '0';
    slider.style.cssText = 'flex: 1; max-width: 200px;';

    const valueLabel = document.createElement('span');
    valueLabel.textContent = '0%';
    valueLabel.style.cssText = 'font-size: 0.875rem; color: #6b7280; min-width: 3rem;';

    slider.oninput = (e) => {
        const value = parseInt(e.target.value);
        valueLabel.textContent = `${value}%`;
        if (onFilterChange) {
            onFilterChange(value / 100);
        }
    };

    container.appendChild(label);
    container.appendChild(slider);
    container.appendChild(valueLabel);

    return container;
}

/**
 * Initialize confidence indicators for all memory cards on page
 */
function initializeConfidenceIndicators() {
    // Find all memory cards with confidence data
    const memoryCards = document.querySelectorAll('.memory-card, .memory-row');

    memoryCards.forEach(card => {
        const confidenceData = card.dataset.confidence;
        if (confidenceData) {
            try {
                const confidence = JSON.parse(confidenceData);
                addConfidenceIndicator(card, confidence);
            } catch (e) {
                console.error('Failed to parse confidence data:', e);
            }
        }
    });
}

// Export functions for use in templates
window.Confidence = {
    createBadge: createConfidenceBadge,
    createBreakdown: createConfidenceBreakdown,
    addIndicator: addConfidenceIndicator,
    filterByConfidence: filterByConfidence,
    sortByConfidence: sortByConfidence,
    createFilter: createConfidenceFilter,
    initialize: initializeConfidenceIndicators,
    LEVELS: CONFIDENCE_LEVELS
};

// Auto-initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeConfidenceIndicators);
} else {
    initializeConfidenceIndicators();
}
