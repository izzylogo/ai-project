const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');

// API Configuration - Replace with your backend URL
const API_BASE_URL = 'http://localhost:8000'; // Change this to your backend URL

function autoResize(element) {
    element.style.height = 'auto';
    element.style.height = Math.min(element.scrollHeight, 300) + 'px';
}

userInput.addEventListener('input', function() {
    autoResize(this);
    updateButtonState();
});

userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function updateButtonState() {
    const hasText = userInput.value.trim().length > 0;
    sendButton.style.opacity = hasText ? '1' : '0.4';
}

function addMessage(sender, content, type = 'user') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    if (type === 'loading') {
        messageDiv.innerHTML = `
            <div class="message-header">AI Trip Assistant</div>
            <div class="message-content">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                Planning your perfect trip...
            </div>
        `;
    } else {
        const header = type === 'ai' ? 'AI Trip Assistant' : 'You';
        const processedContent = type === 'ai' ? marked.parse(content) : content;
        
        messageDiv.innerHTML = `
            <div class="message-header">${header}</div>
            <div class="message-content">${processedContent}</div>
        `;
    }
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return messageDiv;
}

function disableInput(disabled) {
    userInput.disabled = disabled;
    sendButton.disabled = disabled;
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Add user message
    addMessage('You', message, 'user');
    
    // Clear input and disable controls
    userInput.value = '';
    autoResize(userInput);
    disableInput(true);
    
    // Add loading message
    const loadingMessage = addMessage('', '', 'loading');

    try {
        // Make API call to your backend
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: message 
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Remove loading message
        chatContainer.removeChild(loadingMessage);

        if (Array.isArray(data.reply)) {
            // If flight details are returned, display them
            data.reply.forEach(flight => {
                addMessage('AI', `Flight: ${flight.airline} | ${flight.route} | Price: $${flight.price}`, 'ai');
            });
        } else {
            // Display AI reply (non-flight related)
            addMessage('AI', data.reply || 'I apologize, but I encountered an issue. Please try again.', 'ai');
        }
        
    } catch (error) {
        console.error('Error:', error);
        
        // Remove loading message
        chatContainer.removeChild(loadingMessage);
        
        // Add error message
        addMessage('AI', '🔧 I\'m having trouble connecting to my travel database right now. Please check that the backend server is running and try again!', 'ai');
    } finally {
        // Re-enable input
        disableInput(false);
        userInput.focus();
        updateButtonState();
    }
}

// Initialize
autoResize(userInput);
updateButtonState();
userInput.focus();
