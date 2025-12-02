import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
from utils.helpers import parse_metadata

load_dotenv()

def get_llm(model_name="gemini-2.5-flash-preview-05-20"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(model_name=model_name)
    return model

def extract_metadata_basic(text):
    # Initialize with default values
    metadata = {
        "domain": "General",
        "tone": "Neutral",
        "time_period": "Contemporary",
        "region": "Global",
        "audience": "Adults",
        "complexity": "Medium",
        "purpose": "General",
        "emotional_tone": "Neutral"
    }
    
    # Domain detection
    domain_keywords = {
        "Medical": ["medical", "health", "doctor", "hospital"],
        "Technical": ["technical", "engineering", "software", "code"],
        "Legal": ["legal", "law", "contract", "agreement"],
        "Business": ["business", "enterprise", "corporate", "sale"],
        "Education": ["education", "school", "university", "learn"],
        "Entertainment": ["entertainment", "movie", "music", "game"]
    }
    
    for domain, keywords in domain_keywords.items():
        if any(kw in text.lower() for kw in keywords):
            metadata["domain"] = domain
            break
    
    # Tone detection
    if any(word in text.lower() for word in ["buddy", "pal", "dude", "hey", "hi", "wassup"]):
        metadata["tone"] = "Informal"
    elif any(word in text.lower() for word in ["sir", "madam", "respectfully", "honorable"]):
        metadata["tone"] = "Formal"
    
    # Time period detection
    if any(word in text.lower() for word in ["ancient", "medieval", "century"]):
        metadata["time_period"] = "Historical"
    elif any(word in text.lower() for word in ["future", "next gen", "tomorrow"]):
        metadata["time_period"] = "Futuristic"
    
    # Region detection
    region_keywords = {
        "North America": ["usa", "united states", "canada", "mexico"],
        "Europe": ["europe", "eu", "uk", "united kingdom"],
        "Asia": ["asia", "china", "india", "japan"],
        "Africa": ["africa", "nigeria", "south africa", "egypt"]
    }
    
    for region, keywords in region_keywords.items():
        if any(kw in text.lower() for kw in keywords):
            metadata["region"] = region
            break
    
    # Audience detection
    if any(word in text.lower() for word in ["child", "kid", "children", "toy"]):
        metadata["audience"] = "Children"
    elif any(word in text.lower() for word in ["teen", "youth", "student"]):
        metadata["audience"] = "Teens"
    elif any(word in text.lower() for word in ["senior", "elderly", "retirement"]):
        metadata["audience"] = "Seniors"
    elif any(word in text.lower() for word in ["academic", "research", "study", "thesis"]):
        metadata["audience"] = "Academics"
    
    # Complexity detection
    word_count = len(text.split())
    if word_count < 20:
        metadata["complexity"] = "Simple"
    elif word_count > 100:
        metadata["complexity"] = "Advanced"
    
    # Purpose detection
    if any(word in text.lower() for word in ["business", "company", "enterprise", "corporate"]):
        metadata["purpose"] = "Business"
    elif any(word in text.lower() for word in ["legal", "law", "contract", "agreement"]):
        metadata["purpose"] = "Legal"
    elif any(word in text.lower() for word in ["entertainment", "movie", "music", "game"]):
        metadata["purpose"] = "Entertainment"
    elif any(word in text.lower() for word in ["education", "school", "university", "learn"]):
        metadata["purpose"] = "Education"
    
    # Emotional tone detection
    if any(word in text.lower() for word in ["funny", "joke", "laugh", "humor"]):
        metadata["emotional_tone"] = "Humorous"
    elif any(word in text.lower() for word in ["serious", "important", "critical", "urgent"]):
        metadata["emotional_tone"] = "Serious"
    elif any(word in text.lower() for word in ["inspire", "motivate", "encourage", "hope"]):
        metadata["emotional_tone"] = "Inspiring"
    
    return metadata

def extract_metadata_advanced(text, model="gemini-1.5-flash"):
    llm = get_llm(model)
    
    prompt = f"""Analyze the text and extract metadata. Respond in JSON with:
    - domain (General, Medical, Technical, Legal, Business, Education, Entertainment)
    - tone (Formal, Informal, Neutral)
    - time_period (Contemporary, Historical, Futuristic)
    - region (specific region if mentioned)
    - audience (Children, Teens, Adults, Seniors, Academics)
    - complexity (Simple, Medium, Advanced)
    - purpose (Entertainment, Education, Business, Legal)
    - emotional_tone (Neutral, Humorous, Serious, Inspiring)

    Text:
    {text}
    """
    
    response = llm.generate_content(prompt)
    raw_response = response.text.strip()
    
    # Try to parse JSON
    try:
        # Attempt to find JSON in the response
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start != -1 and end != -1:
            json_str = raw_response[start:end+1]
            return json.loads(json_str)
    except:
        pass
    
    # Fallback to basic extraction
    return extract_metadata_basic(text)

def extract_metadata(text, mode="basic"):
    if mode == "basic":
        return extract_metadata_basic(text)
    elif mode == "advanced":
        return extract_metadata_advanced(text)
    else:  # agentic
        return extract_metadata_advanced(text, "gemini-2.5-flash-preview-05-20")