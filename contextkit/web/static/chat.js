// Global state
let sessionId = generateSessionId();
let attachedFiles = [];
let sessionFiles = []; // Track files uploaded in this session
let currentSessionId = null;
let chatSessions = [];

// DOM elements
const messagesArea = document.getElementById('messages-area');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const attachButton = document.getElementById('attach-button');
const fileInput = document.getElementById('file-input');
const attachmentsDiv = document.getElementById('attachments');
const contextkitToggle = document.getElementById('contextkit-toggle');
const projectInput = document.getElementById('project-input');
const fileDropZone = document.getElementById('file-drop-zone');
const browseButton = document.getElementById('browse-button');
let typingIndicator = null; // Will be created dynamically
// Removed sessionFilesDiv - no longer needed

// Event listeners
messageInput.addEventListener('keydown', handleKeyDown);
messageInput.addEventListener('input', autoResize);
sendButton.addEventListener('click', sendMessage);
attachButton.addEventListener('click', () => {
    console.log('Attach button clicked');
    if (fileDropZone) {
        fileDropZone.classList.add('visible');
        console.log('Drop zone made visible');
    } else {
        console.error('File drop zone element not found');
    }
});

if (fileInput) {
    fileInput.addEventListener('change', handleFileUpload);
} else {
    console.error('Cannot add change listener - file input not found');
}

// Browse button and drag-and-drop functionality
if (browseButton) {
    browseButton.addEventListener('click', (e) => {
        e.preventDefault();
        if (fileInput) {
            fileInput.click();
        }
    });
}

if (fileDropZone) {
    // Show drop zone when files are being dragged
    document.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileDropZone.classList.add('visible');
    });
    
    document.addEventListener('dragleave', (e) => {
        // Only hide if we're leaving the document entirely
        if (!e.relatedTarget) {
            fileDropZone.classList.remove('visible');
        }
    });
    
    // Drop zone events
    fileDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileDropZone.classList.add('drag-over');
    });
    
    fileDropZone.addEventListener('dragleave', (e) => {
        if (!fileDropZone.contains(e.relatedTarget)) {
            fileDropZone.classList.remove('drag-over');
        }
    });
    
    fileDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileDropZone.classList.remove('visible', 'drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            attachedFiles.push(...files);
            updateAttachments();
        }
    });
    
    // Click to browse
    fileDropZone.addEventListener('click', () => {
        if (fileInput) {
            fileInput.click();
        }
    });
}

// Hide drop zone when clicking outside or pressing escape
document.addEventListener('click', (e) => {
    if (fileDropZone && fileDropZone.classList.contains('visible')) {
        // If click is outside the drop zone and not on the attach button
        if (!fileDropZone.contains(e.target) && !attachButton.contains(e.target)) {
            fileDropZone.classList.remove('visible');
        }
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && fileDropZone && fileDropZone.classList.contains('visible')) {
        fileDropZone.classList.remove('visible');
    }
});

// Debug: Check if elements exist
console.log('DOM elements:', {
    attachButton: !!attachButton,
    fileInput: !!fileInput,
    attachmentsDiv: !!attachmentsDiv,
    attachButtonElement: attachButton,
    fileInputElement: fileInput
});

// Additional debugging for file input
if (fileInput) {
    console.log('File input details:', {
        type: fileInput.type,
        multiple: fileInput.multiple,
        accept: fileInput.accept,
        style: fileInput.style.display
    });
} else {
    console.log('File input element not found!');
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
    
    // Update send button state based on input content
    const hasContent = messageInput.value.trim().length > 0 || attachedFiles.length > 0;
    if (hasContent) {
        sendButton.classList.add('active');
    } else {
        sendButton.classList.remove('active');
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message && attachedFiles.length === 0) return;
    
    // Disable send button
    sendButton.disabled = true;
    
    try {
        // Upload files first if any
        let uploadedFiles = [];
        if (attachedFiles.length > 0) {
            const formData = new FormData();
            attachedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            if (uploadResponse.ok) {
                const uploadData = await uploadResponse.json();
                uploadedFiles = uploadData.files || [];
            } else {
                console.error('File upload failed');
            }
        }
        
        // Add uploaded files to session files list
        if (uploadedFiles.length > 0) {
            uploadedFiles.forEach(file => {
                // Check if file already exists in session
                const existingFile = sessionFiles.find(f => f.filename === file.filename);
                if (!existingFile) {
                    sessionFiles.push(file);
                }
            });
            updateSessionFiles();
        }
        
        // Add user message to chat first (after upload to show file content)
        addMessage('user', message, null, uploadedFiles.length > 0 ? uploadedFiles : null);
        
        // Show typing indicator after user message
        showTyping(true);
        
        // Clear input
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // Prepare request
        const requestData = {
            session_id: sessionId,
            message: message,
            contextkit_enabled: contextkitToggle.checked,
            project: projectInput.value.trim() || null,
            max_context_tokens: 8000,
            attachments: uploadedFiles
        };
        
        // Send request
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Set currentSessionId to track this session for saving
            if (!currentSessionId) {
                currentSessionId = sessionId;
            }
            
            // Add assistant response
            addMessage('assistant', data.response, data.context_used, null, data.context_metadata);
        } else {
            addMessage('assistant', `Error: ${data.error || 'Unknown error'}`, null);
        }
    } catch (error) {
        addMessage('assistant', `Network error: ${error.message}`, null);
    } finally {
        showTyping(false);
        sendButton.disabled = false;
        attachedFiles = [];
        updateAttachments();
    }
}

