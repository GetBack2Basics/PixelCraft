import os
import json

# --- File Paths ---
PLUGIN_DIR = os.path.dirname(os.path.realpath(__file__))
SETTINGS_FILE = os.path.join(PLUGIN_DIR, "pc_settings.json")
METADATA_FILE = os.path.join(PLUGIN_DIR, "metadata.txt")

# --- Settings (JSON) ---
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_settings(settings_dict):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings_dict, f, indent=4)

# --- Metadata (TXT) ---
def load_metadata():
    meta = {}
    if not os.path.exists(METADATA_FILE):
        return meta

    with open(METADATA_FILE, 'r') as f:
        current_section = 'general'
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                meta.setdefault(current_section, {})
            elif '=' in line:
                parts = line.split('=', 1)
                meta.setdefault(current_section, {})[parts[0].strip()] = parts[1].strip()
    return meta

# --- Global Variables ---
settings = load_settings()
metadata = load_metadata()