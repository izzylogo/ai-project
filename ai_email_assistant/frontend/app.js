const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendButton = document.querySelector('button');

async function sendMessage() {
  const message = userInput.value.trim();
  if (!message) return;

  addMessage('You', message, 'user');
  userInput.value = '';
  disableInput(true);

  const aiBubble = addLoadingBubble();

  try {
    const response = await fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    const data = await response.json();
    typeWriter(aiBubble, data.reply, () => {
      disableInput(false);
      userInput.focus();
      playReplySound();
    });
  } catch (err) {
    updateMessage(aiBubble, '❌ Could not reach the server.');
    disableInput(false);
    userInput.focus();
  }
}

function disableInput(state) {
  userInput.disabled = state;
  sendButton.disabled = state;
}

function addMessage(sender, text, type) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${type}`;
  if (sender === 'AI') {
    msgDiv.innerHTML = `<strong>AI:</strong> ` + marked.parse(text);
  } else {
    msgDiv.innerHTML = `<strong>${sender}:</strong> ${text}`;
  }
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
  return msgDiv;
}

function addLoadingBubble() {
  const msgDiv = document.createElement('div');
  msgDiv.className = 'message ai loader';
  msgDiv.innerHTML = `<strong>AI:</strong> <span class="dots"><span>.</span><span>.</span><span>.</span></span>`;
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
  return msgDiv;
}

function updateMessage(element, newText) {
  element.innerHTML = `<strong>AI:</strong> ` + marked.parse(newText);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function typeWriter(element, text, callback, i = 0) {
  const base = `<strong>AI:</strong> `;
  const htmlContent = marked.parse(text);

  if (i < htmlContent.length) {
    element.innerHTML = base + htmlContent.substring(0, i + 3);
    chatBox.scrollTop = chatBox.scrollHeight;
    setTimeout(() => typeWriter(element, text, callback, i + 3), 70);
  } else {
    element.innerHTML = base + htmlContent;
    chatBox.scrollTop = chatBox.scrollHeight;
    if (callback) callback();
  }
}

function playReplySound() {
  const audio = new Audio("https://freesound.org/data/previews/341/341695_5260876-lq.mp3");
  audio.play();
}

// ✅ Enter key to send
userInput.addEventListener('keypress', function (e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    sendMessage();
  }
});
