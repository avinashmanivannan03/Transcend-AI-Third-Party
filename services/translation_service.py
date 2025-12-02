from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from core.state_graph import run_state_graph
import json
import time
import logging
import streamlit as st
from core.database import get_translation_history
from core.crewai_orchestrator import run_crewai_translation

load_dotenv()

def get_llm():
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3
        )
    except Exception as e:
        logging.error(f"LLM initialization failed: {str(e)}")
        raise ValueError(f"Failed to initialize language model: {str(e)}")

# Helper function to safely parse JSON
def safe_json_loads(data):
    try:
        if isinstance(data, str):
            return json.loads(data)
        return data
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Error processing data: {str(e)}")
        return None

def basic_translate(text, source_lang, target_lang, feedback=None):
    try:
        llm = get_llm()
        
        if source_lang == "Auto":
            source_desc = "the detected source language"
        else:
            source_desc = source_lang
        
        # Build prompt with clear instructions
        prompt = f"""You are a professional translator. Translate the following text from {source_desc} to {target_lang}.

Source Text:
{text}

Instructions:
1. Return ONLY the translated text
2. Do not include any additional explanations
3. Maintain proper {target_lang} grammar and syntax

{target_lang} translation:"""

        if feedback:
            prompt += "\n\nUser Feedback:\n"
            if feedback.get("issues"):
                prompt += f"- Please improve these aspects: {', '.join(feedback['issues'])}\n"
            if feedback.get("custom"):
                prompt += f"- Specific instructions: {feedback['custom']}\n"
        
        response = llm.invoke(prompt)
        
        if not response or not hasattr(response, 'content'):
            raise ValueError("Invalid response from language model")
            
        translation = response.content.strip()
        if not translation:
            raise ValueError("Empty translation received")
            
        return {
            'translation': translation,
            'context': "Basic Mode Translation",
            'metadata': {"mode": "basic"}
        }
    except Exception as e:
        error_msg = f"Translation error: {str(e)}"
        logging.error(error_msg)
        return {
            'translation': error_msg,
            'context': None,
            'metadata': {"mode": "basic"}
        }

def advanced_translate(text, source_lang, target_lang, metadata, feedback=None):
    llm = get_llm()
    
    if source_lang == "Auto":
        source_desc = "the detected source language"
    else:
        source_desc = source_lang
    
    prompt = f"""Translate the following text from {source_desc} to {target_lang}:
    
    Text:
    {text}
    
    Metadata:
    - Domain: {metadata.get('domain', 'General')}
    - Tone: {metadata.get('tone', 'Neutral')}
    - Region: {metadata.get('region', 'Global')}
    - Audience: {metadata.get('audience', 'Adults')}
    - Purpose: {metadata.get('purpose', 'General')}
    """
    
    if feedback:
        prompt += "\n\nUser Feedback:\n"
        if feedback.get("issues"):
            prompt += f"- Please improve these aspects: {', '.join(feedback['issues'])}\n"
        if feedback.get("custom"):
            prompt += f"- Specific instructions: {feedback['custom']}\n"
    
    prompt += "\nReturn ONLY the translated text."
    
    response = llm.invoke(prompt)
    return {
        'translation': response.content.strip(),
        'context': None,
        'metadata': metadata
    }

def agentic_translate(text, source_lang, target_lang, metadata, framework, intensity=3, feedback=None):
    if source_lang == "Auto":
        source_lang = "Auto"
    
    if feedback:
        metadata["user_feedback"] = feedback
    
    try:
        if "LangGraph" in framework:
            return run_state_graph(text, metadata, source_lang, target_lang, intensity)
        else:  # CrewAI
            from core.crewai_orchestrator import run_crewai_translation
            translation = run_crewai_translation(text, source_lang, target_lang, metadata, intensity, feedback)
            
            # Validate translation result
            if not isinstance(translation, dict) or 'translation' not in translation:
                raise ValueError("Invalid translation response format")
            
            return {
                'translation': translation.get('translation', ""),
                'context': translation.get('context', None),
                'metadata': metadata
            }
    except json.JSONDecodeError:
        return {
            'translation': "Translation error: Invalid JSON response from translation service",
            'context': None,
            'metadata': metadata
        }
    except Exception as e:
        return {
            'translation': f"Translation error: {str(e)}",
            'context': None,
            'metadata': metadata
        }

# In your translation_service.py, modify the translate_text function:

def translate_text(text, source_lang, target_lang, metadata, mode="basic", framework="LangGraph", intensity=3, feedback=None):
    try:
        if mode == "basic":
            result = basic_translate(text, source_lang, target_lang, feedback)
            mode_str = "Basic Mode"
        elif mode == "advanced":
            result = advanced_translate(text, source_lang, target_lang, metadata, feedback)
            mode_str = "Advanced Mode"
        elif mode == "agentic":
            if "LangGraph" in framework:
                result = agentic_translate(text, source_lang, target_lang, metadata, framework, intensity, feedback)
                mode_str = f"Agentic Mode ({framework})"
            else:
                result = run_crewai_translation(text, source_lang, target_lang, metadata, intensity, feedback)
                mode_str = f"Agentic Mode (CrewAI)"
        elif mode == "expert":
            result = expert_translate(text, source_lang, target_lang, metadata, framework, intensity, feedback)
            mode_str = f"Expert Mode ({framework})"
        
        # Save to database if in Streamlit context
        try:
            if hasattr(st, 'session_state') and st.session_state.project and st.session_state.project.get("id"):
                from core.database import save_translation
                version = len(get_translation_history(st.session_state.project["id"])) + 1
                save_translation(
                    project_id=st.session_state.project["id"],
                    source_text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    translation=result['translation'],
                    metadata=result.get('metadata', metadata),
                    framework=framework,
                    mode=mode_str,
                    intensity=intensity,
                    version=version
                )
        except Exception as db_error:
            logging.error(f"Database save failed: {str(db_error)}")
        
        return result
    except Exception as e:
        return {
            'translation': f"Translation error: {str(e)}",
            'context': None,
            'metadata': metadata
        }