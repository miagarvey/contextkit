# ContextKit

Content-addressed storage for reusable LLM context. Save chat sessions, extract artifacts, and retrieve relevant context for new analyses.

## What it does

ContextKit solves the problem of losing valuable context when LLM conversations become too long or hit token limits. Instead of starting over, you can capture, organize, and reuse your analytical work.

**Core Workflow:**
- **Capture**: Save LLM chat sessions as structured markdown with automatic content hashing
- **Extract**: Automatically identify and store SQL queries, Python code, JavaScript, YAML configs, and other artifacts
- **Distill**: Create compact "ContextPacks" - structured summaries optimized for LLM reuse
- **Search**: Find relevant previous work using semantic similarity combined with metadata filters
- **Inject**: Copy-paste ready context into new LLM sessions with full provenance tracking

**Key Features:**
- Content-addressed storage using BLAKE3 hashing for deduplication and integrity
- Enhanced artifact extraction supporting 15+ programming languages with metadata analysis
- Schema fingerprinting to detect database changes and assess ContextPack compatibility
- Hybrid search combining vector embeddings with traditional metadata filtering
- LLM-powered summarization with graceful fallback to heuristic methods
- Schema drift detection to warn when database structures have changed

Perfect for data analysts, researchers, and developers who frequently use LLMs for complex, multi-step analyses involving databases, code generation, and iterative problem-solving.

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
