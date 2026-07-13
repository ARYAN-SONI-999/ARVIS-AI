/* ==========================================================================
   ARVIS FUTURISTIC LANDING PAGE JS (HUD LOGIC & LIVE SOCKET CONNECTION)
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialise particles constellation background
    initParticlesCanvas();

    // 2. Boot sequence simulation
    runBootSequence();

    // 3. Setup typewriter subtitles
    initTypewriter();

    // 4. Setup scroll reveal bindings
    initScrollReveal();

    // 5. Connect Socket.IO for the live HUD chat console
    initLiveConsole();
});

/* ── 1. NEURAL PARTICLE CONSTELLATION CANVAS ───────────────────────────────── */
function initParticlesCanvas() {
    const canvas = document.getElementById("particles-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const particles = [];
    const maxParticles = 65;
    const connectionDist = 120;
    
    // Mouse interaction parameters
    let mouse = { x: null, y: null, radius: 150 };
    window.addEventListener("mousemove", (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });
    window.addEventListener("mouseleave", () => {
        mouse.x = null;
        mouse.y = null;
    });

    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.4;
            this.vy = (Math.random() - 0.5) * 0.4;
            this.radius = Math.random() * 1.5 + 0.5;
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            // Repel from mouse cursor
            if (mouse.x !== null && mouse.y !== null) {
                const dx = this.x - mouse.x;
                const dy = this.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < mouse.radius) {
                    const force = (mouse.radius - dist) / mouse.radius;
                    // Push particles away gently
                    this.x += (dx / dist) * force * 1.5;
                    this.y += (dy / dist) * force * 1.5;
                }
            }

            // Bounce off edges
            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = "rgba(0, 229, 255, 0.4)";
            ctx.fill();
        }
    }

    // Populate particles
    for (let i = 0; i < maxParticles; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);

        // Draw connections
        for (let i = 0; i < particles.length; i++) {
            const p1 = particles[i];
            p1.update();
            p1.draw();

            for (let j = i + 1; j < particles.length; j++) {
                const p2 = particles[j];
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < connectionDist) {
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    const alpha = (1 - dist / connectionDist) * 0.12;
                    ctx.strokeStyle = `rgba(123, 97, 255, ${alpha})`;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }
        }
        requestAnimationFrame(animate);
    }

    animate();

    window.addEventListener("resize", () => {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    });
}

/* ── 2. SIMULATED SYSTEM BOOT SEQUENCE ─────────────────────────────────────── */
function runBootSequence() {
    const bootContainer = document.getElementById("boot-sequence");
    const terminal = document.querySelector(".boot-terminal");
    if (!bootContainer || !terminal) return;

    const lines = [
        "[SYSTEM]: Initializing ARVIS Neural Subnetworks...",
        "[COGNITIVE]: Loading ReAct Agent Loop Framework...",
        "[DATABASE]: Initializing sqlite connections...",
        "[MEMORY]: Migration complete. Embedding columns verified.",
        "[HARDWARE]: Calibrating PyAudioWPatch sound adapters...",
        "[SOUND]: Winsound interactive chimes bound and ready.",
        "[SKILLS]: System control, Weather, Scraper, and Vision mounted.",
        "[AGENT]: Status: ALL SYSTEMS ACTIVE."
    ];

    let delay = 0;
    lines.forEach((line, index) => {
        setTimeout(() => {
            const el = document.createElement("div");
            el.className = "boot-line";
            el.innerText = line;
            terminal.appendChild(el);
        }, delay);
        delay += 350;
    });

    // Fade out boot overlay and display home page
    setTimeout(() => {
        bootContainer.style.opacity = 0;
        setTimeout(() => {
            bootContainer.style.display = "none";
        }, 800);
    }, delay + 1000);
}

