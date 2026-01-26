import os
import json
from pathlib import Path
from typing import Dict, List


class FileSkills:
    def __init__(self):
        self.safe_root = Path.home() / "Documents"
        print("File Skills loaded")

    def list_files(self, directory: str = None) -> str:
        """List files in a directory (restricted to user's Documents)."""
        try:
            if not directory:
                path = self.safe_root
            else:
                path = self.safe_root / directory
            
            # Prevent directory traversal attacks
            if not str(path).startswith(str(self.safe_root)):
                return "Access denied: path outside safe directory."
            
            if not path.exists():
                return f"Directory not found: {directory}"
            
            files = list(path.iterdir())
            if not files:
                return f"Directory is empty: {directory or 'Documents'}"
            
            file_list = [f.name for f in files[:20]]
            return f"Files in {directory or 'Documents'}: {', '.join(file_list)}"
        except Exception as e:
            return f"Failed to list files: {e}"

    def read_file(self, filename: str) -> str:
        """Read contents of a text file (restricted to user's Documents)."""
        try:
            path = self.safe_root / filename
            if not str(path).startswith(str(self.safe_root)):
                return "Access denied: path outside safe directory."
            
            if not path.exists():
                return f"File not found: {filename}"
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if len(content) > 2000:
                return content[:2000] + "... (truncated)"
            return content
        except Exception as e:
            return f"Failed to read file: {e}"

    def write_file(self, filename: str, content: str) -> str:
        """Write content to a file (restricted to user's Documents)."""
        try:
            path = self.safe_root / filename
            if not str(path).startswith(str(self.safe_root)):
                return "Access denied: path outside safe directory."
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return f"File written: {filename}"
        except Exception as e:
            return f"Failed to write file: {e}"

    def search_files(self, pattern: str, directory: str = None) -> str:
        """Search for files matching a pattern."""
        try:
            if not directory:
                path = self.safe_root
            else:
                path = self.safe_root / directory
            
            if not str(path).startswith(str(self.safe_root)):
                return "Access denied: path outside safe directory."
            
            matches = list(path.glob(f"*{pattern}*"))[:10]
            if not matches:
                return f"No files matching '{pattern}' found."
            
            file_list = [m.name for m in matches]
            return f"Found: {', '.join(file_list)}"
        except Exception as e:
            return f"Search failed: {e}"


_file_skills = FileSkills()


def execute_function(payload: Dict):
    """Route file operations."""
    tool = payload.get("tool", "")
    
    if tool.endswith("list_files") or tool.endswith("list"):
        directory = payload.get("directory") or payload.get("dir") or None
        return _file_skills.list_files(directory)
    
    if tool.endswith("read_file") or tool.endswith("read"):
        filename = payload.get("filename") or payload.get("file") or ""
        return _file_skills.read_file(filename)
    
    if tool.endswith("write_file") or tool.endswith("write"):
        filename = payload.get("filename") or payload.get("file") or ""
        content = payload.get("content") or ""
        return _file_skills.write_file(filename, content)
    
    if tool.endswith("search_files") or tool.endswith("search"):
        pattern = payload.get("pattern") or payload.get("search") or ""
        directory = payload.get("directory") or payload.get("dir") or None
        return _file_skills.search_files(pattern, directory)
    
    return f"Unknown file tool: {tool}"
