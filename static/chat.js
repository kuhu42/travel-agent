let conversationId = null;
let currentContext = {};

function add(role, text, result = null, reasoning = null) {
  const chat = document.getElementById("chat");
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  
  const label = document.createElement("div");
  label.className = "message-label";
  label.innerText = role === "user" ? "You" : "Travel Agent";
  messageDiv.appendChild(label);
  
  const content = document.createElement("div");
  content.className = "message-content";
  content.innerText = text;
  messageDiv.appendChild(content);
  
  // Add reasoning if present (for debugging/transparency)
  if (reasoning) {
    const reasoningDiv = document.createElement("div");
    reasoningDiv.className = "reasoning";
    reasoningDiv.innerText = `💭 ${reasoning}`;
    content.appendChild(reasoningDiv);
  }
  
  // Add result if present
  if (result) {
    const resultDiv = document.createElement("div");
    resultDiv.className = "result-box";
    
    if (Array.isArray(result)) {
      resultDiv.innerHTML = result.map(item => 
        typeof item === 'object' 
          ? `<div>${JSON.stringify(item, null, 2)}</div>` 
          : `<div>${item}</div>`
      ).join('<br>');
    } else {
      resultDiv.innerText = JSON.stringify(result, null, 2);
    }
    
    content.appendChild(resultDiv);
  }
  
  chat.appendChild(messageDiv);
  chat.scrollTop = chat.scrollHeight;
}

async function send() {
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const message = input.value.trim();
  
  if (!message) return;
  
  // Disable input while processing
  input.disabled = true;
  sendBtn.disabled = true;
  sendBtn.innerHTML = '<span class="loading"></span>';
  
  add("user", message);
  input.value = "";
  
  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        message,
        conversation_id: conversationId
      })
    });
    
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    
    const data = await res.json();
    conversationId = data.conversation_id;
    currentContext = data.context;
    
    const reply = data.reply.message;
    const result = data.reply.result;
    const reasoning = data.reply.reasoning;
    
    add("agent", reply, result, reasoning);
    
  } catch (error) {
    add("agent", `Sorry, I encountered an error: ${error.message}`);
    console.error("Error:", error);
  } finally {
    // Re-enable input
    input.disabled = false;
    sendBtn.disabled = false;
    sendBtn.innerText = "Send";
    input.focus();
  }
}

function showContext() {
  const modal = document.getElementById("contextModal");
  const display = document.getElementById("contextDisplay");
  
  display.innerText = JSON.stringify(currentContext, null, 2);
  modal.style.display = "flex";
}

function hideContext() {
  const modal = document.getElementById("contextModal");
  modal.style.display = "none";
}

// Initialize with a greeting
window.addEventListener('load', () => {
  add("agent", "Hello! I'm your travel planning assistant. I can help you find flights, hotels, and restaurant recommendations. Where would you like to go?");
});