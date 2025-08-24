---
description: Delegate task to best available hAIveMind agent
argument-hint: task description and requirements
allowed-tools: ["mcp__haivemind__delegate_task", "mcp__haivemind__get_agent_roster"]
---

Delegate this task to the most suitable agent in the collective: **$ARGUMENTS**

Task delegation process:
1. **Analyze Requirements**: Parse task complexity and required capabilities
2. **Find Best Agent**: Match task to agent expertise and availability
3. **Assign Task**: Send task with context and priority
4. **Track Progress**: Monitor task execution and provide updates
5. **Coordinate Response**: Ensure results are shared with relevant agents

The system will automatically:
- Identify agents with matching capabilities
- Consider current workload and availability
- Set appropriate priority and deadline
- Provide task context from collective memory
- Coordinate multi-agent collaboration if needed

Available agent capabilities include:
- Infrastructure management and monitoring
- Database operations and optimization
- Security analysis and incident response
- Development and code review
- Data collection and processing