import os
import json
import re
import time
import datetime
import hashlib
import requests
import warnings
import config
from dotenv import load_dotenv
load_dotenv()

# Claude Integration Constants
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_URL     = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-20241022")

# Gemini Integration Constants
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_URL     = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)

from agent.memory import ArvisMemory
from agent.context_manager import ContextManager
from skills.calculator import evaluate_formula

class ArvisBrain:
    def __init__(self, session_id="default_session", task_router=None):
        self.session_id = session_id
        self.router = task_router
        self.memory = ArvisMemory()
        
        # Conversation window restricted to 4 messages for token savings as requested in prompt
        self.context_manager = ContextManager(max_history=4)
        
        # Track model cooldowns to avoid rate-limit log spamming
        self.model_cooldowns = {}
        
        # Load Groq API keys supporting rotation (comma-separated list)
        self.groq_keys = [k.strip() for k in config.GROQ_API_KEY.split(",") if k.strip()]
        self.active_groq_index = 0
        self.groq_keys_health = {key: {"status": "ok", "cooldown_until": 0.0} for key in self.groq_keys}
        
        self.system_instruction = self.get_system_instruction()

    def get_system_instruction(self):
        return """You are ARVIS, a smart local AI assistant on Windows.

RESPONSE FORMAT: Always reply with a single JSON object only (no wrappers):
- Tool call:    {"thought":"...","tool":"tool_name","args":{}}
- Final answer: {"thought":"...","final_answer":"..."}

COMMAND → TOOL MAPPING (follow these exactly):
- "open/launch/turn on/start [app]"  → tool: open_app,   args: {"app_name": "[app]"}
- "close/quit/exit [app]"            → tool: close_app,  args: {"window_title": "[app]"}
- "turn off wifi" / "disable wifi"   → tool: turn_off_wifi, args: {}
- "turn on wifi"  / "enable wifi"    → tool: turn_on_wifi,  args: {}
- "wifi status"   / "check wifi"     → tool: get_wifi_status, args: {}
- "turn off bluetooth"               → tool: turn_off_bluetooth, args: {}
- "turn on bluetooth"                → tool: turn_on_bluetooth, args: {}
- "set volume to N" / "volume N%"   → tool: set_volume,  args: {"level": N}
- "mute"                             → tool: mute_volume, args: {}
- "unmute"                           → tool: unmute_volume, args: {}
- "set brightness to N"             → tool: set_brightness, args: {"level": N}
- "lock screen" / "lock my screen"  → tool: lock_screen, args: {}
- "sleep" / "put to sleep"          → tool: sleep_system, args: {}
- "shutdown" / "turn off computer"  → tool: shutdown_system, args: {"delay_seconds": 0}
- "restart" / "reboot"              → tool: restart_system, args: {"delay_seconds": 0}
- "cancel shutdown"                 → tool: cancel_shutdown, args: {}
- "battery" / "battery status"      → tool: get_battery_status, args: {}
- "screenshot" / "take screenshot"  → tool: take_screenshot, args: {}
- "[topic] news" / "news about [X]" / "tech news" → tool: get_news, args: {"category_or_topic": "[topic]"}
- "search [query]" / "look up"      → tool: web_search, args: {"query": "[query]"}
- "calculate [expr]"                → tool: evaluate_formula, args: {"expression": "[expr]"}
- "system stats" / "cpu usage"      → tool: get_system_stats, args: {}
- "browse [url]" / "read url [url]"  → tool: browse_url, args: {"url": "[url]"}
- "analyze screen" / "see screen"    → tool: analyze_screen, args: {"prompt": "[optional prompt]"}
- "delegate [task]" / "spawn agent"  → tool: delegate_task, args: {"role": "[coder/reviewer/analyst/researcher]", "task": "[task]"}

EXAMPLES:
  User: "turn on whatsapp"  → {"thought":"Opening WhatsApp","tool":"open_app","args":{"app_name":"whatsapp"}}
  User: "turn off wifi"     → {"thought":"Disabling WiFi","tool":"turn_off_wifi","args":{}}
  User: "set volume to 60"  → {"thought":"Setting volume","tool":"set_volume","args":{"level":60}}
  User: "lock my screen"    → {"thought":"Locking screen","tool":"lock_screen","args":{}}
  User: "tech news"          → {"thought":"Fetching tech news","tool":"get_news","args":{"category_or_topic":"tech"}}
  User: "news about cricket"  → {"thought":"Fetching cricket news","tool":"get_news","args":{"category_or_topic":"cricket"}}
  User: "15% of 2500"        → {"thought":"Calculating","tool":"evaluate_formula","args":{"expression":"15% of 2500"}}

MARKDOWN RULES (inside final_answer string only):
- Use ## for main headers, ### for sub-headers
- Use **bold** for key terms, `inline code` for commands/files
- Use - bullets for lists, 1. 2. 3. for steps only
- Use ```language ... ``` for code blocks
- Never use markdown outside final_answer

GENERAL RULES & REASONING GUIDELINES:
- Answer first, explain after. Short = better.
- No hallucination. Say "I don't know" if unsure.
- TOOL CHOICE DECISIONS (Follow strictly):
  1. For math calculations, ALWAYS use `evaluate_formula` (do not run code for simple math).
  2. For web search queries, current news, dates, weather, or real-time lookup, ALWAYS use `web_search`.
  3. For file operations (create, read, search, delete, list), use the corresponding file tools instead of writing custom scripts.
  4. For programming tasks, running complex loops/algorithms, or data processing, use `execute_code`.
- Code: clean Python with try/except blocks. Fix syntax errors and retry.

TOOLS: open_app, close_app, focus_window, take_screenshot,
type_text, click_at, press_keys, list_files, create_file,
read_file(path,start_line,end_line), search_in_file,
delete_file, move_file, search_files, web_search,
send_email, execute_code, evaluate_formula,
get_system_stats, schedule_task, get_news(category_or_topic),
set_volume(level), mute_volume, unmute_volume,
set_brightness(level), turn_on_wifi, turn_off_wifi,
get_wifi_status, turn_on_bluetooth, turn_off_bluetooth,
lock_screen, sleep_system, shutdown_system(delay_seconds),
restart_system(delay_seconds), cancel_shutdown,
get_battery_status, browse_url(url), analyze_screen(prompt),
delegate_task(role, task)"""


    def rotate_groq_key(self):
        if not self.groq_keys:
            return False
            
        now = time.time()
        found_key_index = None
        for i in range(len(self.groq_keys)):
            idx = (self.active_groq_index + 1 + i) % len(self.groq_keys)
            key = self.groq_keys[idx]
            health = self.groq_keys_health.get(key, {"status": "ok", "cooldown_until": 0.0})
            if health["status"] == "ok" and now >= health["cooldown_until"]:
                found_key_index = idx
                break
                
        if found_key_index is None:
            # Fall back to key with shortest cooldown
            shortest_cooldown_idx = None
            min_cooldown = float('inf')
            for i in range(len(self.groq_keys)):
                idx = (self.active_groq_index + 1 + i) % len(self.groq_keys)
                key = self.groq_keys[idx]
                health = self.groq_keys_health.get(key, {"status": "ok", "cooldown_until": 0.0})
                if health["status"] == "ok" and health["cooldown_until"] < min_cooldown:
                    min_cooldown = health["cooldown_until"]
                    shortest_cooldown_idx = idx
            
            if shortest_cooldown_idx is not None:
                # Instead of pausing, return False so the caller raises an exception and triggers fallback immediately
                return False
            else:
                return False
                
        self.active_groq_index = found_key_index
        print(f"🔄 [ARVIS Brain]: Rotating to Groq API Key #{self.active_groq_index + 1}...")
        return True

    def call_groq_with_rotation(self, history):
        """Primary AI API call utilizing Groq with key rotation and rate-limit backoff."""
        if not self.groq_keys:
            raise Exception("No Groq API keys configured in environment.")
            
        from groq import Groq
        max_attempts = max(1, len(self.groq_keys) * 2)
        
        for attempt in range(max_attempts):
            current_key = self.groq_keys[self.active_groq_index]
            try:
                client = Groq(api_key=current_key, timeout=12.0)
                
                # Format history list for OpenAI/Groq messages structure
                messages = [{"role": "system", "content": self.system_instruction}]
                for msg in history:
                    role = msg["role"]
                    if role == "model":
                        role = "assistant"
                    messages.append({"role": role, "content": msg["parts"][0]})
                
                # Use smartest model, with an automatic fallback to Llama 3.1 8B on failure
                model_to_use = getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")
                
                # If model is on cooldown, use fallback directly without printing warning
                now = time.time()
                if model_to_use in self.model_cooldowns and now < self.model_cooldowns[model_to_use]:
                    model_to_use = "llama-3.1-8b-instant"
                
                try:
                    response = client.chat.completions.create(
                        model=model_to_use,
                        messages=messages,
                        temperature=0.1,
                        response_format={"type": "json_object"} # Enforce JSON format output
                    )
                except Exception as model_err:
                    model_err_str = str(model_err).lower()
                    # Catch model access issues or rate limits on the 70B model to fall back on 8B model
                    if model_to_use != "llama-3.1-8b-instant" and any(x in model_err_str for x in ["not found", "unsupported", "limit", "429", "model"]):
                        print(f"⚠️ [ARVIS Brain]: Groq model '{model_to_use}' unavailable or rate-limited ({model_err}). Falling back to 'llama-3.1-8b-instant'...")
                        self.model_cooldowns[model_to_use] = time.time() + 60.0 # 60-second cooldown
                        response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=messages,
                            temperature=0.1,
                            response_format={"type": "json_object"}
                        )
                    else:
                        raise model_err

                self.groq_keys_health[current_key] = {"status": "ok", "cooldown_until": 0.0}
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ Groq call failed (Key #{self.active_groq_index + 1}): {err_str}")
                
                if "429" in err_str or "rate limit" in err_str.lower():
                    self.groq_keys_health[current_key] = {"status": "ok", "cooldown_until": time.time() + 30.0}
                
                if attempt < max_attempts - 1:
                    if not self.rotate_groq_key():
                        raise Exception("All Groq API keys are currently rate-limited or unavailable.")
                else:
                    raise Exception(f"All Groq keys failed. Last error: {err_str}")

    def call_openrouter(self, history):
        """Fallback API call utilizing OpenRouter model."""
        if not config.OPENROUTER_API_KEY or "your_openrouter_api_key" in config.OPENROUTER_API_KEY:
            raise Exception("OpenRouter API key not configured in environment.")
            
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
            timeout=12.0
        )
        
        # Format history list for OpenAI messages structure
        messages = [{"role": "system", "content": self.system_instruction}]
        for msg in history:
            role = msg["role"]
            if role == "model":
                role = "assistant"
            messages.append({"role": role, "content": msg["parts"][0]})
            
        model_to_use = getattr(config, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
        print(f"🔗 [ARVIS Brain]: Groq exhausted. Invoking OpenRouter fallback ({model_to_use})...")
        
        try:
            response = client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"} # Enforce JSON format output
            )
        except Exception as e_or:
            e_or_str = str(e_or).lower()
            fallback_or = "meta-llama/llama-3.1-8b-instruct:free"
            print(f"⚠️ [ARVIS Brain]: OpenRouter model '{model_to_use}' failed. Falling back to '{fallback_or}'...")
            response = client.chat.completions.create(
                model=fallback_or,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
        return response.choices[0].message.content.strip()

    def call_ollama(self, history):
        """Call local Ollama service using its OpenAI-compatible endpoint."""
        url = f"{getattr(config, 'OLLAMA_HOST', 'http://localhost:11434')}/v1/chat/completions"
        model_name = getattr(config, 'OLLAMA_MODEL', 'llama3')
        
        messages = [{"role": "system", "content": self.system_instruction}]
        for msg in history:
            role = msg["role"]
            if role == "model":
                role = "assistant"
            # Format content correctly (extract from parts list if needed)
            content = msg["parts"][0] if (isinstance(msg.get("parts"), list) and msg["parts"]) else msg.get("content", "")
            messages.append({"role": role, "content": content})
            
        body = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        try:
            print(f"🔗 [ARVIS Brain]: Calling local Ollama model '{model_name}' at {getattr(config, 'OLLAMA_HOST', 'http://localhost:11434')}...")
            r = requests.post(url, json=body, timeout=15)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return content.strip()
        except Exception as e:
            raise Exception(f"Ollama call failed: {str(e)}")

    def call_ai_smart(self, history):
        """Smart Multi-Provider router. Tries Ollama first if preferred, otherwise Groq as primary, falling back to OpenRouter."""
        errors = []
        
        # 0. Try Ollama if explicitly preferred as primary local provider
        if getattr(config, 'OLLAMA_PREFERRED', False):
            try:
                return self.call_ollama(history)
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ [ARVIS Brain]: Preferred local Ollama failed: {err_str}")
                errors.append(f"Ollama (Preferred): {err_str}")

        # 1. Try Groq (Primary)
        if self.groq_keys and "your_groq_api_key" not in self.groq_keys[0]:
            try:
                return self.call_groq_with_rotation(history)
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ [ARVIS Brain]: Groq failed: {err_str}")
                errors.append(f"Groq: {err_str}")
                
        # 2. Try OpenRouter (Fallback)
        if config.OPENROUTER_API_KEY and "your_openrouter_api_key" not in config.OPENROUTER_API_KEY:
            try:
                return self.call_openrouter(history)
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ [ARVIS Brain]: OpenRouter fallback failed: {err_str}")
                errors.append(f"OpenRouter: {err_str}")
                
        # If all smart/online providers fail, try Ollama as local fallback if it was not already tried
        if not getattr(config, 'OLLAMA_PREFERRED', False):
            try:
                return self.call_ollama(history)
            except Exception as e:
                errors.append(f"Ollama (Fallback): {str(e)}")

        # If all providers fail
        raise Exception("All primary and fallback AI providers (Groq/OpenRouter/Ollama) failed. Logs:\n" + "\n".join(errors))

    def detect_prompt_type(self, msg):
        """Detect ANS / SOLUTION / REPLY from user message."""
        m = msg.lower()
        if any(w in m for w in ["fix","solve","how to","error","install",
                                  "steps","setup","build","debug","not working",
                                  "create","write code","make a"]):
            return "SOLUTION"
        if any(w in m for w in ["i feel","i'm stuck","i don't know",
                                  "what should i","help me","chat","talk"]):
            return "REPLY"
        return "ANS"

    def call_claude(self, user_msg, prompt_type="ANS", history=None):
        TYPE_PROMPTS = {
            "ANS": (
                "Answer in 1-2 sentences. Bold key terms. "
                "Return JSON only: {\"thought\":\"...\",\"final_answer\":\"...\"}"
            ),
            "SOLUTION": (
                "Solve step by step with numbered list. Use code blocks. "
                "Add ## heading. Return JSON only: {\"thought\":\"...\",\"final_answer\":\"...\"}"
            ),
            "REPLY": (
                "Be friendly and concise, max 3 sentences. "
                "Return JSON only: {\"thought\":\"...\",\"final_answer\":\"...\"}"
            )
        }

        headers = {
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        messages = []
        if history:
            for msg in history:
                role = msg["role"]
                if role == "model":
                    role = "assistant"
                messages.append({"role": role, "content": msg["parts"][0]})
        else:
            messages = [{"role": "user", "content": user_msg}]

        body = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "system": self.system_instruction + "\n\n" + TYPE_PROMPTS[prompt_type],
            "messages": messages
        }

        r = requests.post(CLAUDE_URL, headers=headers, json=body, timeout=12)
        r.raise_for_status()
        raw = r.json()["content"][0]["text"]
        return self.parse_json_fallback(raw)

    def call_gemini(self, user_msg, prompt_type="ANS", history=None):
        TYPE_PROMPTS = {
            "ANS": (
                "Answer in 1-2 sentences. Bold key terms. "
                "Return JSON only: {\"thought\":\"...\",\"final_answer\":\"...\"}"
            ),
            "SOLUTION": (
                "Solve step by step with numbered list. Use code blocks. "
                "Add ## heading. Return JSON only: {\"thought\":\"...\",\"final_answer\":\"...\"}"
            ),
            "REPLY": (
                "Be friendly and concise, max 3 sentences. "
                "Return JSON only: {\"thought\":\"...\",\"final_answer\":\"...\"}"
            )
        }

        system_text = self.system_instruction + "\n\n" + TYPE_PROMPTS[prompt_type]

        # Use dynamic URL configuration
        api_key = getattr(config, 'GEMINI_API_KEY', '') or GEMINI_API_KEY
        model_name = getattr(config, 'GEMINI_MODEL', '') or GEMINI_MODEL
        gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={api_key}"
        )

        contents = []
        if history:
            for msg in history:
                contents.append({
                    "role": msg["role"],
                    "parts": [{"text": msg["parts"][0]}]
                })
        else:
            contents = [
                {"role": "user", "parts": [{"text": user_msg}]}
            ]

        body = {
            "system_instruction": {
                "parts": [{"text": system_text}]
            },
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.7,
                "responseMimeType": "application/json"
            }
        }

        r = requests.post(gemini_url, json=body, timeout=12)
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return self.parse_json_fallback(raw)

    def route_all_providers(self, user_msg, history=None):
        """Try Ollama/Local check → Groq → Claude → Gemini with auto prompt type detection."""
        if history is None:
            history = []
        ptype  = self.detect_prompt_type(user_msg)
        errors = []

        # 0. Check for explicit local/ollama prefix
        user_msg_lower = user_msg.lower().strip()
        if user_msg_lower.startswith("local: ") or user_msg_lower.startswith("ollama: "):
            prefix_len = 7 if user_msg_lower.startswith("local: ") else 8
            stripped_history = list(history)
            if stripped_history and stripped_history[-1]["role"] == "user":
                stripped_msg = user_msg[prefix_len:].strip()
                stripped_history[-1] = {"role": "user", "parts": [stripped_msg]}
            try:
                return self.call_ollama(stripped_history)
            except Exception as e:
                errors.append(f"Ollama (Explicit): {e}")

        # Try Preferred Ollama first if configured
        if getattr(config, 'OLLAMA_PREFERRED', False):
            try:
                return self.call_ollama(history)
            except Exception as e:
                errors.append(f"Ollama (Preferred): {e}")

        # 1. Try Groq (primary — fastest, free)
        try:
            return self.call_ai_smart(history)
        except Exception as e:
            errors.append(f"Groq/Router: {e}")

        # 2. Try Claude (first fallback — best quality)
        if CLAUDE_API_KEY:
            try:
                print("🔗 [ARVIS Brain]: Smart router failed. Invoking Claude fallback...")
                return self.call_claude(user_msg, ptype, history=history)
            except Exception as e:
                errors.append(f"Claude: {e}")
        else:
            errors.append("Claude: API key not configured.")

        # 3. Try Gemini (second fallback — free tier)
        api_key = getattr(config, 'GEMINI_API_KEY', '') or GEMINI_API_KEY
        if api_key:
            try:
                print("🔗 [ARVIS Brain]: Claude failed. Invoking Gemini fallback...")
                return self.call_gemini(user_msg, ptype, history=history)
            except Exception as e:
                errors.append(f"Gemini: {e}")
        else:
            errors.append("Gemini: API key not configured.")

        # 4. Final local Ollama fallback if nothing else worked
        if not getattr(config, 'OLLAMA_PREFERRED', False):
            try:
                print("🔗 [ARVIS Brain]: Online providers failed. Invoking Ollama local fallback...")
                return self.call_ollama(history)
            except Exception as e:
                errors.append(f"Ollama (Final Fallback): {e}")

        raise Exception("All providers failed:\n" + "\n".join(errors))

    def parse_json_fallback(self, raw_text):
        """Attempts to parse JSON from the response text using regex fallbacks if direct loading fails."""
        try:
            match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except Exception:
            pass
        return None

    def check_local_task(self, query):
        """Local fallback interceptor to resolve simple queries without invoking any AI model."""
        query_clean = query.lower().strip()
        
        # 1. Time query
        if any(k in query_clean for k in ["what is the time", "current time", "what time is it"]):
            now = datetime.datetime.now().strftime("%I:%M %p")
            return {
                "thought": "Local fallback: retrieved current system time.", 
                "final_answer": f"The current system time is {now}."
            }
            
        # 2. Date query
        if any(k in query_clean for k in ["what is the date", "today's date", "what date is it", "current date"]):
            now = datetime.datetime.now().strftime("%B %d, %Y")
            return {
                "thought": "Local fallback: retrieved current system date.", 
                "final_answer": f"Today's date is {now}."
            }
            
        # 3. Math calculation query (e.g., "calculate 2 + 2" or "what is 100 / 5")
        if query_clean.startswith("calculate ") or query_clean.startswith("what is "):
            expr = query_clean.replace("calculate", "").replace("what is", "").strip()
            expr = expr.rstrip("?").strip()
            if re.match(r'^[\d\s+\-*/%().,a-zA-Z_]+$', expr):
                res = evaluate_formula(expr)
                if "Error:" not in res:
                    return {
                        "thought": "Local fallback: calculated mathematical expression.", 
                        "final_answer": res
                    }
                    
        return None

    def get_cached_response(self, prompt):
        """Checks local JSON response cache for exact prompt matches."""
        cache_file = os.path.join(config.BASE_DIR, "database", "cache.json")
        if not os.path.exists(cache_file):
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            key = hashlib.md5(prompt.lower().strip().encode("utf-8")).hexdigest()
            return cache.get(key)
        except Exception:
            return None

    def save_to_cache(self, prompt, response):
        """Saves a successful final answer response to the local JSON cache."""
        cache_file = os.path.join(config.BASE_DIR, "database", "cache.json")
        try:
            cache = {}
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            key = hashlib.md5(prompt.lower().strip().encode("utf-8")).hexdigest()
            cache[key] = response
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

    def has_any_valid_key(self) -> bool:
        """Returns True if at least one configured API key is not a placeholder or empty, or if local Ollama is active."""
        # Check Groq
        for key in self.groq_keys:
            if key and "your_groq" not in key.lower() and "placeholder" not in key.lower():
                return True
        # Check OpenRouter
        or_key = getattr(config, 'OPENROUTER_API_KEY', '')
        if or_key and "your_openrouter" not in or_key.lower() and "placeholder" not in or_key.lower():
            return True
        # Check Claude
        claude_key = CLAUDE_API_KEY
        if claude_key and "your_claude" not in claude_key.lower() and "placeholder" not in claude_key.lower():
            return True
        # Check Gemini
        gemini_key = getattr(config, 'GEMINI_API_KEY', '') or gemini_key
        if gemini_key and "your_gemini" not in gemini_key.lower() and "placeholder" not in gemini_key.lower():
            return True
        # Check Ollama
        ollama_host = getattr(config, 'OLLAMA_HOST', '')
        if ollama_host and "placeholder" not in ollama_host.lower():
            return True
        return False

    def execute_react_loop(self, user_prompt, max_steps=10):
        """Executes the complete ReAct loop: Thinking, Acting, Observing, and concluding.
        
        Yields JSON updates for frontend real-time status.
        """
        # Step A: Check local task fallbacks (time, date, simple math)
        local_res = self.check_local_task(user_prompt)
        if local_res:
            self.memory.save_message(self.session_id, "user", user_prompt)
            final_ans = local_res["final_answer"]
            self.memory.save_message(self.session_id, "assistant", final_ans)
            yield {"type": "thought", "content": local_res["thought"], "step": 1}
            yield {"type": "final_answer", "content": final_ans}
            return

        # Step B: Check response cache
        cached_val = self.get_cached_response(user_prompt)
        if cached_val:
            self.memory.save_message(self.session_id, "user", user_prompt)
            self.memory.save_message(self.session_id, "assistant", cached_val)
            yield {"type": "thought", "content": "Retrieved response from local cache (saved quota).", "step": 1}
            yield {"type": "final_answer", "content": cached_val}
            return

        # Step C: Check if at least one API key is configured (avoids total API failure crashes)
        if not self.has_any_valid_key():
            self.memory.save_message(self.session_id, "user", user_prompt)
            final_ans = (
                "⚠️ **ARVIS Configuration Required**\n\n"
                "All AI provider API keys in your `.env` file are set to default placeholders. "
                "Please configure at least one active API key (`GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CLAUDE_API_KEY`, or `GEMINI_API_KEY`) to enable cognitive reasoning.\n\n"
                "1. **How to configure**: Open the file [`.env`](file:///e:/MY%20AI/real/.env) in a text editor or use the settings panel.\n"
                "2. **Offline capabilities**: Local features like current date/time and basic math calculations (e.g. `calculate 15 * 5` or `what is 100/4`) still work offline without any configuration!"
            )
            self.memory.save_message(self.session_id, "assistant", final_ans)
            yield {"type": "thought", "content": "Configuration required: no valid API keys found in .env", "step": 1}
            yield {"type": "final_answer", "content": final_ans}
            return

        # Load conversation history
        history_msgs = self.memory.get_conversation_history(self.session_id)
        
        # SQLite Keyword Memory RAG
        # Extract alphanumeric words from prompt longer than 3 characters to search past exchanges, filtering common stopwords
        stopwords = {
            "what", "with", "from", "that", "this", "your", "have", "here", "there", "their", 
            "about", "could", "would", "should", "where", "which", "please", "thanks", "thank",
            "hello", "arvis", "jarvis", "local", "ollama", "execute", "calculate", "search",
            "create", "delete", "write"
        }
        words = [w for w in re.findall(r'\b\w{4,}\b', user_prompt) if w.lower() not in stopwords]
        rag_context_list = []
        for word in words[:3]: # limit to first 3 significant keywords
            matches = self.memory.search_past_conversations(word, limit=2)
            for m in matches:
                if m.get("user_content") and m.get("assistant_content"):
                    rag_context_list.append(f"User: {m['user_content']}\nARVIS: {m['assistant_content']}")
        
        if rag_context_list:
            rag_instruction = "\n\nRelevant past memory context:\n" + "\n---\n".join(set(rag_context_list))
            self.system_instruction = self.get_system_instruction() + rag_instruction
        else:
            self.system_instruction = self.get_system_instruction()

        # Save user query to database
        self.memory.save_message(self.session_id, "user", user_prompt)
        
        # Build the dynamic context window
        history_to_send = self.context_manager.format_history_for_gemini(history_msgs)
        # Add current user prompt
        history_to_send.append({"role": "user", "parts": [user_prompt]})
        
        # Keep track of local loop dialogue
        local_loop_history = list(history_to_send)
        
        for step in range(max_steps):
            yield {"type": "thought_start", "step": step + 1}
            
            try:
                # Optimized: Try Groq → Claude → Gemini with auto prompt type detection
                raw_response = self.route_all_providers(user_prompt, local_loop_history)
            except Exception as e:
                yield {"type": "error", "message": f"Brain processing failed: {str(e)}"}
                return

            res_data = None
            if isinstance(raw_response, dict):
                res_data = raw_response
                raw_response_str = json.dumps(raw_response)
            else:
                try:
                    res_data = json.loads(raw_response)
                except (json.JSONDecodeError, TypeError):
                    res_data = self.parse_json_fallback(raw_response)
                raw_response_str = raw_response
                
            if not res_data:
                err_msg = f"Failed to parse JSON response. Raw output: {raw_response_str}"
                yield {"type": "error", "message": err_msg}
                return

            thought = res_data.get("thought", "Analyzing inputs...")
            yield {"type": "thought", "content": thought, "step": step + 1}

            # Check for final answer
            if "final_answer" in res_data:
                final_ans = res_data["final_answer"]
                self.memory.save_message(self.session_id, "assistant", final_ans)
                self.save_to_cache(user_prompt, final_ans) # Cache response
                yield {"type": "final_answer", "content": final_ans}
                return

            # Check for tool/tools calls
            parallel_tools = res_data.get("tools")
            single_tool = res_data.get("tool")
            args = res_data.get("args", {})

            if not single_tool and not parallel_tools:
                # Ask Gemini to re-assess
                local_loop_history.append({"role": "model", "parts": [raw_response_str]})
                local_loop_history.append({
                    "role": "user",
                    "parts": ["Error: Your JSON response did not specify a 'tool' to call, a list of 'tools' to call, or a 'final_answer' to return. Please choose a valid action."]
                })
                continue

            # Load model response to conversation logic
            local_loop_history.append({"role": "model", "parts": [raw_response_str]})
            
            # Execute actions
            if parallel_tools and isinstance(parallel_tools, list):
                yield {"type": "status", "content": f"Running {len(parallel_tools)} actions..."}
                
                tool_results_list = []
                for tc in parallel_tools:
                    t_name = tc.get("tool")
                    t_args = tc.get("args", {})
                    yield {"type": "tool_call", "tool": t_name, "args": t_args}
                    
                    # Execute tool
                    start_time = time.time()
                    success, res_val = self.router.route_call(t_name, t_args) if self.router else (False, "Router offline.")
                    duration = int((time.time() - start_time) * 1000)
                    
                    # Log task in database
                    self.memory.log_task(t_name, json.dumps(t_args), str(res_val), success, duration)
                    yield {"type": "tool_result", "tool": t_name, "result": res_val, "success": success}
                    tool_results_list.append(f"Action '{t_name}' result: {res_val}")
                
                # Append tool observation
                observation = "\n".join(tool_results_list)
                local_loop_history.append({"role": "user", "parts": [observation]})
                
            else:
                # Single tool call
                yield {"type": "tool_call", "tool": single_tool, "args": args}
                
                # Execute tool
                start_time = time.time()
                success, res_val = self.router.route_call(single_tool, args) if self.router else (False, "Router offline.")
                duration = int((time.time() - start_time) * 1000)
                
                # Log task in database
                self.memory.log_task(single_tool, json.dumps(args), str(res_val), success, duration)
                yield {"type": "tool_result", "tool": single_tool, "result": res_val, "success": success}
                
                observation = f"Action '{single_tool}' result: {res_val}"
                local_loop_history.append({"role": "user", "parts": [observation]})

        yield {"type": "error", "message": "Task reached maximum reasoning steps (10) without a final answer."}