/* ── 3. TYPEWRITER TERMINAL EFFECT ────────────────────────────────────────── */
function initTypewriter() {
    const typewriter = document.getElementById("typewriter");
    if (!typewriter) return;

    const sentences = [
        "I am ARVIS, a Windows-based agentic AI assistant.",
        "I can browse and read web URLs directly.",
        "I can analyze your desktop screen using vision.",
        "I can execute Python and render Matplotlib charts.",
        "I can delegate work to specialized sub-agents."
    ];

    let sentenceIndex = 0;
    let charIndex = 0;
    let isDeleting = false;

    function tick() {
        const currentSentence = sentences[sentenceIndex];

        if (isDeleting) {
            typewriter.innerText = currentSentence.substring(0, charIndex - 1);
            charIndex--;
        } else {
            typewriter.innerText = currentSentence.substring(0, charIndex + 1);
            charIndex++;
        }

        let speed = isDeleting ? 30 : 60;

        if (!isDeleting && charIndex === currentSentence.length) {
            isDeleting = true;
            speed = 2000; // Pause at end of sentence
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            sentenceIndex = (sentenceIndex + 1) % sentences.length;
            speed = 500; // Pause before typing next
        }

        setTimeout(tick, speed);
    }

    tick();
}

/* ── 4. SCROLL REVEAL BINDINGS ─────────────────────────────────────────────── */
function initScrollReveal() {
    const reveals = document.querySelectorAll(".scroll-reveal");

    function checkReveal() {
        reveals.forEach((el) => {
            const rect = el.getBoundingClientRect();
            const triggerOffset = window.innerHeight * 0.85;
            if (rect.top < triggerOffset) {
                el.classList.add("reveal-active");
            }
        });
    }

    window.addEventListener("scroll", checkReveal);
    checkReveal(); // Trigger once on load
}

