def get_lang_code(lang_name):
    lang_map = {
        "English": "en",
        "Hindi": "hi",
        "Tamil": "ta",
        "Russian": "ru",
        "French": "fr",
        "Auto": "auto"
    }
    return lang_map.get(lang_name, "auto")

def parse_metadata(metadata_str):
    if isinstance(metadata_str, dict):
        return metadata_str
    
    try:
        # Attempt to parse as JSON
        return json.loads(metadata_str)
    except:
        # Fallback to string parsing
        metadata = {}
        parts = metadata_str.split(",")
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata

def detect_language(text):
    """Simple language detection heuristic"""
    if not text:
        return "Unknown"
    
    # Check for specific character ranges
    if any('\u0900' <= char <= '\u097F' for char in text):  # Devanagari (Hindi)
        return "Hindi"
    if any('\u0B80' <= char <= '\u0BFF' for char in text):  # Tamil
        return "Tamil"
    if any('\u0400' <= char <= '\u04FF' for char in text):  # Cyrillic (Russian)
        return "Russian"
    if any('à' in text or 'é' in text or 'ç' in text):  # French accents
        return "French"
    
    # Default to English
    return "English"