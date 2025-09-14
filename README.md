# ContextKit

Content-addressed storage for reusable LLM context with web interface.

ContextKit provides persistent context memory, file handling, and markdown rendering for LLM workflows. Capture and reuse analytical work across sessions.

## Recent Updates

### Web Interface
- Markdown rendering with syntax highlighting for code blocks
- Persistent file memory - uploaded files remain available throughout conversation
- Drag & drop file uploads with multiple upload methods
- Multi-stage LLM context selection from existing ContextPacks
- Automatic session saving to ContextPacks

### Context Management
- Multi-stage LLM context selection - finds relevant context from stored ContextPacks
- File persistence - uploaded files remain in memory across all messages
- Visual file tracking - displays which files are in current session
- Project-based context isolation - separate analyses by project name

## What it does

ContextKit solves the problem of losing valuable context when LLM conversations become too long or hit token limits. Instead of starting over, you can capture, organize, and reuse your analytical work.

**Core Workflow:**
- **Capture**: Save LLM chat sessions as structured markdown with automatic content hashing
- **Extract**: Automatically identify and store SQL queries, Python code, JavaScript, YAML configs, and other artifacts
- **Distill**: Create compact "ContextPacks" - structured summaries optimized for LLM reuse
- **Search**: Find relevant previous work using semantic similarity combined with metadata filters
- **Inject**: Copy-paste ready context into new LLM sessions with full provenance tracking
- **Web Interface**: Interactive chat with persistent file memory and markdown formatting

**Key Features:**
- Web interface with markdown rendering and syntax highlighting
- Persistent file memory - files stay in session throughout entire conversation
- Multi-stage context selection - LLM-powered context retrieval
- Content-addressed storage using BLAKE3 hashing for deduplication and integrity
- Enhanced artifact extraction supporting 15+ programming languages with metadata analysis
- Schema fingerprinting to detect database changes and assess ContextPack compatibility
- Hybrid search combining vector embeddings with traditional metadata filtering
- LLM-powered summarization with graceful fallback to heuristic methods
- Schema drift detection to warn when database structures have changed

Designed for data analysts, researchers, and developers who use LLMs for complex, multi-step analyses involving databases, code generation, and iterative problem-solving.

## Web Interface

The ContextKit web interface provides an interactive chat experience with context management:

### Getting Started
```bash
# Start the web interface
ctx web
# Open http://localhost:8000 in your browser
```

### Sample Workflow
1. Upload data files: drag `customers.csv` and `orders.csv` into the interface
2. Set project name: enter "analytics" to match existing ContextPacks
3. Ask questions: "What's the average customer lifetime value by channel?"
4. Follow up: "Which products have the highest margins?" (files remain in memory)
5. Get insights: the assistant uses both uploaded files and relevant ContextPacks
6. Access previous chats through the web interface

## Quick start

```bash
# Install
uv venv && source .venv/bin/activate
uv pip install -e .

# Save a chat session
ctx save-chat --project retail --title "Customer LTV Analysis" --from chat.md

# Create reusable context pack
ctx summarize chats/2025-09-07--customer-ltv-analysis.md

# Find relevant context
ctx find "ltv cohort retention"

# Inject into new session
ctx inject packs/customer-ltv-analysis--abc123.md

# Or use the web interface (recommended!)
ctx web
# Then open http://localhost:8000 in your browser
```

## Commands

- `ctx save-chat` - Ingest markdown chat, extract artifacts, update index
- `ctx summarize` - Create structured ContextPack from chat
- `ctx find` - Search chats and packs by content and metadata
- `ctx inject` - Output copy-pasteable context with provenance
- `ctx auto` - **Automatically compose relevant context for any prompt**
- `ctx schema fingerprint` - Snapshot database schema for compatibility tracking
- `ctx schema-drift` - Detect schema changes and assess ContextPack compatibility

Set `OPENAI_API_KEY` in `.env` for LLM-powered summarization.