function addMessage(role, content, contextUsed = null, attachments = null, contextMetadata = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    // Configure marked for better code rendering
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            highlight: function(code, lang) {
                if (typeof Prism !== 'undefined' && Prism.languages[lang]) {
                    return Prism.highlight(code, Prism.languages[lang], lang);
                }
                return code;
            },
            breaks: true,
            gfm: true
        });
    }
    
    // Render content as markdown for assistant messages, plain text for user messages
    let renderedContent;
    if (role === 'assistant' && typeof marked !== 'undefined') {
        renderedContent = marked.parse(content);
    } else {
        renderedContent = `<p>${escapeHtml(content).replace(/\n/g, '<br>')}</p>`;
    }
    
    let html = `<div class="message-content">${renderedContent}</div>`;
    
    // Add timestamp
    const timestamp = new Date().toLocaleTimeString();
    html += `<div class="message-meta">${timestamp}`;
    
    // Add context toggle for assistant messages with context
    if (role === 'assistant' && contextUsed) {
        const contextId = 'context_' + Date.now();
        html += ` • <button class="context-toggle" onclick="toggleContext('${contextId}')">View Context</button>`;
        html += `</div>`;
        html += `<div class="context-display" id="${contextId}">${escapeHtml(contextUsed)}</div>`;
    } else {
        html += `</div>`;
    }
    
    // Add attachments info for user messages
    if (attachments && attachments.length > 0) {
        html += `<div class="message-meta">📎 ${attachments.length} file(s) attached</div>`;
    }
    
    messageDiv.innerHTML = html;
    messagesArea.appendChild(messageDiv);
    
    // Trigger syntax highlighting for any new code blocks
    if (typeof Prism !== 'undefined') {
        Prism.highlightAllUnder(messageDiv);
    }
    
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

function toggleContext(contextId) {
    const contextDiv = document.getElementById(contextId);
    contextDiv.classList.toggle('visible');
}

