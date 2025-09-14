"""HTML templates for the ContextKit web interface."""

def get_main_template() -> str:
    """Return the main chat interface HTML template."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ContextKit Assistant</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="header">
        <h1>ContextKit Assistant</h1>
        <div class="controls">
            <div class="control-group">
                <label for="contextkit-toggle" class="control-label">ContextKit</label>
                <label class="toggle-switch">
                    <input type="checkbox" id="contextkit-toggle" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <input type="text" id="project-input" class="project-input" placeholder="Project (optional)">
        </div>
    </div>
    
    <div class="chat-container">
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <h3>Chat History</h3>
                <div class="sidebar-controls">
                    <button class="new-chat-btn" id="new-chat-btn" title="Start new chat">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 5v14M5 12h14"/>
                        </svg>
                    </button>
                    <button class="collapse-btn" id="collapse-btn" title="Collapse sidebar" onclick="toggleSidebar()">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="15,18 9,12 15,6"/>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="chat-list" id="chat-list">
                <!-- Chat sessions will be loaded here -->
            </div>
        </div>
        <div class="main-chat">
            <div class="messages-area" id="messages-area">
                <div class="message assistant">
                    <div>Hello! I'm your ContextKit-powered assistant. I can help you with data analysis, code generation, and more. When ContextKit is enabled, I'll automatically find and use relevant context from your previous conversations.</div>
                    <div class="message-meta">
                        Try asking me about your data, uploading files, or connecting your database schema.
                    </div>
                </div>
            </div>
        
        <div class="typing-indicator" id="typing-indicator">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
        
        <div class="input-area">
            <div class="attachments" id="attachments"></div>
            <div class="file-drop-zone" id="file-drop-zone">
                <div class="drop-zone-content">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14,2 14,8 20,8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                        <polyline points="10,9 9,9 8,9"/>
                    </svg>
                    <p>Drop files here or <button class="browse-button" id="browse-button">browse</button></p>
                </div>
            </div>
            <div class="input-container">
                <div class="input-wrapper">
                    <textarea 
                        id="message-input" 
                        class="message-input" 
                        placeholder="Type your message..."
                        rows="1"
                    ></textarea>
                    <button class="attach-button" id="attach-button" title="Attach files">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.64 16.2a2 2 0 0 1-2.83-2.83l8.49-8.49"/>
                        </svg>
                    </button>
                    <input type="file" id="file-input" multiple 
                           accept=".txt,.md,.sql,.py,.js,.json,.csv,.xlsx,.pdf"
                           style="position: absolute; left: -9999px;">
                </div>
                <button class="send-button" id="send-button" title="Send message">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/>
                    </svg>
                </button>
            </div>
        </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/marked@9.1.2/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-core.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism.min.css">
    <script>
        // Make sure function is available globally
        window.toggleSidebar = function() {
            console.log('toggleSidebar called');
            const sidebar = document.getElementById('sidebar');
            const collapseBtn = document.getElementById('collapse-btn');
            
            console.log('Sidebar element:', sidebar);
            console.log('Collapse button element:', collapseBtn);
            
            if (sidebar && collapseBtn) {
                sidebar.classList.toggle('collapsed');
                
                if (sidebar.classList.contains('collapsed')) {
                    collapseBtn.title = 'Expand sidebar';
                    console.log('Sidebar collapsed');
                } else {
                    collapseBtn.title = 'Collapse sidebar';
                    console.log('Sidebar expanded');
                }
            } else {
                console.error('Sidebar or collapse button not found');
                console.error('Sidebar:', sidebar);
                console.error('Collapse button:', collapseBtn);
            }
        };
        
        // Also add event listener as backup
        document.addEventListener('DOMContentLoaded', function() {
            const collapseBtn = document.getElementById('collapse-btn');
            if (collapseBtn) {
                console.log('Adding click event listener to collapse button');
                collapseBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    console.log('Click event triggered');
                    window.toggleSidebar();
                });
            } else {
                console.error('Collapse button not found during DOMContentLoaded');
            }
        });
    </script>
    <script src="/static/chat.js"></script>
</body>
</html>"""
