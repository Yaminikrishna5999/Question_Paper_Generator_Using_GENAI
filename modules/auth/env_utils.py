import os
import re
from config import Config

def update_env_key(new_key):
    """
    Safely updates the GEMINI_API_KEY in the .env file and the current session.
    """
    env_path = ".env"
    key_found = False
    lines = []
    
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith("GEMINI_API_KEY="):
                lines[i] = f"GEMINI_API_KEY={new_key}\n"
                key_found = True
                break
    
    if not key_found:
        lines.append(f"\nGEMINI_API_KEY={new_key}\n")
        
    with open(env_path, "w") as f:
        f.writelines(lines)
    
    # Update current session
    os.environ["GEMINI_API_KEY"] = new_key
    Config.GEMINI_API_KEY = new_key
    return True
