// Global state
let sessionId = generateSessionId();
let attachedFiles = [];

// DOM elements
const messagesArea = document.getElementById('messages-area');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const attachButton = document.getElementById('attach-button');
const fileInput = document.getElementById('file-input');
const attachmentsDiv = document.getElementById('attachments');
const contextkitToggle = document.getElementById('contextkit-toggle');
const projectInput = document.getElementById('project-input');
const typingIndicator = document.getElementById('typing-indicator');

// Event listeners
messageInput.addEventListener('keydown', handleKeyDown);
messageInput.addEventListener('input', autoResize);
sendButton.addEventListener('click', sendMessage);
attachButton.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileUpload);

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
    messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message && attachedFiles.length === 0) return;
    
    // Add user message to chat
    addMessage('user', message, null, attachedFiles.length > 0 ? [...attachedFiles] : null);
    
    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    // Show typing indicator
    showTyping(true);
    
    // Disable send button
    sendButton.disabled = true;
    
    try {
        // Prepare request
        const requestData = {
            session_id: sessionId,
            message: message,
            contextkit_enabled: contextkitToggle.checked,
            project: projectInput.value.trim() || null,
            max_context_tokens: 8000
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
    
    let html = `<div>${escapeHtml(content)}</div>`;
    
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
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

function toggleContext(contextId) {
    const contextDiv = document.getElementById(contextId);
    contextDiv.classList.toggle('visible');
}

function showTyping(show) {
    typingIndicator.style.display = show ? 'block' : 'none';
    if (show) {
        messagesArea.scrollTop = messagesArea.scrollHeight;
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
}

function removeAttachment(index) {
    attachedFiles.splice(index, 1);
    updateAttachments();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make toggleContext global
window.toggleContext = toggleContext;
window.removeAttachment = removeAttachment;