/* ── 5. LIVE HUD CHAT DEMO CONSOLE ─────────────────────────────────────────── */
function initLiveConsole() {
    const consoleOutput = document.getElementById("console-output");
    const consoleInput = document.getElementById("console-input");
    const consoleSend = document.getElementById("console-send");

    if (!consoleOutput || !consoleInput) return;

    // Establish WebSocket and session parameters
    const socket = io();
    const activeSessionId = "landing_" + Math.random().toString(36).substring(2, 9);

    // Scroll output terminal to bottom helper
    function scrollToBottom() {
        setTimeout(() => {
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }, 50);
    }

    // Typing Indicators for futuristic loader HUD
    function showTypingIndicator() {
        const loader = document.createElement('div');
        loader.id = 'landing-typing-indicator';
        loader.className = 'console-bubble agent';
        loader.innerHTML = `
            <div style="display: flex; gap: 4px; align-items: center; justify-content: center; height: 16px;">
                <span class="pill-dot" style="animation: pulse 1s infinite alternate; background-color: var(--accent-primary); width: 6px; height: 6px; border-radius: 50%;"></span>
                <span class="pill-dot" style="animation: pulse 1s infinite alternate; animation-delay: 0.2s; background-color: var(--accent-primary); width: 6px; height: 6px; border-radius: 50%;"></span>
                <span class="pill-dot" style="animation: pulse 1s infinite alternate; animation-delay: 0.4s; background-color: var(--accent-primary); width: 6px; height: 6px; border-radius: 50%;"></span>
            </div>
        `;
        consoleOutput.appendChild(loader);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const loader = document.getElementById('landing-typing-indicator');
        if (loader) {
            loader.remove();
        }
    }

    const timelineLog = document.getElementById("timeline-log");
    const timelineHeaderBtn = document.getElementById("timeline-header-btn");
    const timelineBody = document.getElementById("timeline-body");
    let currentTimelineStep = 0;

    if (timelineHeaderBtn && timelineLog) {
        timelineHeaderBtn.addEventListener("click", () => {
            timelineLog.classList.toggle("collapsed");
        });
    }

    // Socket.IO event listeners
    socket.on("connect", () => {
        console.log("🔌 Connected to ARVIS Live Stream.");
    });

    socket.on("react_update", (update) => {
        const type = update.type;
        
        if (type === "thought_start") {
            currentTimelineStep = update.step;
            if (update.step === 1 && timelineBody) {
                timelineBody.innerHTML = '';
            }
            if (timelineLog) {
                timelineLog.classList.remove("collapsed");
            }
        }
        else if (type === "thought") {
            if (timelineBody) {
                const node = document.createElement('div');
                node.className = 'step-node step-thought';
                node.innerHTML = `
                    <div class="step-title step-thought">Step ${currentTimelineStep}: Thought</div>
                    <div class="step-content">${update.content}</div>
                `;
                timelineBody.appendChild(node);
                timelineBody.scrollTop = timelineBody.scrollHeight;
            }
        }
        else if (type === "tool_call") {
            if (timelineBody) {
                const node = document.createElement('div');
                node.className = 'step-node step-tool';
                node.innerHTML = `
                    <div class="step-title step-tool">Running Skill Action: ${update.tool}</div>
                    <div class="step-code-block">${JSON.stringify(update.args, null, 2)}</div>
                `;
                timelineBody.appendChild(node);
                timelineBody.scrollTop = timelineBody.scrollHeight;
            }
        }
        else if (type === "tool_result") {
            if (timelineBody) {
                const node = document.createElement('div');
                node.className = 'step-node step-observation';
                node.innerHTML = `
                    <div class="step-title step-observation">Observation Output: ${update.tool}</div>
                    <div class="step-content">${update.result || ""}</div>
                `;
                timelineBody.appendChild(node);
                timelineBody.scrollTop = timelineBody.scrollHeight;
            }
        }
        else if (type === "final_answer") {
            removeTypingIndicator();
            if (timelineLog) {
                timelineLog.classList.add("collapsed");
            }

            const el = document.createElement("div");
            el.className = "console-bubble agent";
            consoleOutput.appendChild(el);
            scrollToBottom();

            // Type html content character by character to simulate generative streaming
            const htmlString = marked.parse(update.content);
            let currentHtml = "";
            let i = 0;
            const interval = setInterval(() => {
                if (i >= htmlString.length) {
                    el.innerHTML = htmlString;
                    clearInterval(interval);
                    scrollToBottom();
                    return;
                }
                
                // Keep HTML tags intact without splitting them
                if (htmlString[i] === '<') {
                    const closingIndex = htmlString.indexOf('>', i);
                    if (closingIndex !== -1) {
                        currentHtml += htmlString.substring(i, closingIndex + 1);
                        i = closingIndex + 1;
                    } else {
                        currentHtml += htmlString[i];
                        i++;
                    }
                } else {
                    currentHtml += htmlString[i];
                    i++;
                }
                
                el.innerHTML = currentHtml;
                scrollToBottom();
            }, 8);
        }
        else if (type === "error") {
            removeTypingIndicator();
            if (timelineLog) {
                timelineLog.classList.add("collapsed");
            }
            
            const el = document.createElement("div");
            el.className = "console-bubble agent";
            el.style.borderColor = "var(--alert-danger)";
            el.innerHTML = `<span style="color: var(--alert-danger)">❌ Error: ${update.message}</span>`;
            consoleOutput.appendChild(el);
            scrollToBottom();
        }
    });

    // Send command helper
    function sendCommand(text) {
        if (!text.trim()) return;

        // Display user query in console
        const userBubble = document.createElement("div");
        userBubble.className = "console-bubble user";
        userBubble.innerText = text;
        consoleOutput.appendChild(userBubble);
        
        // Show loader
        showTypingIndicator();
        scrollToBottom();

        // Clear active steps container for the next run
        activeStepContainer = null;

        // Emit command to SocketIO backend
        socket.emit("user_message", { 
            message: text,
            session_id: activeSessionId 
        });

        // Reset input box
        consoleInput.value = "";
    }

    // Event bindings for send
    consoleSend.addEventListener("click", () => {
        sendCommand(consoleInput.value);
    });

    consoleInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            sendCommand(consoleInput.value);
        }
    });

    // Bind preset HUD action buttons
    window.sendPreset = function(text) {
        sendCommand(text);
    };
}