function showTyping(show) {
    if (show) {
        // Create typing indicator if it doesn't exist
        if (!typingIndicator) {
            typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            typingIndicator.innerHTML = `
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
        }
        
        // Insert typing indicator after the last message (which should be the user's message)
        messagesArea.appendChild(typingIndicator);
        typingIndicator.style.display = 'block';
        messagesArea.scrollTop = messagesArea.scrollHeight;
    } else {
        // Remove typing indicator from DOM
        if (typingIndicator && typingIndicator.parentNode) {
            typingIndicator.parentNode.removeChild(typingIndicator);
        }
    }
}

function handleFileUpload(e) {
    const files = Array.from(e.target.files);
    attachedFiles.push(...files);
    updateAttachments();
    e.target.value = ''; // Reset file input
}

function updateAttachments() {
    attachmentsDiv.innerHTML = '';
    attachedFiles.forEach((file, index) => {
        const attachmentDiv = document.createElement('div');
        attachmentDiv.className = 'attachment';
        attachmentDiv.innerHTML = `
            <span>📄 ${file.name}</span>
            <button class="remove" onclick="removeAttachment(${index})">×</button>
        `;
        attachmentsDiv.appendChild(attachmentDiv);
    });
    
    // Update send button state when attachments change
    autoResize();
}

function removeAttachment(index) {
    attachedFiles.splice(index, 1);
    updateAttachments();
}

function updateSessionFiles() {
    // Files are now handled in context automatically - no UI indicator needed
    // This function is kept for compatibility but does nothing
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Chat history management
async function loadChatSessions() {
    try {
        const response = await fetch('/api/sessions');
        if (response.ok) {
            chatSessions = await response.json();
            updateChatList();
        }
    } catch (error) {
        console.error('Error loading chat sessions:', error);
    }
}

function updateChatList() {
    const chatList = document.getElementById('chat-list');
    if (!chatList) return;
    
    if (chatSessions.length === 0) {
        chatList.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-muted); font-size: 0.875rem;">No previous chats</div>';
        return;
    }
    
    chatList.innerHTML = '';
    chatSessions.forEach(session => {
        const chatItem = document.createElement('div');
        chatItem.className = `chat-item ${session.session_id === currentSessionId ? 'active' : ''}`;
        chatItem.onclick = () => loadChatSession(session.session_id);
        
        // Generate title from first message or use default
        const title = session.title || `Chat ${session.session_id.slice(-8)}`;
        const timeAgo = formatTimeAgo(new Date(session.created_at));
        
        chatItem.innerHTML = `
            <div class="chat-item-title">${escapeHtml(title)}</div>
            <div class="chat-item-meta">
                <span>${timeAgo}</span>
                ${session.project ? `<span class="chat-item-project">${escapeHtml(session.project)}</span>` : ''}
            </div>
        `;
        
        chatList.appendChild(chatItem);
    });
}

async function loadChatSession(sessionIdToLoad) {
    try {
        const response = await fetch(`/api/sessions/${sessionIdToLoad}`);
        if (response.ok) {
            const sessionData = await response.json();
            
            // Update current session
            currentSessionId = sessionIdToLoad;
            sessionId = sessionIdToLoad;  // Update the global sessionId for future messages
            
            // Clear current messages
            messagesArea.innerHTML = '';
            
            // Load session files
            sessionFiles = sessionData.uploaded_files || [];
            updateSessionFiles();
            
            // Load messages
            if (sessionData.messages && sessionData.messages.length > 0) {
                sessionData.messages.forEach(msg => {
                    addMessage(msg.role, msg.content, msg.context_used, msg.attachments);
                });
            } else {
                // Show welcome message for empty session
                addMessage('assistant', "Hello! I'm your ContextKit-powered assistant. I can help you with data analysis, code generation, and more. When ContextKit is enabled, I'll automatically find and use relevant context from your previous conversations.");
            }
            
            // Update project input
            if (sessionData.project) {
                projectInput.value = sessionData.project;
            }
            
            // Update ContextKit toggle
            if (sessionData.contextkit_enabled !== undefined) {
                contextkitToggle.checked = sessionData.contextkit_enabled;
            }
            
            // Update chat list to show active session
            updateChatList();
            
        } else {
            console.error('Failed to load chat session');
        }
    } catch (error) {
        console.error('Error loading chat session:', error);
    }
}

async function startNewChat() {
    // Save current session if it has messages and isn't already saved
    const sessionToSave = currentSessionId || sessionId; // Use currentSessionId or fallback to sessionId
    if (sessionToSave && messagesArea.children.length > 1) { // More than just welcome message
        try {
            // Save current session using the dedicated save endpoint
            const saveResponse = await fetch(`/api/sessions/${sessionToSave}/save`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (saveResponse.ok) {
                const saveData = await saveResponse.json();
                console.log('Current session saved before starting new chat:', saveData.message);
            } else {
                console.warn('Failed to save current session');
            }
        } catch (error) {
            console.error('Error saving current session:', error);
        }
    }
    
    // Generate new session ID
    sessionId = generateSessionId();
    currentSessionId = null;
    
    // Clear current state
    messagesArea.innerHTML = '';
    sessionFiles = [];
    attachedFiles = [];
    updateSessionFiles();
    updateAttachments();
    
    // Reset form
    messageInput.value = '';
    projectInput.value = '';
    contextkitToggle.checked = true;
    
    // Show welcome message
    addMessage('assistant', "Hello! I'm your ContextKit-powered assistant. I can help you with data analysis, code generation, and more. When ContextKit is enabled, I'll automatically find and use relevant context from your previous conversations.");
    
    // Reload chat list to show the saved session
    await loadChatSessions();
}

function formatTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

// Initialize chat history on page load
document.addEventListener('DOMContentLoaded', () => {
    loadChatSessions();
    
    // Add new chat button listener
    const newChatBtn = document.getElementById('new-chat-btn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', startNewChat);
    }
    
    // Add collapse button listener
    const collapseBtn = document.getElementById('collapse-btn');
    const sidebar = document.getElementById('sidebar');
    console.log('Collapse button found:', !!collapseBtn);
    console.log('Sidebar found:', !!sidebar);
    
    if (collapseBtn && sidebar) {
        console.log('Adding collapse button listener');
        collapseBtn.addEventListener('click', () => {
            console.log('Collapse button clicked');
            sidebar.classList.toggle('collapsed');
            
            // Update button title
            if (sidebar.classList.contains('collapsed')) {
                collapseBtn.title = 'Expand sidebar';
                console.log('Sidebar collapsed');
            } else {
                collapseBtn.title = 'Collapse sidebar';
                console.log('Sidebar expanded');
            }
        });
    } else {
        console.error('Collapse button or sidebar not found!');
    }
});

// Make functions global
window.toggleContext = toggleContext;
window.removeAttachment = removeAttachment;
window.loadChatSession = loadChatSession;
