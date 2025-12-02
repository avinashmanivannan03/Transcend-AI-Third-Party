import google.generativeai as genai
from dotenv import load_dotenv
import os
import json

load_dotenv()

def get_llm(model_name="gemini-2.5-flash-preview-05-20"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(model_name=model_name)
    return model

def adapt_text(text, region, model="gemini-2.5-flash-preview-05-20", audience="Adults", purpose="General"):
    llm = get_llm(model)
    
    prompt = f"""Adapt the following text for cultural context. Follow these guidelines:
    
    1. Region: {region}
    2. Target Audience: {audience}
    3. Purpose: {purpose}
    
    Cultural adaptation should include:
    - Using region-specific idioms and expressions
    - Adjusting references to local customs/traditions
    - Adapting measurements, dates, and formats
    - Modifying humor to be culturally appropriate
    
    Return ONLY the adapted text.
    
    Text to adapt:
    \"\"\"{text}\"\"\"
    """
    
    response = llm.generate_content(prompt)
    return response.text.strip()

def cultural_adaptation_analysis(text, region):
    llm = get_llm("gemini-2.5-flash-preview-05-20")
    
    prompt = f"""Analyze this text for cultural adaptation needs in {region}:
    {text}
    
    Respond in JSON format with:
    - cultural_issues: list of potential cultural issues
    - adaptation_suggestions: list of adaptation suggestions
    - cultural_markers: list of region-specific features used
    - complexity_score: 1-10 rating of cultural complexity
    
    Return ONLY the JSON object.
    """
    
    response = llm.generate_content(prompt)
    raw_response = response.text.strip()
    
    try:
        # Attempt to find JSON in the response
        start = raw_response.find("{")
        end = raw_response.rfind("}")
        if start != -1 and end != -1:
            json_str = raw_response[start:end+1]
            return json.loads(json_str)
    except:
        return {
            "cultural_issues": ["Unknown cultural conflicts"],
            "adaptation_suggestions": ["Apply general cultural adaptation"],
            "complexity_score": 5
        }