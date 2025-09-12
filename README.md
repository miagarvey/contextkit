# ContextKit

**Next-generation LLM context management with intelligent web interface**

ContextKit transforms how you work with LLMs by providing persistent context memory, intelligent file handling, and beautiful markdown rendering. Never lose valuable analytical work again.

## 🚀 What's New

### **Professional Web Interface**
- **Beautiful markdown rendering** with syntax highlighting for code blocks
- **Persistent file memory** - upload once, use throughout entire conversation
- **Drag & drop file uploads** with multiple upload methods
- **Real-time context selection** using multi-stage LLM processing
- **Session management** with automatic chat saving to ContextPacks

### **Intelligent Context System**
- **Multi-stage LLM context selection** - automatically finds the most relevant context
- **Smart file persistence** - uploaded files remain in memory across all messages
- **Visual file tracking** - see exactly which files are in your session
- **Context isolation by project** - keep different analyses separate

## What it does

ContextKit solves the problem of losing valuable context when LLM conversations become too long or hit token limits. Instead of starting over, you can capture, organize, and reuse your analytical work.

**Core Workflow:**
- **Capture**: Save LLM chat sessions as structured markdown with automatic content hashing
- **Extract**: Automatically identify and store SQL queries, Python code, JavaScript, YAML configs, and other artifacts
- **Distill**: Create compact "ContextPacks" - structured summaries optimized for LLM reuse
- **Search**: Find relevant previous work using semantic similarity combined with metadata filters
- **Inject**: Copy-paste ready context into new LLM sessions with full provenance tracking
- **Web Interface**: Interactive chat with persistent file memory and beautiful formatting

**Key Features:**
- **Professional web interface** with markdown rendering and syntax highlighting
- **Persistent file memory** - files stay in session throughout entire conversation
- **Multi-stage context selection** - intelligent LLM-powered context retrieval
- Content-addressed storage using BLAKE3 hashing for deduplication and integrity
- Enhanced artifact extraction supporting 15+ programming languages with metadata analysis
- Schema fingerprinting to detect database changes and assess ContextPack compatibility
- Hybrid search combining vector embeddings with traditional metadata filtering
- LLM-powered summarization with graceful fallback to heuristic methods
- Schema drift detection to warn when database structures have changed

Perfect for data analysts, researchers, and developers who frequently use LLMs for complex, multi-step analyses involving databases, code generation, and iterative problem-solving.

## 🌐 Web Interface

The ContextKit web interface provides a premium chat experience with intelligent context management:

### **Getting Started**
```bash
# Start the web interface
ctx web
# Open http://localhost:8000 in your browser
```

### **Key Features**

#### **📁 Persistent File Memory**
- **Upload once, use forever**: Files remain in session memory throughout the entire conversation
- **Multiple upload methods**: Drag & drop, browse button, or attachment icon
- **Visual tracking**: See all uploaded files in the "Files in session memory" section
- **Smart deduplication**: Prevents duplicate files from cluttering your session

#### **🎨 Beautiful Markdown Rendering**
- **Syntax highlighting**: Code blocks with proper language detection and coloring
- **Rich formatting**: Headers, lists, tables, blockquotes, and more
- **Professional styling**: Clean, readable interface optimized for technical content
- **Copy-friendly**: Easy to copy code snippets and formatted text

#### **🧠 Intelligent Context Selection**
- **Multi-stage LLM processing**: Automatically finds the most relevant context from your ContextPacks
- **Project isolation**: Set project names to keep different analyses separate
- **Context visibility**: Toggle to see exactly what context was used for each response
- **Smart relevance**: Combines your uploaded files with existing ContextPacks

#### **💬 Enhanced Chat Experience**
- **Real-time responses**: Streaming responses with typing indicators
- **Session persistence**: Conversations are automatically saved as ContextPacks
- **File attachments**: Support for CSV, JSON, Python, SQL, Markdown, and more
- **Context toggle**: View the exact context used for any assistant response

### **Sample Workflow**
1. **Upload your data**: Drag `customers.csv` and `orders.csv` into the interface
2. **Set project**: Enter "analytics" to match existing ContextPacks
3. **Ask questions**: "What's the average customer lifetime value by channel?"
4. **Follow up**: "Which products have the highest margins?" (files still in memory!)
5. **Get insights**: The assistant uses both your files and relevant ContextPacks

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
