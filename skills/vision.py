"""
ARVIS Screen Vision Skill — Captures and analyzes screenshot via Gemini multimodal API
"""

import os
import base64
import requests
import pyautogui
import urllib3
import warnings
import config

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

def analyze_screen(prompt: str = "Describe what is on my screen in detail.") -> str:
    """Takes a desktop screenshot, encodes it, and sends it to Gemini API for visual analysis.

    Enables features like visual debugging, reading open documents, or summarizing current tasks.
    """
    api_key = getattr(config, 'GEMINI_API_KEY', '')
    if not api_key or "your_gemini" in api_key.lower():
        return "❌ Error: Gemini API Key is not configured. Please add `GEMINI_API_KEY` to your `.env` file."

    model_name = getattr(config, 'GEMINI_MODEL', 'gemini-1.5-flash')
    
    # 1. Take a screenshot
    print("[Screen Vision]: Capturing screenshot...")
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    temp_img_path = os.path.join(config.TEMP_DIR, "vision_temp.png")
    
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(temp_img_path)
    except Exception as e:
        return f"❌ Error: Failed to capture desktop screenshot: {str(e)}"
        
    # 2. Encode to base64
    try:
        with open(temp_img_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        return f"❌ Error: Failed to read/encode screenshot: {str(e)}"
    finally:
        # Cleanup temp file
        if os.path.exists(temp_img_path):
            try:
                os.remove(temp_img_path)
            except Exception:
                pass

    # 3. Call Gemini API
    print(f"[Screen Vision]: Sending image to Gemini model '{model_name}'...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": base64_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 1024,
            "temperature": 0.4
        }
    }
    
    try:
        r = requests.post(url, json=body, timeout=25, verify=False)
        r.raise_for_status()
        res_json = r.json()
        
        candidates = res_json.get("candidates", [])
        if not candidates:
            return "⚠️ Gemini returned no responses. Check API status."
            
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return "⚠️ Gemini response did not contain any text components."
            
        return parts[0].get("text", "").strip()
        
    except Exception as e:
        return f"❌ Error: Visual analysis failed: {str(e)}"
