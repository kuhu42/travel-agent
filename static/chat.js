let conversationId = null;
let currentContext = {};
let currentMessageDiv = null;
let currentContentDiv = null;
let isStreaming = false;

function add(role, text = "", results = null, reasoning = null) {
  const chat = document.getElementById("chat");
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${role}`;
  
  const label = document.createElement("div");
  label.className = "message-label";
  label.innerText = role === "user" ? "You" : "Travel Agent";
  messageDiv.appendChild(label);
  
  const content = document.createElement("div");
  content.className = "message-content";
  if (text) {
    content.innerText = text;
  }
  messageDiv.appendChild(content);
  
  if (reasoning) {
    const reasoningDiv = document.createElement("div");
    reasoningDiv.className = "reasoning";
    reasoningDiv.innerText = `💭 ${reasoning}`;
    content.appendChild(reasoningDiv);
  }
  
  if (results && results.length > 0) {
    results.forEach(result => {
      const resultSection = document.createElement("div");
      resultSection.className = "result-section";
      
      const toolHeader = document.createElement("div");
      toolHeader.className = "tool-header";
      toolHeader.innerHTML = `<strong>🔧 ${result.tool}</strong>`;
      if (result.message) {
        toolHeader.innerHTML += ` - ${result.message}`;
      }
      resultSection.appendChild(toolHeader);
      
      if (result.error) {
        const errorDiv = document.createElement("div");
        errorDiv.className = "error-box";
        errorDiv.innerText = `Error: ${result.error}`;
        resultSection.appendChild(errorDiv);
      } else if (result.data) {
        const dataDiv = document.createElement("div");
        dataDiv.className = "result-box";
        
        if (Array.isArray(result.data)) {
          dataDiv.innerHTML = result.data.map(item => {
            if (typeof item === 'object') {
              return `<div class="result-item">${formatObject(item)}</div>`;
            }
            return `<div class="result-item">${item}</div>`;
          }).join('');
        } else {
          dataDiv.innerText = JSON.stringify(result.data, null, 2);
        }
        
        resultSection.appendChild(dataDiv);
      }
      
      content.appendChild(resultSection);
    });
  }
  
  chat.appendChild(messageDiv);
  chat.scrollTop = chat.scrollHeight;
  
  return { messageDiv, content };
}

function addStatusMessage(status) {
  if (!currentMessageDiv) return;
  
  let statusDiv = currentMessageDiv.querySelector('.status-indicator');
  if (!statusDiv) {
    statusDiv = document.createElement("div");
    statusDiv.className = "status-indicator";
    currentMessageDiv.appendChild(statusDiv);
  }
  
  statusDiv.innerHTML = `<span class="status-dot"></span> ${status}`;
}

function removeStatusMessage() {
  if (!currentMessageDiv) return;
  const statusDiv = currentMessageDiv.querySelector('.status-indicator');
  if (statusDiv) {
    statusDiv.remove();
  }
}

function addReasoning(reasoning) {
  if (!currentContentDiv) return;
  
  const reasoningDiv = document.createElement("div");
  reasoningDiv.className = "reasoning";
  reasoningDiv.innerText = `💭 ${reasoning}`;
  currentContentDiv.appendChild(reasoningDiv);
}

function addToolResult(toolResult) {
  if (!currentContentDiv) return;
  
  const resultSection = document.createElement("div");
  resultSection.className = "result-section";
  
  const toolHeader = document.createElement("div");
  toolHeader.className = "tool-header";
  toolHeader.innerHTML = `<strong>🔧 ${toolResult.tool}</strong>`;
  resultSection.appendChild(toolHeader);
  
  if (toolResult.result.error) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "error-box";
    errorDiv.innerText = `Error: ${toolResult.result.error}`;
    resultSection.appendChild(errorDiv);
  } else if (toolResult.result.data) {
    const dataDiv = document.createElement("div");
    dataDiv.className = "result-box";
    const data = toolResult.result.data;
    
    if (Array.isArray(data)) {
      dataDiv.innerHTML = data.map(item => {
        if (typeof item === 'object') {
          return `<div class="result-item">${formatObject(item)}</div>`;
        }
        return `<div class="result-item">${item}</div>`;
      }).join('');
    } else {
      dataDiv.innerText = JSON.stringify(data, null, 2);
    }
    
    resultSection.appendChild(dataDiv);
  }
  
  currentContentDiv.appendChild(resultSection);
  
  // Auto-scroll
  const chat = document.getElementById("chat");
  chat.scrollTop = chat.scrollHeight;
}

function formatObject(obj) {
  if (obj.airline) {
    let route = '';
    if (obj.from && obj.to) {
      route = `${obj.from} → ${obj.to} | `;
    }
    return `<strong>${obj.airline}</strong> - ${route}₹${obj.price} | ${obj.stops} stop(s) | ${obj.duration || ''}`;
  } else if (obj.name && obj.price_per_night) {
    return `<strong>${obj.name}</strong> - ₹${obj.price_per_night}/night | ⭐ ${obj.rating || 'N/A'}`;
  } else if (obj.name && obj.cuisine) {
    return `<strong>${obj.name}</strong> - ${obj.cuisine} | ${obj.price_range || ''} | ⭐ ${obj.rating || ''}`;
  } else {
    return Object.entries(obj)
      .map(([key, val]) => `${key}: ${val}`)
      .join(' | ');
  }
}

async function sendStreaming() {
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const message = input.value.trim();
  
  if (!message || isStreaming) return;
  
  console.log("[SSE] Starting stream for:", message);
  
  // Disable input
  isStreaming = true;
  input.disabled = true;
  sendBtn.disabled = true;
  sendBtn.innerHTML = '<span class="loading"></span>';
  
  // Add user message
  add("user", message);
  input.value = "";
  
  // Create agent message placeholder
  const { messageDiv, content } = add("agent", "");
  currentMessageDiv = messageDiv;
  currentContentDiv = content;
  
  // Create a text node for streaming text
  const textNode = document.createTextNode("");
  currentContentDiv.appendChild(textNode);
  
  try {
    console.log("[SSE] Fetching /chat/stream...");
    
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId
      })
    });
    
    console.log("[SSE] Response status:", response.status);
    console.log("[SSE] Response headers:", Object.fromEntries(response.headers.entries()));
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    if (!response.body) {
      throw new Error("Response body is null");
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let messageText = "";
    let eventCount = 0;
    
    console.log("[SSE] Starting to read stream...");
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        console.log("[SSE] Stream complete. Total events:", eventCount);
        break;
      }
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          eventCount++;
          const dataStr = line.slice(6);
          console.log(`[SSE] Event ${eventCount}:`, dataStr.substring(0, 100));
          
          try {
            const data = JSON.parse(dataStr);
            
            switch (data.type) {
              case 'conversation_id':
                console.log("[SSE] Got conversation ID:", data.conversation_id);
                conversationId = data.conversation_id;
                break;
              
              case 'context':
              case 'context_updated':
                console.log("[SSE] Context update:", data.context);
                currentContext = data.context;
                break;
              
              case 'status':
                console.log("[SSE] Status:", data.status);
                addStatusMessage(data.status);
                break;
              
              case 'reasoning':
                console.log("[SSE] Reasoning:", data.reasoning);
                removeStatusMessage();
                addReasoning(data.reasoning);
                break;
              
              case 'message_chunk':
                removeStatusMessage();
                messageText += data.chunk;
                textNode.textContent = messageText;
                // Auto-scroll
                const chat = document.getElementById("chat");
                chat.scrollTop = chat.scrollHeight;
                break;
              
              case 'tool_result':
                console.log("[SSE] Tool result:", data.tool);
                removeStatusMessage();
                addToolResult(data);
                break;
              
              case 'complete':
                console.log("[SSE] Complete:", data.response);
                removeStatusMessage();
                break;
              
              case 'error':
                console.error("[SSE] Error:", data.error);
                removeStatusMessage();
                textNode.textContent = `Error: ${data.error}`;
                textNode.style.color = "red";
                break;
              
              default:
                console.log("[SSE] Unknown event type:", data.type);
            }
          } catch (e) {
            console.error("[SSE] Failed to parse event data:", e);
          }
        }
      }
    }
    
    console.log("[SSE] Stream processing complete");
    
  } catch (error) {
    console.error("[SSE] Stream error:", error);
    removeStatusMessage();
    currentContentDiv.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
  } finally {
    // Re-enable input
    isStreaming = false;
    input.disabled = false;
    sendBtn.disabled = false;
    sendBtn.innerText = "Send";
    input.focus();
    currentMessageDiv = null;
    currentContentDiv = null;
  }
}

async function send() {
  return sendStreaming();
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

// Initialize
window.addEventListener('load', () => {
  console.log("[SSE] Page loaded, ready for streaming");
  add("agent", "Hello! I'm your travel planning assistant. I can help you find flights, hotels, and restaurant recommendations. Where would you like to go?");
});