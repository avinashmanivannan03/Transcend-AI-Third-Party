import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import time
import logging
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class TranslationAgent:
    """Proper multi-agent implementation with accurate outputs"""
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def _get_response(self, prompt: str) -> str:
        """Get clean response from Gemini"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 2048
                }
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise

    def enrich_context(self, text: str, source_lang: str, target_lang: str, metadata: Dict) -> Dict:
        """Context enrichment agent with proper output"""
        prompt = f"""As a Context Specialist, analyze this translation context:

Source: {source_lang} → Target: {target_lang}
Text: {text}
Metadata: {json.dumps(metadata, indent=2)}

Provide SPECIFIC analysis about:
1. Cultural considerations for {target_lang} speakers
2. Domain-specific terminology needed
3. Audience-appropriate language for {metadata.get('audience', 'Adults')}
4. Regional variations to consider
5. Potential translation challenges

Return ONLY a JSON object with these keys:
- cultural_considerations (array)
- domain_terminology (array)
- audience_needs (string)
- regional_variations (string)
- challenges (string)"""

        try:
            response = self._get_response(prompt)
            # Ensure proper JSON format
            if not response.startswith('{'):
                response = '{' + response.split('{', 1)[-1]
                response = response.rsplit('}', 1)[0] + '}'
            return json.loads(response)
        except Exception as e:
            logger.error(f"Context enrichment failed: {str(e)}")
            return {
                "error": str(e),
                "fallback": "Using basic context"
            }

    def translate(self, text: str, context: Dict, metadata: Dict) -> str:
        """Translation agent with context awareness"""
        prompt = f"""As a Senior Translator, translate this text to {context.get('target_lang', '')}:

Source Text: {text}

Context Analysis:
{json.dumps(context, indent=2)}

Requirements:
- Domain: {metadata.get('domain', 'General')}
- Tone: {metadata.get('tone', 'Neutral')}
- Audience: {metadata.get('audience', 'Adults')}

Return ONLY the translated text with NO additional commentary."""

        try:
            return self._get_response(prompt)
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise

    def review_quality(self, source: str, translation: str, context: Dict) -> str:
        """Quality review agent with proper validation"""
        prompt = f"""As a Quality Reviewer, validate this translation:

Source: {source}
Translation: {translation}

Context:
{json.dumps(context, indent=2)}

Check for:
1. Accuracy to source meaning
2. Tone consistency
3. Natural flow in target language

If changes are needed, return the IMPROVED translation.
If acceptable, return the ORIGINAL translation.

Return ONLY the final text with NO commentary."""

        try:
            return self._get_response(prompt)
        except Exception as e:
            logger.error(f"Quality review failed: {str(e)}")
            return translation  # Return original if review fails

    def adapt_culturally(self, text: str, context: Dict, metadata: Dict) -> str:
        """Cultural adaptation agent"""
        prompt = f"""As a Cultural Expert, adapt this text for {metadata.get('region', 'Global')}:

Text: {text}

Context:
{json.dumps(context, indent=2)}

Guidelines:
1. Localize expressions appropriately
2. Adapt cultural references
3. Maintain original meaning
4. Preserve {metadata.get('tone', 'Neutral')} tone

Return ONLY the adapted text with NO commentary."""

        try:
            return self._get_response(prompt)
        except Exception as e:
            logger.error(f"Cultural adaptation failed: {str(e)}")
            return text  # Return original if adaptation fails

def run_crewai_translation(text: str, source_lang: str, target_lang: str, 
                          metadata: Dict, intensity: int = 3, feedback: Optional[str] = None) -> Dict:
    """Complete multi-agent workflow with proper outputs"""
    agent = TranslationAgent()
    result = {
        "translation": "",
        "context": {},
        "metadata": metadata,
        "warnings": []
    }

    try:
        # 1. Context Enrichment
        context = agent.enrich_context(text, source_lang, target_lang, metadata)
        if "error" in context:
            raise ValueError(context["error"])
        result["context"] = context
        result["context"]["source_lang"] = source_lang
        result["context"]["target_lang"] = target_lang

        # 2. Initial Translation
        translation = agent.translate(text, context, metadata)
        result["translation"] = translation

        # 3. Quality Review (intensity >= 2)
        if intensity >= 2:
            reviewed = agent.review_quality(text, translation, context)
            if reviewed != translation:
                result["translation"] = reviewed
                result["context"]["reviewed"] = True

        # 4. Cultural Adaptation (intensity >= 3)
        if intensity >= 3:
            adapted = agent.adapt_culturally(result["translation"], context, metadata)
            if adapted != result["translation"]:
                result["translation"] = adapted
                result["context"]["adapted"] = True

        return result

    except Exception as e:
        logger.error(f"Multi-agent workflow failed: {str(e)}")
        # Fallback to advanced translation
        return advanced_translation(text, source_lang, target_lang, metadata)

def advanced_translation(text: str, source_lang: str, target_lang: str, 
                        metadata: Dict) -> Dict:
    """Metadata-aware fallback translation"""
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""Translate this from {source_lang} to {target_lang}:

Text: {text}

Requirements:
- Domain: {metadata.get('domain', 'General')}
- Tone: {metadata.get('tone', 'Neutral')}
- Audience: {metadata.get('audience', 'Adults')}
- Purpose: {metadata.get('purpose', 'General')}

Return ONLY the translated text with NO additional content."""

        response = model.generate_content(prompt)
        return {
            "translation": response.text.strip(),
            "context": {"fallback": "Used advanced translation"},
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Advanced translation failed: {str(e)}")
        return {
            "translation": text,  # Return original as last resort
            "context": {"error": str(e)},
            "metadata": metadata
        }

def translate_text(text: str, source_lang: str, target_lang: str,
                  metadata: Dict, intensity: int = 3) -> Dict:
    """Main entry point for CrewAI translation"""
    return run_crewai_translation(text, source_lang, target_lang, metadata, intensity)