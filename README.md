# ContextKit

Content-addressed storage for reusable LLM context. Save chat sessions, extract artifacts, and retrieve relevant context for new analyses.

## What it does

- Save LLM chats as structured markdown with content hashing
- Extract SQL, code, and text artifacts automatically  
- Create compact "ContextPacks" for reuse in new sessions
- Search previous work using semantic similarity + metadata
- Track schema compatibility and provenance

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
- `ctx schema fingerprint` - Snapshot database schema for compatibility tracking

Set `OPENAI_API_KEY` in `.env` for LLM-powered summarization.
