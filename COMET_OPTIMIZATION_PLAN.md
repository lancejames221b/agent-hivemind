# Comet# Page Optimization Plan

## Project: Simplified Comet# Page for AI Browser Integration

### Background
- Working on optimizing the Comet# page in hAIveMind to make it much easier for Perplexity's Comet browser AI to use quickly
- Need bidirectional communication between Comet browser and hAIveMind agents
- Implementing Comet tag system for tracking and instruction

### Research Findings

#### Comet Browser (Perplexity AI)
- **Agentic AI browser** launched 2025 with autonomous task execution
- **Context retention** across sessions, cross-platform operation
- Can operate across Gmail, calendars, social platforms autonomously
- Available to Perplexity Max subscribers, invite-only access
- Built on Chromium framework with native ad-blocking and privacy controls
- Transforms browsing sessions into single, seamless interactions

#### Current hAIveMind Integration
- Existing `comet_integration.py` with directive system already built
- Portal available at `/comet` endpoint serving hAIveMind Comet Portal
- Authentication using environment variable `COMET_AUTH_PASSWORD` with 24-hour sessions
- Directive system supporting priority levels, task delegation, memory search
- Rate limiting: 60 requests/minute with 1024KB max response size

### Implementation Plan

#### 1. Create Simplified `/comet#` Endpoint
- **Quick Access Portal**: Streamlined single-page for AI-first interaction
- **Auto-tagging System**: All interactions tagged with `#comet-ai` for tracking
- **Minimal UI**: Optimized for AI reading vs human interface

#### 2. Bidirectional Communication Pattern
```
COMET → AGENTS:
- Submit directives via simple JSON structure
- Auto-tagged with: {"source": "comet", "session": "uuid", "timestamp": "iso"}
- Priority routing based on urgency tags

AGENTS → COMET:
- Response format: {"comet_tag": "#response", "data": {...}}
- Status updates: Real-time via SSE endpoint
- Memory references: Direct links to hAIveMind entries
```

#### 3. Simplified Interaction Components
- **Quick Actions Bar**: Common tasks as single-click/command
- **Directive Templates**: Pre-built patterns for frequent operations
- **Status Dashboard**: AI-readable system state in structured format
- **Memory Search**: Direct semantic search with Comet context

#### 4. Enhanced API Endpoints
- `/comet#/submit`: Quick directive submission
- `/comet#/status`: AI-optimized status display
- `/comet#/search`: Memory search with Comet context
- `/comet#/agents`: Active agent roster and capabilities
- `/comet#/execute`: Direct task execution endpoint

#### 5. Comet Tag System Implementation
```javascript
// Auto-inject Comet tags
const cometTag = {
  source: "comet-browser",
  version: "1.0",
  session: generateSessionId(),
  capabilities: ["autonomous", "workflow", "memory-access"],
  timestamp: new Date().toISOString()
};

// All submissions include tag
submitData = {...userInput, comet_meta: cometTag};
```

#### 6. Security & Rate Limiting
- Session-based authentication (existing password system)
- Rate limiting: 60 requests/minute
- Output sanitization to prevent prompt injection
- Secure directive validation

### Active Todo List

1. **[IN_PROGRESS]** Create new /comet# route in remote_mcp_server.py
2. **[PENDING]** Build simplified HTML/JS interface optimized for AI
3. **[PENDING]** Add Comet tag injection middleware
4. **[PENDING]** Implement quick action templates
5. **[PENDING]** Add real-time status streaming endpoint
6. **[PENDING]** Create AI-readable documentation inline
7. **[PENDING]** Test with sample autonomous workflow

### Expected Benefits
- **Faster AI Interaction**: Optimized for Comet's agentic capabilities
- **Clear Tracking**: All Comet interactions tagged and traceable
- **Bidirectional Flow**: Easy data exchange between browser and agents
- **Minimal Friction**: Single-page, quick-action focused design
- **Context Aware**: Leverages Comet's context retention features

### Technical Implementation Details

#### File Locations
- Main integration: `/home/lj/haivemind-mcp-server/src/comet_integration.py`
- Server routes: `/home/lj/haivemind-mcp-server/src/remote_mcp_server.py`
- Config: `/home/lj/haivemind-mcp-server/config/config.json` (comet section enabled)

#### Configuration Structure
```json
"comet": {
  "enabled": true,
  "authentication": {
    "password": "${COMET_AUTH_PASSWORD}",
    "session_timeout_hours": 24,
    "auto_logout": true
  },
  "directives": {
    "enabled": true,
    "refresh_interval_seconds": 30,
    "max_active_directives": 10,
    "priority_levels": ["low", "normal", "high", "urgent"]
  },
  "api": {
    "enabled": true,
    "rate_limit_per_minute": 60,
    "max_response_size_kb": 1024
  },
  "ui": {
    "theme": "dark",
    "minimal_mode": true
  }
}
```

#### API Response Format Example
```json
{
  "comet_tag": "#haivemind-response",
  "timestamp": "2025-09-05T14:45:00Z",
  "session_id": "abc123",
  "data": {
    "status": "success",
    "directive_id": "dir_12345",
    "result": {...},
    "next_actions": [...]
  },
  "metadata": {
    "agent_id": "lance-dev-agent",
    "response_time_ms": 150,
    "memory_refs": ["mem_abc", "mem_def"]
  }
}
```

### Status
- **Current Phase**: Planning Complete, Implementation Started
- **Next Milestone**: Complete /comet# endpoint and test with simple AI workflow
- **Timeline**: Targeting completion within 1-2 development sessions
- **Priority**: High - Enables seamless AI-browser integration

---

*Created: 2025-09-05*  
*Author: Lance James, Unit 221B, Inc*  
*Project: hAIveMind Comet Browser Integration*