import os
import subprocess
import uuid
import config
import ast

def is_code_safe(code, language="python"):
    """Parses code to check for unauthorized library imports or subprocess invocations."""
    lang_lower = language.lower().strip()
    
    if lang_lower in ["python", "py"]:
        try:
            root = ast.parse(code)
        except SyntaxError:
            # Let python run and show syntax error messages
            return True, ""
            
        unsafe_modules = {"os", "sys", "subprocess", "shutil", "socket", "urllib", "requests", "ctypes", "pty"}
        for node in ast.walk(root):
            if isinstance(node, ast.Import):
                for name in node.names:
                    module_name = name.name.split('.')[0]
                    if module_name in unsafe_modules:
                        return False, f"Import of unsafe module '{module_name}' is blocked."
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name in unsafe_modules:
                        return False, f"Import from unsafe module '{module_name}' is blocked."
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec"]:
                        return False, f"Execution of function '{node.func.id}' is blocked."
    elif lang_lower in ["javascript", "js", "node"]:
        dangerous_js = ["require('child_process')", 'require("child_process")', "require('fs')", 'require("fs")', "eval("]
        for item in dangerous_js:
            if item in code:
                return False, f"Usage of unsafe module/call '{item}' is blocked in JavaScript."
                
    return True, ""
import sys
import importlib.util

SAFE_THIRD_PARTY_PACKAGES = {
    "numpy", "pandas", "matplotlib", "scipy", "sympy", "seaborn", 
    "requests", "bs4", "beautifulsoup4", "pillow", "openpyxl"
}

def check_and_install_dependencies(code):
    """Analyzes Python code for missing safe libraries and auto-installs them using pip."""
    try:
        root = ast.parse(code)
    except Exception:
        return
        
    imported_modules = set()
    for node in ast.walk(root):
        if isinstance(node, ast.Import):
            for name in node.names:
                imported_modules.add(name.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module.split('.')[0])
                
    for mod in imported_modules:
        if mod in SAFE_THIRD_PARTY_PACKAGES:
            package_name = "beautifulsoup4" if mod == "bs4" else mod
            try:
                if importlib.util.find_spec(mod) is None:
                    print(f"📦 Code Executor: Auto-installing missing dependency '{package_name}'...")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", package_name],
                        capture_output=True,
                        timeout=60
                    )
            except Exception as pip_err:
                print(f"⚠️ Pip auto-install failed for '{package_name}': {pip_err}")

def execute_code(code, language="python"):
    """Saves generated code to temp file and executes it.
    
    Returns standard output and errors.
    """
    lang_lower = language.lower().strip()
    if lang_lower not in ["python", "py", "javascript", "js", "node"]:
        return f"Error: Language '{language}' is not supported. Supported: Python, JavaScript."
        
    # Check execution safety using AST parser
    safe, reason = is_code_safe(code, lang_lower)
    if not safe:
        return f"Error: Execution blocked. {reason}"
        
    # Check and install missing safe dependencies
    if lang_lower in ["python", "py"]:
        check_and_install_dependencies(code)
        
    # Block obviously destructive statements
    dangerous_keywords = ["rmdir", "rmtree", "mkfs", "format"]
    for keyword in dangerous_keywords:
        if keyword in code:
            return f"Error: Execution blocked. Code contains potentially destructive keyword: '{keyword}'."

    # Create temporary file
    file_id = str(uuid.uuid4())[:8]
    os.makedirs(config.CODE_RUNS_DIR, exist_ok=True)
    
    if lang_lower in ["python", "py"]:
        file_name = f"run_{file_id}.py"
        run_cmd = ["python", file_name]
    else:
        file_name = f"run_{file_id}.js"
        run_cmd = ["node", file_name]
        
    file_path = os.path.join(config.CODE_RUNS_DIR, file_name)
    
    try:
        # Save code to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Get set of images in CODE_RUNS_DIR before execution to detect new ones
        before_images = set()
        if os.path.exists(config.CODE_RUNS_DIR):
            before_images = {f for f in os.listdir(config.CODE_RUNS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))}

        # Execute script with timeout inside code_runs folder
        result = subprocess.run(
            run_cmd,
            cwd=config.CODE_RUNS_DIR,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        output = result.stdout
        error = result.stderr
        
        # Check for any new images generated (plots/charts)
        new_images = []
        if os.path.exists(config.CODE_RUNS_DIR):
            after_images = {f for f in os.listdir(config.CODE_RUNS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))}
            new_files = after_images - before_images
            
            if new_files:
                charts_dir = os.path.join(config.BASE_DIR, "static", "assets", "charts")
                os.makedirs(charts_dir, exist_ok=True)
                
                import shutil
                for filename in new_files:
                    src_path = os.path.join(config.CODE_RUNS_DIR, filename)
                    clean_name = f"chart_{uuid.uuid4().hex[:8]}_{filename}"
                    dest_path = os.path.join(charts_dir, clean_name)
                    try:
                        shutil.move(src_path, dest_path)
                        new_images.append(f"![Generated Chart](/static/assets/charts/{clean_name})")
                    except Exception as copy_err:
                        print(f"Error copying chart '{filename}': {copy_err}")
        
        response = []
        if output:
            response.append(f"--- Standard Output ---\n{output}")
        if error:
            response.append(f"--- Standard Error ---\n{error}")
            
        if not output and not error:
            response.append("Code executed successfully with no output returned.")
            
        # Append inline Markdown image references for any generated charts
        if new_images:
            response.append("\n" + "\n".join(new_images))
            
        return "\n".join(response)
        
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (limit: 15 seconds)."
    except Exception as e:
        return f"Error running code: {str(e)}"
    finally:
        # Cleanup temp file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
                
def generate_code_draft(prompt, language="python"):
    """Uses Gemini directly to generate clean code matching a description."""
    if not getattr(config, 'GEMINI_API_KEY', ''):
        return "Error: GEMINI_API_KEY not configured in .env."
        
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL)
    
    system_prompt = (
        f"You are a code drafting assistant. Write pure {language} code code matching the description. "
        f"Do NOT include markdown comments, ``` symbols, or explanation. Output ONLY the code itself."
    )
    
    try:
        response = model.generate_content(f"{system_prompt}\n\nTask:\n{prompt}")
        return response.text.strip()
    except Exception as e:
        return f"Error generating code draft: {str(e)}"
