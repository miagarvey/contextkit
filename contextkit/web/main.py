"""Main FastAPI application for ContextKit web interface."""
from __future__ import annotations
import os
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv
from contextkit.web.templates import get_main_template
from contextkit.web.api import (
    ChatRequest, ChatResponse, SessionInfo,
    handle_chat, handle_upload, get_sessions, save_session, delete_session
)

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="ContextKit Chat Assistant",
    description="Full LLM assistant with automated context composition",
    version="0.2.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/")
async def root():
    """Serve the main chat interface."""
    return HTMLResponse(content=get_main_template())

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages with optional ContextKit integration."""
    return await handle_chat(request)

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Handle file uploads for chat attachments."""
    return await handle_upload(files)

@app.get("/api/sessions")
async def list_sessions():
    """List all chat sessions."""
    return get_sessions()

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific chat session with all messages."""
    from contextkit.web.api import chat_sessions
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return chat_sessions[session_id]

@app.post("/api/sessions/{session_id}/save")
async def save_session_endpoint(session_id: str):
    """Save a chat session to ContextKit."""
    return save_session(session_id)

@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    """Delete a chat session."""
    return delete_session(session_id)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "contextkit-chat-assistant"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