// Custom Cursor tracking
document.addEventListener("DOMContentLoaded", () => {
    const cursor = document.getElementById("custom-cursor");
    if (cursor) {
        document.addEventListener("mousemove", (e) => {
            cursor.style.left = e.clientX + "px";
            cursor.style.top = e.clientY + "px";
        });
        document.querySelectorAll("a, button, .preset-btn, .console-send, .timeline-header, input").forEach(el => {
            el.addEventListener("mouseenter", () => cursor.classList.add("hovering"));
            el.addEventListener("mouseleave", () => cursor.classList.remove("hovering"));
        });
    }

    // 3D Card tilt effect
    document.querySelectorAll(".feature-card, .diag-card").forEach(card => {
        card.addEventListener("mousemove", (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const xc = rect.width / 2;
            const yc = rect.height / 2;
            const angleX = (yc - y) / 10; // max 10 deg rotation
            const angleY = (x - xc) / 10;
            card.style.transform = `perspective(1000px) rotateX(${angleX}deg) rotateY(${angleY}deg) translateY(-5px)`;
        });
        card.style.transformOrigin = "center center";
        card.addEventListener("mouseleave", () => {
            card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0deg)";
        });
    });

    // Stat count-ups on scroll reveal
    const countUpElements = document.querySelectorAll(".count-up");
    if (countUpElements.length > 0) {
        const countObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const targetEl = entry.target;
                    const targetValue = parseInt(targetEl.getAttribute("data-target"), 10);
                    let count = 0;
                    const duration = 1200; // ms
                    const stepTime = 20; // ms
                    const steps = duration / stepTime;
                    const increment = targetValue / steps;
                    
                    const interval = setInterval(() => {
                        count += increment;
                        if (count >= targetValue) {
                            targetEl.innerText = targetValue;
                            clearInterval(interval);
                        } else {
                            targetEl.innerText = Math.floor(count);
                        }
                    }, stepTime);
                    
                    countObserver.unobserve(targetEl);
                }
            });
        }, { threshold: 0.2 });
        countUpElements.forEach(el => countObserver.observe(el));
    }

    // Parallax background depth check on scroll
    const hudGrid = document.querySelector(".hud-grid");
    if (hudGrid) {
        window.addEventListener("scroll", () => {
            const offset = window.pageYOffset;
            hudGrid.style.transform = `translateY(${offset * 0.25}px)`;
        });
    }

    // Matrix Demo Data and function
    const matrixData = {
        sys: {
            title: "system_automation.sh",
            lines: [
                { type: "user-input", text: '> arvis "set system volume to 40%"' },
                { type: "step-thought", text: '💭 <strong>Thought:</strong> User wants to adjust Windows audio parameters. Calling system control module.' },
                { type: "step-tool", text: '🛠️ <strong>Tool Call:</strong> system_control(action="volume", value=40)' },
                { type: "step-observation", text: '✅ <strong>Observation:</strong> volume level successfully configured to 40%' },
                { type: "final-reply", text: '🤖 <strong>ARVIS:</strong> Windows system volume has been adjusted to 40%. Audio channels calibrated.' }
            ]
        },
        mem: {
            title: "semantic_memory.sh",
            lines: [
                { type: "user-input", text: '> arvis "recall discussion about eventlet import locks"' },
                { type: "step-thought", text: '💭 <strong>Thought:</strong> Fetching query embeddings to query RAG conversation vector database.' },
                { type: "step-tool", text: '🛠️ <strong>Tool Call:</strong> memory_query(query="eventlet import locks", limit=1)' },
                { type: "step-observation", text: '✅ <strong>Observation:</strong> cosine_similarity matches row ID 24 with score 0.91' },
                { type: "final-reply", text: '🤖 <strong>ARVIS:</strong> Found record from 2026-07-05: Resolved python import deadlocks by injecting os.environ["EVENTLET_NO_GREENDNS"] = "yes".' }
            ]
        },
        vis: {
            title: "desktop_vision.sh",
            lines: [
                { type: "user-input", text: '> arvis "analyze screen and read error message"' },
                { type: "step-thought", text: '💭 <strong>Thought:</strong> Capturing desktop screenshot to extract vision context.' },
                { type: "step-tool", text: '🛠️ <strong>Tool Call:</strong> screen_capture_and_ocr()' },
                { type: "step-observation", text: '✅ <strong>Observation:</strong> Screenshot taken. Gemini Vision identifies: ModuleNotFoundError: No module named pyaudio' },
                { type: "final-reply", text: '🤖 <strong>ARVIS:</strong> Detected PyAudio compile crash in your console. Recommend installing PyAudioWPatch as fallback.' }
            ]
        },
        cod: {
            title: "code_sandbox.sh",
            lines: [
                { type: "user-input", text: '> arvis "write python script to plot monthly chart and save as sales.png"' },
                { type: "step-thought", text: '💭 <strong>Thought:</strong> Generating and executing matplotlib sandbox code.' },
                { type: "step-tool", text: '🛠️ <strong>Tool Call:</strong> execute_code(language="python", code="import matplotlib.pyplot as plt...")' },
                { type: "step-observation", text: '✅ <strong>Observation:</strong> Script completed. Created sales.png. Automatically relocated to static/assets/charts/' },
                { type: "final-reply", text: '🤖 <strong>ARVIS:</strong> Plotted sales data and saved chart. Rendered inline: <br><img src="/static/assets/charts/sales.png" style="max-width:100%; border-radius:6px; margin-top:10px; border: 1px solid rgba(255,255,255,0.05);">' }
            ]
        },
        web: {
            title: "web_scraper.sh",
            lines: [
                { type: "user-input", text: '> arvis "search for open-meteo weather and fetch raw webpage content"' },
                { type: "step-thought", text: '💭 <strong>Thought:</strong> Fetching URL content and extracting readable body text.' },
                { type: "step-tool", text: '🛠️ <strong>Tool Call:</strong> parse_web_page(url="https://open-meteo.com/en/docs")' },
                { type: "step-observation", text: '✅ <strong>Observation:</strong> Webpage loaded. Stripped header navigation, parsed weather code mapping references.' },
                { type: "final-reply", text: '🤖 <strong>ARVIS:</strong> Successfully scraped documentation. Decoded condition code mappings (e.g. WMO 0 = Clear Sky, WMO 3 = Overcast).' }
            ]
        }
    };

    window.showMatrixTab = function(tabName) {
        const display = document.getElementById("matrix-display");
        const titleEl = document.getElementById("matrix-terminal-title");
        if (!display || !titleEl || !matrixData[tabName]) return;

        // Set active class on buttons
        document.querySelectorAll(".matrix-btn").forEach(btn => btn.classList.remove("active"));
        const activeBtn = document.getElementById("btn-" + tabName);
        if (activeBtn) activeBtn.classList.add("active");

        // Set title
        titleEl.innerText = matrixData[tabName].title;

        // Clear and render lines sequentially
        display.innerHTML = "";
        const data = matrixData[tabName];
        
        data.lines.forEach((line, index) => {
            setTimeout(() => {
                const el = document.createElement("div");
                el.className = `matrix-log-line ${line.type}`;
                el.innerHTML = line.text;
                display.appendChild(el);
                display.scrollTop = display.scrollHeight;
            }, index * 250);
        });
    };

    window.updateDeckVal = function(param, value) {
        const valEl = document.getElementById(`${param}-val`);
        const statusEl = document.getElementById(`${param}-status`);
        if (!valEl || !statusEl) return;

        valEl.innerText = value;

        if (param === 'temp') {
            const t = parseFloat(value);
            if (t <= 0.3) {
                statusEl.innerText = "Deterministic. Optimized for coding & debugging.";
            } else if (t <= 0.7) {
                statusEl.innerText = "Balanced reasoning. Standard assistant chats.";
            } else {
                statusEl.innerText = "Highly creative. Good for prose, poetry & speech patterns.";
            }
        } else if (param === 'iter') {
            const val = parseInt(value);
            if (val <= 5) {
                statusEl.innerText = "Fast response loop. Ideal for simple commands.";
            } else if (val <= 10) {
                statusEl.innerText = "Balanced depth. Avoids execution loop locks.";
            } else {
                statusEl.innerText = "Ultra-thorough exploration. Solves complex coding scripts.";
            }
        }
    };
});
