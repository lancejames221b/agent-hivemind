---
description: Assign tickets to hAIveMind agents with capability matching and workload balancing
allowed-tools: ["mcp__vibe_kanban__*", "mcp__haivemind__delegate_task", "mcp__haivemind__get_agent_roster"]
argument-hint: <ticket_id> [agent_id] [options]
---

# ticket-assign - Intelligent Ticket Assignment

## Purpose
Assign tickets to hAIveMind agents with automatic capability matching, workload balancing, and agent coordination through the collective intelligence network.

## When to Use
- **Task Delegation**: Assign specific tickets to appropriate agents
- **Workload Balancing**: Distribute work across available agents
- **Capability Matching**: Find agents with required skills for tickets
- **Agent Coordination**: Enable cross-agent collaboration on complex work
- **Auto-Assignment**: Let hAIveMind choose the best agent automatically

## Syntax
```
ticket-assign <ticket_id> [agent_id] [options]
```

## Assignment Methods

### Specific Agent Assignment
```
ticket-assign WEBTESTS-1 frontend-specialist
ticket-assign API-DEV-5 backend-agent --priority high
```

### Auto-Assignment by Capabilities
```
ticket-assign WEBTESTS-1 --auto --skills "frontend,ui,testing"
ticket-assign INFRA-3 --auto --capabilities "infrastructure,docker,monitoring"
```

### Best Available Agent
```
ticket-assign API-DEV-5 --best-available
ticket-assign WEBTESTS-2 --best-available --exclude overloaded-agents
```

### Team Assignment
```
ticket-assign COMPLEX-1 --team "frontend-agent,backend-agent" --collaboration
```

## Agent Discovery Features

### Capability Matching
The system automatically:
- Analyzes ticket requirements and complexity
- Matches required skills to agent capabilities  
- Considers agent specializations and experience
- Reviews agent performance on similar tickets

### Workload Balancing  
- Checks current agent workload and capacity
- Considers ticket priorities and deadlines
- Balances work distribution across agents
- Avoids overloading high-performing agents

### Agent Coordination
- Links related tickets for collaboration
- Sets up cross-agent dependencies
- Enables knowledge sharing between agents
- Coordinates handoffs and reviews

## Real-World Examples

### Frontend Work Assignment
```
ticket-assign WEBTESTS-1 --auto --skills "react,css,testing" --description "Login form needs responsive design and validation"
```
**Automatic Matching:**
- Finds agents with React and CSS expertise
- Prioritizes agents with testing experience
- Considers UI/UX specialization
- Balances current frontend workload

### Infrastructure Task Delegation
```
ticket-assign INFRA-3 --delegate --requirements "docker,kubernetes,monitoring" --priority critical
```
**hAIveMind Delegation:**
- Searches collective for infrastructure specialists
- Finds agents with Docker/K8s experience
- Considers monitoring setup expertise
- Prioritizes based on critical urgency

### Complex Multi-Agent Work
```
ticket-assign COMPLEX-1 --team "data-engineer,ml-specialist,frontend-agent" --coordination "sequential" --handoff-protocol
```
**Team Coordination:**
- Assigns to multiple specialized agents
- Sets up sequential workflow coordination
- Establishes handoff protocols
- Links agents for knowledge sharing

## Assignment Options
- **--auto**: Automatic agent selection based on capabilities
- **--best-available**: Choose best available agent right now
- **--skills "list"**: Required skills for the work
- **--capabilities "list"**: Required agent capabilities
- **--exclude "agents"**: Exclude specific agents from selection
- **--priority**: Assignment priority (affects agent selection)
- **--deadline**: Work deadline (influences agent availability)
- **--team "list"**: Multi-agent team assignment
- **--collaboration**: Enable cross-agent collaboration features
- **--delegate**: Use hAIveMind task delegation system

## Expected Output

### Successful Assignment
```
🎯 Assigning Ticket: WEBTESTS-1
🔍 Analyzing ticket requirements...

📊 Ticket Analysis:
   • Skills required: frontend, ui, testing, validation
   • Complexity: medium
   • Estimated effort: 4-6 hours
   • Priority: high

🤖 Agent Selection Process:
   • Scanning hAIveMind collective for suitable agents...
   • Found 4 agents with matching capabilities
   • Evaluating workload and availability...
   • Considering past performance on similar tickets...

✅ Assignment Complete:
   • Assigned to: frontend-specialist
   • Agent capabilities: frontend, ui, testing, react, css
   • Current workload: 2/5 tickets (40% capacity)
   • Estimated start: Today 14:30
   • Estimated completion: Tomorrow 16:00

🧠 hAIveMind Integration:
   • Agent notified via collective network
   • Ticket context shared with agent memory
   • Related knowledge and lessons learned provided
   • Collaboration links established

📋 Next Steps:
   • Agent will receive ticket context automatically
   • Pre-work hooks will trigger when agent starts
   • Progress updates will sync across collective
```

### Auto-Assignment with Options
```
🎯 Auto-Assigning Complex Task: INFRA-MIGRATION-1
🔍 Analyzing requirements: infrastructure, migration, database, security

🤖 Collective Intelligence Search:
   • infrastructure-specialist: 85% match, 60% available
   • devops-agent: 92% match, 80% available  
   • database-expert: 78% match, 90% available

✅ Best Match Selected: devops-agent
   • Capability score: 92%
   • Availability: 80% (3/5 ticket capacity)
   • Similar work experience: 8 successful migrations
   • Collaboration rating: excellent

🔗 Team Coordination Setup:
   • Primary: devops-agent (migration lead)
   • Consultant: database-expert (schema review)
   • Coordinator: infrastructure-specialist (deployment)
```

## Agent Capability Categories
The system recognizes these capability types:
- **Development**: frontend, backend, fullstack, mobile, api
- **Infrastructure**: docker, kubernetes, aws, gcp, monitoring
- **Data**: database, elasticsearch, analytics, etl, ml
- **Security**: authentication, encryption, compliance, audit
- **Testing**: unit, integration, e2e, performance, security
- **Operations**: deployment, monitoring, incident, backup

## Integration with hAIveMind

### Agent Registry
- Uses live agent roster from hAIveMind collective
- Considers real-time agent status and availability
- Reviews agent performance metrics and specializations

### Task Delegation System
- Integrates with hAIveMind task delegation infrastructure
- Enables cross-machine agent coordination
- Supports complex multi-agent workflows

### Knowledge Sharing
- Provides assigned agents with relevant context
- Links related memories and lessons learned
- Enables collaboration and knowledge transfer

## Workload Management
- Prevents agent overload with capacity tracking
- Balances work distribution across the collective  
- Considers agent preferences and specializations
- Supports flexible reassignment when needed

Make intelligent assignments that leverage the full power of hAIveMind collective intelligence!