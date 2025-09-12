// Global state
let sessionId = generateSessionId();
let attachedFiles = [];
let sessionFiles = []; // Track files uploaded in this session

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
const fileDropZone = document.getElementById('file-drop-zone');
const browseButton = document.getElementById('browse-button');
const sessionFilesDiv = document.getElementById('session-files');

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
    
    // Show typing indicator
    showTyping(true);
    
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
        
        // Add user message to chat (after upload to show file content)
        addMessage('user', message, null, uploadedFiles.length > 0 ? uploadedFiles : null);
        
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
    
    // Update send button state when attachments change
    autoResize();
}

function removeAttachment(index) {
    attachedFiles.splice(index, 1);
    updateAttachments();
}

function updateSessionFiles() {
    if (!sessionFilesDiv) return;
    
    if (sessionFiles.length === 0) {
        sessionFilesDiv.innerHTML = '';
        return;
    }
    
    let html = `
        <div class="session-files-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 14px; height: 14px;">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10,9 9,9 8,9"/>
            </svg>
            Files in session memory (${sessionFiles.length})
        </div>
        <div class="session-files-list">
    `;
    
    sessionFiles.forEach(file => {
        html += `
            <div class="session-file">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 12px; height: 12px;">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                </svg>
                ${file.filename}
            </div>
        `;
    });
    
    html += '</div>';
    sessionFilesDiv.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make toggleContext global
window.toggleContext = toggleContext;
window.removeAttachment = removeAttachment;
