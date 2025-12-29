let conversationId = null;
let currentContext = {};

function add(role, text, results = null, reasoning = null) {
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
  
  // Add reasoning if present
  if (reasoning) {
    const reasoningDiv = document.createElement("div");
    reasoningDiv.className = "reasoning";
    reasoningDiv.innerText = `💭 ${reasoning}`;
    content.appendChild(reasoningDiv);
  }
  
  // Add results if present (MULTIPLE TOOL RESULTS)
  if (results && results.length > 0) {
    results.forEach(result => {
      const resultSection = document.createElement("div");
      resultSection.className = "result-section";
      
      // Tool header
      const toolHeader = document.createElement("div");
      toolHeader.className = "tool-header";
      toolHeader.innerHTML = `<strong>🔧 ${result.tool}</strong>`;
      if (result.message) {
        toolHeader.innerHTML += ` - ${result.message}`;
      }
      resultSection.appendChild(toolHeader);
      
      // Tool data
      if (result.error) {
        const errorDiv = document.createElement("div");
        errorDiv.className = "error-box";
        errorDiv.innerText = `Error: ${result.error}`;
        resultSection.appendChild(errorDiv);
      } else if (result.data) {
        const dataDiv = document.createElement("div");
        dataDiv.className = "result-box";
        
        if (Array.isArray(result.data)) {
          // Format array of objects nicely
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
}

function formatObject(obj) {
  // Pretty format objects (flights, hotels, restaurants)
  if (obj.airline) {
    // Flight
    let route = '';
    if (obj.from && obj.to) {
      route = `${obj.from} → ${obj.to} | `;
    }
    return `<strong>${obj.airline}</strong> - ${route}₹${obj.price} | ${obj.stops} stop(s) | ${obj.duration || ''}`;
  } else if (obj.name && obj.price_per_night) {
    // Hotel
    return `<strong>${obj.name}</strong> - ₹${obj.price_per_night}/night | ⭐ ${obj.rating || 'N/A'}`;
  } else if (obj.name && obj.cuisine) {
    // Restaurant
    return `<strong>${obj.name}</strong> - ${obj.cuisine} | ${obj.price_range || ''} | ⭐ ${obj.rating || ''}`;
  } else {
    // Generic object
    return Object.entries(obj)
      .map(([key, val]) => `${key}: ${val}`)
      .join(' | ');
  }
}

async function send() {
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const message = input.value.trim();
  
  if (!message) return;
  
  // Disable input
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
    const results = data.reply.results;  // Array of tool results
    const reasoning = data.reply.reasoning;
    
    add("agent", reply, results, reasoning);
    
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

// Initialize
window.addEventListener('load', () => {
  add("agent", "Hello! I'm your travel planning assistant. I can help you find flights, hotels, and restaurant recommendations. Where would you like to go?");
});