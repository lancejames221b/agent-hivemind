# Enhanced Ticket Search Command

## Description
Search tickets using hAIveMind semantic search and text matching with relevance scoring.

## Usage
```bash
# Basic keyword search
search_tickets project_id="<project_id>" query="authentication"

# Search with result limit
search_tickets project_id="<project_id>" query="database error" limit=5

# Search for specific ticket number
search_tickets project_id="<project_id>" query="#1001"

# Complex multi-word search
search_tickets project_id="<project_id>" query="user login validation bug" limit=10
```

## Parameters
- **project_id**: Project ID from Vibe Kanban (required)
- **query**: Search query - supports keywords, phrases, ticket numbers (required)
- **limit**: Maximum results to return (default: 10, max: 50)

## Search Features
- ✅ **Semantic Search**: Uses hAIveMind memory for intelligent matching
- ✅ **Text Matching**: Searches titles, descriptions, and metadata
- ✅ **Relevance Scoring**: Results ranked by relevance (0.0-1.0)
- ✅ **Ticket Number Search**: Find tickets by #number
- ✅ **Keyword Matching**: Matches partial words and phrases
- ✅ **Memory Integration**: Searches related work history
- ✅ **Cross-Reference**: Finds related tickets and dependencies

## Output Format
```
🔍 Found 3 tickets matching 'authentication bug'

#1001 - Fix critical authentication bypass (Relevance: 0.95)
  Status: in_progress | Priority: critical
  ID: task_abc123

#1015 - Update authentication middleware (Relevance: 0.87)
  Status: review | Priority: high  
  ID: task_def456

#1023 - Authentication error handling (Relevance: 0.72)
  Status: done | Priority: medium
  ID: task_ghi789
```

## Search Query Examples

### Find security issues
```bash
search_tickets project_id="proj_123" query="security vulnerability auth"
```

### Look for performance problems
```bash
search_tickets project_id="proj_123" query="slow performance timeout"
```

### Find database-related work
```bash
search_tickets project_id="proj_123" query="database connection pool migration"
```

### Search for API issues
```bash
search_tickets project_id="proj_123" query="API endpoint 500 error"
```

### Find specific ticket by number
```bash
search_tickets project_id="proj_123" query="#1001"
```

### UI/UX related tickets
```bash
search_tickets project_id="proj_123" query="user interface design mobile"
```

### Integration problems
```bash
search_tickets project_id="proj_123" query="third party integration webhook"
```

## Search Tips
- **Use specific keywords**: "database timeout" instead of just "slow"
- **Include ticket numbers**: Search "#1001" to find specific tickets
- **Use multiple keywords**: "user login validation" for better matching
- **Try variations**: "auth", "authentication", "login" for broader results
- **Check relevance scores**: Higher scores (>0.8) are most relevant

## How Search Works
1. **Memory Search**: Queries hAIveMind for semantically related tickets
2. **Text Matching**: Searches ticket titles and descriptions
3. **Relevance Ranking**: Combines semantic similarity and text matches
4. **Result Merging**: Deduplicates and sorts by relevance
5. **Context Enhancement**: Adds related memories and work history

The search leverages hAIveMind's collective intelligence to find not just exact matches, but semantically related tickets and relevant work history.