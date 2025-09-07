"""FastAPI routes and models for the ContextKit web interface."""
from __future__ import annotations
import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import HTTPException, UploadFile, File
from pydantic import BaseModel
from contextkit.core.auto import auto_compose_context
import tempfile
import shutil

# In-memory chat sessions (in production, use Redis or database)
chat_sessions: Dict[str, Dict[str, Any]] = {}

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    context_used: Optional[str] = None
    context_visible: bool = False
    attachments: Optional[List[Dict[str, Any]]] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str
    contextkit_enabled: bool = True
    project: Optional[str] = None
    max_context_tokens: int = 8000

class ChatResponse(BaseModel):
    session_id: str
    response: str
    context_used: Optional[str] = None
    context_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    message_count: int
    contextkit_enabled: bool
    project: Optional[str] = None

async def handle_chat(request: ChatRequest) -> ChatResponse:
    """Handle chat messages with optional ContextKit integration."""
    try:
        # Initialize session if it doesn't exist
        if request.session_id not in chat_sessions:
            chat_sessions[request.session_id] = {
                "created_at": datetime.now(),
                "messages": [],
                "contextkit_enabled": request.contextkit_enabled,
                "project": request.project
            }
        
        session = chat_sessions[request.session_id]
        
        # Add user message to session
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now()
        )
        session["messages"].append(user_message)
        
        # Generate response
        response_content = ""
        context_used = None
        context_metadata = None
        
        if request.contextkit_enabled:
            # Use ContextKit to compose context
            try:
                composed_context = auto_compose_context(
                    prompt=request.message,
                    max_tokens=request.max_context_tokens,
                    current_schema=None
                )
                
                # Extract the actual context and metadata
                if "[CONTEXTKIT]" in composed_context:
                    parts = composed_context.split("[CONTEXTKIT]", 1)
                    if len(parts) > 1:
                        context_used = "[CONTEXTKIT]" + parts[1]
                        
                        # Extract metadata
                        lines = context_used.split('\n')
                        packs_used = []
                        token_count = 0
                        
                        for line in lines:
                            if "ContextPack(s):" in line:
                                packs_part = line.split("ContextPack(s):")[1].strip()
                                packs_used = [p.strip() for p in packs_part.split(",") if p.strip()]
                            elif "Estimated tokens:" in line:
                                try:
                                    token_part = line.split("Estimated tokens:")[1].split("/")[0].strip()
                                    token_count = int(token_part)
                                except (IndexError, ValueError):
                                    pass
                        
                        context_metadata = {
                            "packs_used": packs_used,
                            "token_count": token_count
                        }
                
                # For now, simulate an LLM response based on the context
                if context_used:
                    response_content = f"Based on the context from your previous conversations, I can help you with that. I found {len(context_metadata.get('packs_used', []))} relevant ContextPack(s) that contain information about your request.\n\n"
                    response_content += "Here's what I can tell you:\n"
                    response_content += "• I have access to your previous analysis patterns and code\n"
                    response_content += "• I can build upon your existing work\n"
                    response_content += "• I understand your data schema and business context\n\n"
                    response_content += "Please note: This is a demo response. In a full implementation, this would be sent to an actual LLM (OpenAI, Claude, etc.) along with the composed context."
                else:
                    response_content = "I don't have relevant context for this request, but I can still help you. What would you like to know?"
                    
            except Exception as e:
                response_content = f"I encountered an issue with ContextKit ({str(e)}), but I can still assist you. What would you like to know?"
        else:
            # ContextKit disabled - provide basic response
            response_content = "ContextKit is disabled. I'm responding without additional context. How can I help you today?"
        
        # Add assistant message to session
        assistant_message = ChatMessage(
            role="assistant",
            content=response_content,
            timestamp=datetime.now(),
            context_used=context_used,
            context_visible=False
        )
        session["messages"].append(assistant_message)
        
        return ChatResponse(
            session_id=request.session_id,
            response=response_content,
            context_used=context_used,
            context_metadata=context_metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

async def handle_upload(files: List[UploadFile]) -> Dict[str, Any]:
    """Handle file uploads for chat attachments."""
    try:
        uploaded_files = []
        
        for file in files:
            # Create temporary file
            temp_dir = Path(tempfile.gettempdir()) / "contextkit_uploads"
            temp_dir.mkdir(exist_ok=True)
            
            temp_file = temp_dir / f"{uuid.uuid4()}_{file.filename}"
            
            # Save file
            with temp_file.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "filename": file.filename,
                "content_type": file.content_type,
                "size": file.size,
                "temp_path": str(temp_file)
            })
        
        return {
            "status": "success",
            "files": uploaded_files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")

def get_sessions() -> List[SessionInfo]:
    """List all chat sessions."""
    sessions = []
    for session_id, session_data in chat_sessions.items():
        sessions.append(SessionInfo(
            session_id=session_id,
            created_at=session_data["created_at"],
            message_count=len(session_data["messages"]),
            contextkit_enabled=session_data.get("contextkit_enabled", True),
            project=session_data.get("project")
        ))
    return sessions

def delete_session(session_id: str) -> Dict[str, str]:
    """Delete a chat session."""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return {"status": "success", "message": "Session deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")
