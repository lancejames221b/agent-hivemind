# Conversation Import Examples

## How to Use Conversation Import

The memory MCP server can import full conversations and automatically parse them into structured memories.

## Usage Examples

### 1. Import from Clipboard

**You:** Import this conversation I had with Claude:

Human: How do I set up a Python virtual environment?
Assistant: You can set up a Python virtual environment using venv. Here's how:

1. Create a virtual environment:
   python -m venv myenv

2. Activate it:
   - On Windows: myenv\Scripts\activate
   - On macOS/Linux: source myenv/bin/activate

3. Install packages:
   pip install requests

Human: What about using conda instead?
Assistant: Conda is another great option! Here's how to use conda:

1. Create environment:
   conda create -n myenv python=3.9

2. Activate:
   conda activate myenv

3. Install packages:
   conda install requests

Conda manages both Python versions and packages, making it easier for data science workflows.

**Claude:** *Uses import_conversation tool*

✅ **Result:** Imported conversation "How do I set up a Python..." with 4 messages
- **Conversation ID:** abc123-def456
- **Messages stored:** 4 (2 user, 2 assistant)
- **Categories:** conversation (user messages), agent (assistant responses)
- **Tags:** imported, conversation, clipboard

### 2. Import from File

**You:** Import the conversation from ~/Downloads/claude-chat-export.txt

**Claude:** *Uses import_conversation_file tool*

✅ **Result:** Imported conversation "claude-chat-export" with 12 messages
- **File:** /home/user/Downloads/claude-chat-export.txt
- **Messages:** 12 (6 user, 6 assistant)
- **Tags:** imported, file_import, conversation

## Supported Formats

The parser automatically detects:

### Claude Export Format
```
Human: Your question here
Assistant: My response here

Human: Follow-up question
Assistant: Another response
```

### ChatGPT Format
```
User: Your question
ChatGPT: My response

User: Next question
ChatGPT: Next response
```

### Generic Chat Format
```
Speaker1: Message content
Speaker2: Response content
```

### Timestamped Format
```
[2024-08-21 10:30] User: Question
[2024-08-21 10:31] Assistant: Answer
```

## What Gets Stored

When you import a conversation, the system creates:

1. **Full Conversation Memory** (conversation category)
   - Complete conversation text
   - Metadata: participants, message count, import date

2. **Individual Message Memories**
   - User messages → conversation category
   - Assistant messages → agent category
   - Each with conversation context and metadata

3. **Summary Memory** (global category)
   - High-level overview of the imported conversation

## Finding Imported Conversations

### Search by Content
```
You: "What did I ask about Python environments?"
Claude: *Searches and finds your original question*
```

### Search by Assistant Responses
```
You: "How did Claude explain conda?"
Claude: *Finds the assistant's conda explanation*
```

### Find Full Conversations
```
You: "Show me recent imported conversations"
Claude: *Lists conversations with summaries*
```

## Advanced Usage

### With Custom Tags
**You:** Import this conversation and tag it with "python", "setup", "tutorial"

**Claude:** *Imports with custom tags for better organization*

### With Custom Title
**You:** Import this conversation with the title "Python Environment Setup Guide"

**Claude:** *Uses your custom title instead of auto-generated one*

### File Import with Path Expansion
**You:** Import conversation from ~/Documents/important-chat.txt

**Claude:** *Handles path expansion and imports the file*

## Benefits

✅ **Searchable History** - Find any part of past conversations
✅ **Context Preservation** - Maintains conversation flow and context
✅ **Smart Categorization** - Automatically sorts by speaker role
✅ **Cross-Machine Sync** - Available on all connected machines
✅ **Semantic Search** - Find conversations by meaning, not just keywords

## Tips

- **Large Conversations**: No size limit - import entire long discussions
- **Multiple Formats**: Works with exports from Claude, ChatGPT, and other AI systems
- **Batch Import**: Import multiple conversation files by running the command multiple times
- **Organization**: Use tags and custom titles for better organization
- **Integration**: Imported conversations integrate seamlessly with other memory tools

Your conversation history becomes a searchable knowledge base across all your AI interactions!