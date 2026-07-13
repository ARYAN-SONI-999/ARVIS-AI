import os
import shutil
import glob
from pathlib import Path
import config

def resolve_path(path):
    """Utility to resolve relative/absolute paths strictly inside the project workspace root."""
    base_path = os.path.abspath(config.BASE_DIR)
    resolved = os.path.abspath(os.path.join(base_path, path))
    if not resolved.startswith(base_path):
        raise PermissionError("Access Denied: Path escapes the workspace directory sandbox.")
    return resolved

def list_files(directory="."):
    """Lists files and folders inside the directory, indicating sizes."""
    target_dir = resolve_path(directory)
    if not os.path.exists(target_dir):
        return f"Error: Directory '{directory}' does not exist."
    if not os.path.isdir(target_dir):
        return f"Error: '{directory}' is not a directory."
        
    try:
        items = os.listdir(target_dir)
        output = [f"Contents of {target_dir}:"]
        for item in items:
            full_path = os.path.join(target_dir, item)
            
            # Wrap properties check to handle Windows junction links / system files safely
            try:
                is_symlink = os.path.islink(full_path)
                is_dir = os.path.isdir(full_path)
                
                if is_symlink:
                    prefix = "[LINK]"
                    size = " (Junction Point)"
                elif is_dir:
                    prefix = "[DIR] "
                    size = ""
                else:
                    prefix = "[FILE]"
                    size_bytes = os.path.getsize(full_path)
                    if size_bytes > 1024 * 1024:
                        size = f" ({size_bytes / (1024**2):.2f} MB)"
                    elif size_bytes > 1024:
                        size = f" ({size_bytes / 1024:.2f} KB)"
                    else:
                        size = f" ({size_bytes} Bytes)"
            except Exception:
                # Safe fallback if symlink target is missing or permission is blocked
                prefix = "[LINK]"
                size = " (Access Denied / Broken Link)"
                
            output.append(f" {prefix} {item}{size}")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def create_file(path, content=""):
    """Creates a text file at path with given content."""
    target_path = resolve_path(path)
    try:
        # Ensure directories exist
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File created successfully at '{target_path}' ({len(content)} characters)."
    except Exception as e:
        return f"Error creating file at '{path}': {str(e)}"

def read_file(path, start_line=None, end_line=None):
    """Reads content of a text file with optional line range.
    Args:
        path: File path (relative or absolute).
        start_line: First line to include (1-indexed, optional).
        end_line: Last line to include (1-indexed, optional).
    """
    target_path = resolve_path(path)
    if not os.path.exists(target_path):
        return f"Error: File '{path}' does not exist."
    if os.path.isdir(target_path):
        return f"Error: '{path}' is a directory, not a file."
    try:
        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
        total_lines = len(all_lines)

        if start_line is not None or end_line is not None:
            s = max(0, int(start_line) - 1) if start_line is not None else 0
            e = min(total_lines, int(end_line)) if end_line is not None else total_lines
            selected = all_lines[s:e]
            header = f"File '{target_path}' (lines {s+1}–{e} of {total_lines}):\n---\n"
        else:
            selected = all_lines
            header = f"File '{target_path}' ({total_lines} lines):\n---\n"

        MAX_LINES = 2000
        content = ''.join(selected[:MAX_LINES])
        suffix = f"\n\n... [TRUNCATED — showing {MAX_LINES} of {len(selected)} lines] ..." \
                 if len(selected) > MAX_LINES else ''
        return header + content + suffix + '\n---'
    except Exception as e:
        return f"Error reading file at '{path}': {str(e)}"

def delete_file(path):
    """Deletes a file."""
    target_path = resolve_path(path)
    if not os.path.exists(target_path):
        return f"Error: File '{path}' does not exist."
    if os.path.isdir(target_path):
        return f"Error: '{path}' is a directory. Please delete it manually or use custom scripts."
        
    try:
        os.remove(target_path)
        return f"File '{target_path}' deleted successfully."
    except Exception as e:
        return f"Error deleting file at '{path}': {str(e)}"

def move_file(src, dst):
    """Moves or renames file from src to dst."""
    target_src = resolve_path(src)
    target_dst = resolve_path(dst)
    
    if not os.path.exists(target_src):
        return f"Error: Source file '{src}' does not exist."
        
    try:
        # Create destination directories if needed
        dest_dir = os.path.dirname(target_dst)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        shutil.move(target_src, target_dst)
        return f"Moved/Renamed '{target_src}' to '{target_dst}' successfully."
    except Exception as e:
        return f"Error moving file: {str(e)}"

def search_files(query, directory="."):
    """Finds files recursively matching glob query (e.g. *.py, note*)."""
    target_dir = resolve_path(directory)
    if not os.path.exists(target_dir):
        return f"Error: Search directory '{directory}' does not exist."
        
    try:
        # Build search glob
        search_pattern = os.path.join(target_dir, "**", query)
        # Search recursively
        matches = glob.glob(search_pattern, recursive=True)
        
        if not matches:
            return f"No files found matching query '{query}' in '{target_dir}'."
            
        output = [f"Found {len(matches)} files matching '{query}':"]
        # Limit matches output to 50 items
        for idx, m in enumerate(matches[:50]):
            rel = os.path.relpath(m, target_dir)
            output.append(f" - {rel}")
            
        if len(matches) > 50:
            output.append(f" ... and {len(matches) - 50} more files.")
            
        return "\n".join(output)
    except Exception as e:
        return f"Error searching files: {str(e)}"

def search_in_file(path, query):
    """Searches for a string query inside a file and returns matching lines."""
    target_path = resolve_path(path)
    if not os.path.exists(target_path):
        return f"Error: File '{path}' does not exist."
    if os.path.isdir(target_path):
        return f"Error: '{path}' is a directory, not a file."
    try:
        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        matches = []
        for i, line in enumerate(lines, 1):
            if query.lower() in line.lower():
                matches.append(f"  Line {i:4d}: {line.rstrip()}")
        if not matches:
            return f"No matches found for '{query}' in '{os.path.basename(path)}'."
        result = f"Found {len(matches)} match(es) for '{query}' in '{path}':\n"
        result += "\n".join(matches[:100])
        if len(matches) > 100:
            result += f"\n  ... and {len(matches) - 100} more matches."
        return result
    except Exception as e:
        return f"Error searching in file: {str(e)}"
