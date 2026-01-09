# hAIveMind Token Optimization Strategy

## Problem
The original CLAUDE.md was 612 lines (~3000 words), consuming significant context window tokens every session.

## Solution: Tiered Documentation Architecture

### Tier 1: Minimal Context (Default)
**File**: `CLAUDE.minimal.md` (57 lines, ~230 words)
- **90% reduction** from original
- Core concepts only
- Tool names listed (not full descriptions)
- Essential ports/configs
- Links to detailed docs

**When to use**: Normal sessions, quick tasks, familiar users

### Tier 2: Standard Context
**File**: `CLAUDE.md` (current full version)
- Complete tool descriptions
- All examples inline
- Full troubleshooting section

**When to use**: New users, complex multi-system tasks, reference

### Tier 3: On-Demand Detailed Docs
**Files**:
- `examples/command-sequences/hv-examples-full.md` - All usage examples
- `examples/command-sequences/quick-reference.md` - Workflow patterns
- `examples/cheatsheet.txt` - Ultra-compact reference

**Load via**:
- `/help <topic>` - Load specific command docs
- `/examples <context>` - Load contextual examples
- `Read examples/cheatsheet.txt` - Quick reference

## Implementation Strategies

### 1. Use Minimal CLAUDE.md
Replace `CLAUDE.md` with `CLAUDE.minimal.md` for most sessions:
```bash
cp CLAUDE.minimal.md CLAUDE.md.bak
cp CLAUDE.md CLAUDE.full.md
cp CLAUDE.minimal.md CLAUDE.md
```

### 2. Lazy-Load Pattern
Instead of loading all docs upfront, use slash commands:
```
/help memory       # Loads only memory tool docs
/examples incident # Loads only incident examples
```

### 3. MCP Tool Discovery
Claude can discover MCP tool parameters at runtime - no need to document every parameter:
- Tool names are enough
- Claude queries MCP for schemas
- Reduces documentation overhead

### 4. Compact Notation
Use abbreviated formats:
- `store_memory | retrieve_memory` vs full descriptions
- Category lists vs paragraphs
- Tables vs prose

### 5. Reference by ID
Instead of repeating context, store and reference:
```
remember "context" project → returns memory_id
"See memory abc123 for full context"
```

## Token Savings Breakdown

| Component | Original | Optimized | Savings |
|-----------|----------|-----------|---------|
| CLAUDE.md | ~3000 tokens | ~350 tokens | 88% |
| Examples inline | ~2000 tokens | 0 (on-demand) | 100% |
| Tool descriptions | ~800 tokens | ~150 tokens | 81% |
| **Total** | ~5800 tokens | ~500 tokens | **91%** |

## Best Practices for AI Communication

### DO:
- Use tool names only (Claude knows schemas)
- Keep categories/enums in compact lists
- Reference external docs via paths
- Use tables for structured data
- Load details only when needed

### DON'T:
- Include full parameter descriptions
- Embed all examples in CLAUDE.md
- Duplicate info across files
- Use verbose prose for structured data
- Load full docs every session

## Recommended Workflow

1. **Session Start**: Minimal CLAUDE.md loads automatically
2. **Need Help?**: `/help <topic>` loads specific docs
3. **Need Examples?**: `/examples <context>` loads relevant patterns
4. **Quick Reference?**: Load `cheatsheet.txt` inline
5. **Deep Dive?**: Load `hv-examples-full.md` for complete reference

## Files Created

```
CLAUDE.minimal.md              # Compact context (use as default)
CLAUDE.md                      # Full context (keep for reference)
examples/cheatsheet.txt        # Ultra-compact quick reference
examples/command-sequences/
  hv-examples-full.md          # All examples extracted
  quick-reference.md           # Workflow patterns
docs/TOKEN_OPTIMIZATION_STRATEGY.md  # This file
```

## Migration Steps

To adopt minimal context:

1. Backup current: `mv CLAUDE.md CLAUDE.full.md`
2. Use minimal: `mv CLAUDE.minimal.md CLAUDE.md`
3. Update slash commands to load details on demand
4. Test with typical workflows
5. Adjust minimal version based on common needs

## Future Optimizations

1. **Dynamic CLAUDE.md**: Generate based on project type
2. **Context Caching**: Store loaded context in session memory
3. **Smart Loading**: Auto-load relevant docs based on task
4. **Compression**: Use structured formats (YAML/JSON) where appropriate
5. **Summarization**: AI-generated summaries of detailed docs
