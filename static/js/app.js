// Establish socket connection
const socket = io();

// UI elements cache
const chatHistory = document.getElementById('chat-history');
const timelineLog = document.getElementById('timeline-log');
const timelineBody = document.getElementById('timeline-body');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const timelineHeaderBtn = document.getElementById('timeline-header-btn');
const voiceToggleBtn = document.getElementById('voice-toggle-btn');
const voiceBtnText = document.getElementById('voice-btn-text');
const screenshotBtn = document.getElementById('screenshot-btn');
const screenshotModal = document.getElementById('screenshot-modal');
const screenshotImg = document.getElementById('screenshot-img');
const closeModalBtn = document.getElementById('close-modal-btn');

// State control variables
let activeSessionId = "session_" + Math.random().toString(36).substring(2, 9);
let currentStepNode = null;
let currentTimelineStep = 0;

// Initialize layout elements
timelineHeaderBtn.addEventListener('click', () => {
    timelineLog.classList.toggle('collapsed');
});

// Update system metric gauges
function updateSystemGauges() {
    fetch('/api/system/status')
        .then(res => res.json())
        .then(data => {
            if (data.error) return;
            
            // Set labels
            document.getElementById('cpu-value').innerText = `${Math.round(data.cpu)}%`;
            document.getElementById('ram-value').innerText = `${Math.round(data.ram)}%`;
            document.getElementById('battery-txt').innerText = `${data.battery}% (${data.power_plugged ? "Plugged" : "Battery"})`;
            document.getElementById('os-txt').innerText = data.os;
            document.getElementById('user-txt').innerText = data.user;
            
            // Adjust SVG paths (circumference 2 * PI * r = 2 * 3.14159 * 40 = 251.2)
            const circumference = 251.2;
            
            const cpuFill = document.querySelector('.cpu-fill');
            const cpuOffset = circumference - (data.cpu / 100) * circumference;
            cpuFill.style.strokeDashoffset = cpuOffset;
            
            const ramFill = document.querySelector('.ram-fill');
            const ramOffset = circumference - (data.ram / 100) * circumference;
            ramFill.style.strokeDashoffset = ramOffset;
            
            // Adjust battery fill color
            const batteryFill = document.getElementById('battery-fill');
            batteryFill.style.width = `${data.battery}%`;
            if (data.battery < 20) {
                batteryFill.style.background = 'var(--neon-pink)';
            } else {
                batteryFill.style.background = 'linear-gradient(90deg, var(--neon-cyan), var(--neon-blue))';
            }
        })
        .catch(err => console.error("Error reading system metrics: ", err));
}
setInterval(updateSystemGauges, 5000);
updateSystemGauges(); // First load

// Appending chat bubbles
function appendChatBubble(sender, text) {
    const bubble = document.createElement('div');
    
    const content = document.createElement('div');
    content.className = 'bubble-content';
    
    if (sender === 'agent') {
        bubble.className = 'chat-bubble agent agent-reply';
        bubble.style.position = 'relative';
        if (typeof marked !== 'undefined') {
            content.innerHTML = marked.parse(text || "");
        } else {
            content.innerHTML = text.replace(/\n/g, '<br/>');
        }
        
        // Add floating copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-msg-btn';
        copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
        copyBtn.title = "Copy response";
        copyBtn.style.cssText = "position: absolute; bottom: 8px; right: 8px; background: none; border: none; color: rgba(255,255,255,0.4); cursor: pointer; font-size: 13px; transition: color 0.2s; padding: 4px;";
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(text);
            copyBtn.innerHTML = '<i class="fa-solid fa-check" style="color: #00ff80;"></i>';
            setTimeout(() => {
                copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
            }, 2000);
        };
        bubble.appendChild(copyBtn);
    } else {
        bubble.className = 'chat-bubble user';
        content.innerHTML = text.replace(/\n/g, '<br/>');
    }
    
    bubble.appendChild(content);
    chatHistory.appendChild(bubble);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Render typing state
function showTypingIndicator() {
    const loader = document.createElement('div');
    loader.id = 'typing-indicator';
    loader.className = 'typing-dots chat-bubble agent';
    loader.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;
    chatHistory.appendChild(loader);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function removeTypingIndicator() {
    const loader = document.getElementById('typing-indicator');
    if (loader) {
        loader.remove();
    }
}

// Send input prompts
function sendCommand(prompt) {
    if (!prompt.trim()) return;
    
    // Add user bubble
    appendChatBubble('user', prompt);
    showTypingIndicator();
    
    // Expand timeline and clear old runs
    timelineLog.classList.remove('collapsed');
    timelineBody.innerHTML = '';
    currentTimelineStep = 0;
    
    // Send to WebSocket
    socket.emit('user_message', {
        message: prompt,
        session_id: activeSessionId
    });
    
    chatInput.value = '';
}

sendBtn.addEventListener('click', () => {
    sendCommand(chatInput.value);
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        sendCommand(chatInput.value);
    }
});

