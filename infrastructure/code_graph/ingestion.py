import os
import shutil
import tempfile
from git import Repo
from pathlib import Path

class Ingestor:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()

    def clone_repo(self, repo_url):
        try:
            print(f"Cloning {repo_url} to {self.temp_dir}...")
            Repo.clone_from(repo_url, self.temp_dir)
            return self.temp_dir
        except Exception as e:
            print(f"Error cloning repo: {e}")
            return None

    def get_codebase_context(self, max_chars=100000):
        context = ""
        # Walk through the directory
        for root, dirs, files in os.walk(self.temp_dir):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in [
                '.git', 'node_modules', '.yarn', 'dist', 'build', '__pycache__',
                'venv', 'env', '.venv', 'vendor', 'target', '.cache'
            ]]
            
            for file in files:
                file_path = os.path.join(root, file)
                # Simple filter for text files (can be improved)
                if self._is_text_file(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            rel_path = os.path.relpath(file_path, self.temp_dir)
                            context += f"\n--- FILE: {rel_path} ---\n"
                            context += content
                            if len(context) > max_chars:
                                context += "\n... (truncated due to size) ..."
                                return context
                    except Exception:
                        continue
        return context

    def _is_text_file(self, file_path):
        """Simple heuristic to check if a file is a text file we want to index."""
        # Skip specific non-code files
        file_name = os.path.basename(file_path).lower()
        if file_name in ['license', 'notice', 'changelog', 'authors', '.gitignore', '.npmrc', '.yarnrc', '.yarnrc.yml']:
            return False
        if 'example' in file_name and file_name.endswith('.env'):
            return False
        if file_name.endswith(('.lock', '.map', '.min.js', '.min.css')):
            return False
            
        # Common binary extensions
        binary_ext = ['.pyc', '.exe', '.dll', '.so', '.dylib', '.bin', '.jpg', '.jpeg', 
                     '.png', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz', '.mp4', '.mp3']
        if any(file_path.endswith(ext) for ext in binary_ext):
            return False
        return True

    def cleanup(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
