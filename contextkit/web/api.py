"""FastAPI routes and models for the ContextKit web interface."""
from __future__ import annotations
import os
import json
import uuid
import tempfile
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import HTTPException, UploadFile, File
from pydantic import BaseModel
from contextkit.core.auto import auto_compose_context
from contextkit.commands.chat_commands import save_chat_command
from contextkit.core.utils import now_utc_iso

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
    attachments: Optional[List[Dict[str, Any]]] = None

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

def get_llm_response(prompt: str, context: Optional[str] = None) -> str:
    """Get response from OpenAI LLM."""
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "⚠️ OpenAI API key not set. Please set OPENAI_API_KEY environment variable to get real LLM responses."
        
        client = OpenAI(api_key=api_key)
        
        # Build the full prompt with context if available
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\nUser: {prompt}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful data analyst assistant. Use any provided context to give more informed responses."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"Error getting LLM response: {str(e)}"

def save_session_to_markdown(session_id: str, session_data: Dict[str, Any]) -> Optional[str]:
    """Save chat session to markdown file using ContextKit."""
    try:
        # Build markdown content from messages
        messages = session_data.get("messages", [])
        if not messages:
            return None
        
        # Create markdown content
        markdown_lines = []
        markdown_lines.append(f"# Chat Session: {session_data.get('project', 'Unknown Project')}")
        markdown_lines.append(f"Session ID: {session_id}")
        markdown_lines.append(f"Created: {session_data.get('created_at', datetime.now()).isoformat()}")
        markdown_lines.append("")
        
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
            else:
                role = msg.role
                content = msg.content
                timestamp = msg.timestamp
            
            if role == "user":
                markdown_lines.append(f"## User ({timestamp})")
                markdown_lines.append(content)
                markdown_lines.append("")
            elif role == "assistant":
                markdown_lines.append(f"## Assistant ({timestamp})")
                markdown_lines.append(content)
                markdown_lines.append("")
        
        # Save to temporary file first
        temp_file = Path(tempfile.gettempdir()) / f"contextkit_session_{session_id}.md"
        temp_file.write_text("\n".join(markdown_lines), encoding="utf-8")
        
        # Use ContextKit to save the chat
        project = session_data.get("project", "web-chat")
        title = f"Web Chat Session {session_id[:8]}"
        
        save_chat_command(
            project=project,
            title=title,
            from_=temp_file,
            schema=None,
            tags="web-chat,auto-saved"
        )
        
        # Clean up temp file
        temp_file.unlink()
        
        return f"Saved chat to ContextKit: {project}/{title}"
        
    except Exception as e:
        print(f"Error saving session to markdown: {e}")
        return None

async def handle_chat(request: ChatRequest) -> ChatResponse:
    """Handle chat messages with real LLM integration."""
    try:
        # Initialize session if it doesn't exist
        if request.session_id not in chat_sessions:
            chat_sessions[request.session_id] = {
                "created_at": datetime.now(),
                "messages": [],
                "contextkit_enabled": request.contextkit_enabled,
                "project": request.project or "web-chat"
            }
        
        session = chat_sessions[request.session_id]
        
        # Handle file attachments if present
        attachment_context = ""
        if request.attachments:
            attachment_context = "\n\nAttached files:\n"
            for attachment in request.attachments:
                filename = attachment.get("filename", "unknown")
                content = attachment.get("content", "")
                attachment_context += f"- {filename}:\n{content[:500]}...\n"
        
        # Add user message to session
        user_message = {
            "role": "user",
            "content": request.message + attachment_context,
            "timestamp": datetime.now().isoformat(),
            "attachments": request.attachments
        }
        session["messages"].append(user_message)
        
        # Generate response
        context_used = None
        context_metadata = None
        
        # Get context if ContextKit is enabled
        if request.contextkit_enabled:
            try:
                composed_context = auto_compose_context(
                    prompt=request.message,
                    max_tokens=request.max_context_tokens,
                    current_schema=None,
                    project=request.project
                )
                
                # Extract context and metadata
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
                        
            except Exception as e:
                print(f"ContextKit error: {e}")
                context_used = None
        
        # Get LLM response
        full_prompt = request.message + attachment_context
        response_content = get_llm_response(full_prompt, context_used)
        
        # Add assistant message to session
        assistant_message = {
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.now().isoformat(),
            "context_used": context_used,
            "context_visible": False
        }
        session["messages"].append(assistant_message)
        
        # Auto-save session to ContextKit every few messages
        if len(session["messages"]) % 6 == 0:  # Save every 3 exchanges
            save_result = save_session_to_markdown(request.session_id, session)
            if save_result:
                print(f"Auto-saved session: {save_result}")
        
        return ChatResponse(
            session_id=request.session_id,
            response=response_content,
            context_used=context_used,
            context_metadata=context_metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

async def handle_upload(files: List[UploadFile]) -> Dict[str, Any]:
    """Handle file uploads and extract content for ContextKit."""
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
            
            # Extract content based on file type
            content = ""
            try:
                if file.content_type and file.content_type.startswith("text/"):
                    content = temp_file.read_text(encoding="utf-8")
                elif file.filename and file.filename.endswith((".md", ".txt", ".py", ".sql", ".js", ".json", ".yaml", ".yml")):
                    content = temp_file.read_text(encoding="utf-8")
                elif file.filename and file.filename.endswith(".csv"):
                    # For CSV files, read first few rows
                    lines = temp_file.read_text(encoding="utf-8").split('\n')
                    content = '\n'.join(lines[:10]) + f"\n... ({len(lines)} total rows)"
                else:
                    content = f"Binary file: {file.filename} ({file.size} bytes)"
            except Exception as e:
                content = f"Could not read file content: {str(e)}"
            
            uploaded_files.append({
                "filename": file.filename,
                "content_type": file.content_type,
                "size": file.size,
                "temp_path": str(temp_file),
                "content": content[:2000]  # Limit content size
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
        # Save session before deleting if it has messages
        session_data = chat_sessions[session_id]
        if session_data.get("messages"):
            save_result = save_session_to_markdown(session_id, session_data)
            if save_result:
                print(f"Saved session before deletion: {save_result}")
        
        del chat_sessions[session_id]
        return {"status": "success", "message": "Session deleted and saved to ContextKit"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")