// Bind quick actions shortcuts
function sendQuickCommand(prompt) {
    sendCommand(prompt);
}

// WebSocket Event Listeners
socket.on('connection_response', (data) => {
    console.log("WebSocket Established: ", data.message);
});

socket.on('react_update', (update) => {
    if (update.session_id && update.session_id !== activeSessionId) return;
    const type = update.type;
    
    if (type === 'thought_start') {
        currentTimelineStep = update.step;
    } 
    else if (type === 'thought') {
        const node = document.createElement('div');
        node.className = 'step-node step-thought';
        node.innerHTML = `
            <div class="step-title step-thought">Step ${currentTimelineStep}: Thought</div>
            <div class="step-content">${update.content}</div>
        `;
        timelineBody.appendChild(node);
        timelineBody.scrollTop = timelineBody.scrollHeight;
    } 
    else if (type === 'tool_call') {
        const node = document.createElement('div');
        node.className = 'step-node step-tool';
        node.innerHTML = `
            <div class="step-title step-tool">Running Skill Action: ${update.tool}</div>
            <div class="step-code-block">${JSON.stringify(update.args, null, 2)}</div>
        `;
        timelineBody.appendChild(node);
        timelineBody.scrollTop = timelineBody.scrollHeight;
    } 
    else if (type === 'tool_result') {
        const node = document.createElement('div');
        node.className = 'step-node step-observation';
        node.innerHTML = `
            <div class="step-title step-observation">Observation Output: ${update.tool}</div>
            <div class="step-code-block">${update.result}</div>
        `;
        timelineBody.appendChild(node);
        timelineBody.scrollTop = timelineBody.scrollHeight;
    } 
    else if (type === 'final_answer') {
        removeTypingIndicator();
        appendChatBubble('agent', update.content);
        // Collapse timeline on complete
        setTimeout(() => {
            timelineLog.classList.add('collapsed');
        }, 3000);
    } 
    else if (type === 'error') {
        removeTypingIndicator();
        appendChatBubble('agent', `❌ Error: ${update.message}`);
    }
});

// Take desktop screenshot manually
screenshotBtn.addEventListener('click', () => {
    screenshotBtn.disabled = true;
    screenshotBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Capturing...</span>';
    
    fetch('/api/screenshot/trigger', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            // Load image with cache buster query parameter to force reload
            screenshotImg.src = `/static/assets/screenshot.png?t=${Date.now()}`;
            screenshotModal.classList.remove('hidden');
        })
        .catch(err => {
            alert("Screenshot capture failed: " + err);
        })
        .finally(() => {
            screenshotBtn.disabled = false;
            screenshotBtn.innerHTML = '<i class="fa-solid fa-camera text-purple"></i><span>Screenshot</span>';
        });
});

// Close modal handlers
closeModalBtn.addEventListener('click', () => {
    screenshotModal.classList.add('hidden');
});

window.addEventListener('click', (e) => {
    if (e.target === screenshotModal) {
        screenshotModal.classList.add('hidden');
    }
});

// Toggle background voice wake word thread
voiceToggleBtn.addEventListener('click', () => {
    const isInactive = voiceToggleBtn.classList.contains('btn-inactive');
    
    voiceToggleBtn.disabled = true;
    voiceToggleBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Toggling...</span>';
    
    fetch('/api/voice/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable: isInactive })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'active') {
            voiceToggleBtn.className = 'glass-btn btn-active';
            voiceToggleBtn.innerHTML = '<i class="fa-solid fa-microphone"></i><span id="voice-btn-text">Voice Listener: ON</span>';
        } else {
            voiceToggleBtn.className = 'glass-btn btn-inactive';
            voiceToggleBtn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i><span id="voice-btn-text">Voice Listener: OFF</span>';
        }
    })
    .catch(err => console.error("Failed to toggle background voice pipeline:", err))
    .finally(() => {
        voiceToggleBtn.disabled = false;
    });
});

// Check Voice status on startup
fetch('/api/voice/status')
    .then(res => res.json())
    .then(data => {
        if (data.status === 'active') {
            voiceToggleBtn.className = 'glass-btn btn-active';
            voiceToggleBtn.innerHTML = '<i class="fa-solid fa-microphone"></i><span id="voice-btn-text">Voice Listener: ON</span>';
        } else {
            voiceToggleBtn.className = 'glass-btn btn-inactive';
            voiceToggleBtn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i><span id="voice-btn-text">Voice Listener: OFF</span>';
        }
    });

// Bind Speech recognition to input
const dictation = new BrowserVoiceSTT('chat-input', 'mic-record-btn', (text) => {
    // Automatically submit message after 1.5 seconds of voice pause
    setTimeout(() => {
        if (chatInput.value === text) {
            sendCommand(text);
        }
    }, 1500);
});
