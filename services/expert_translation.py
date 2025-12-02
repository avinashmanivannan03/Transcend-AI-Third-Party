# expert_translation.py
import json
import requests
from typing import Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
import logging
from wikipediaapi import Wikipedia as WikipediaAPI
from langdetect import detect
from textblob import TextBlob
from deep_translator import GoogleTranslator
from langgraph.graph import StateGraph, END
from typing import Dict, Any, Optional, TypedDict
from typing import TypedDict, Optional, Dict, Any
from core.crewai_orchestrator import run_crewai_translation
from core.database import get_translation_history, save_translation
from langchain_google_genai import ChatGoogleGenerativeAI
from langdetect import detect
from textblob import TextBlob
from deep_translator import GoogleTranslator
import streamlit as st

load_dotenv()

logger = logging.getLogger(__name__)

class ExpertTranslationService:
    def __init__(self, model="gemini-flash-preview-0506", max_retries=3):
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3,
            max_retries=max_retries
        )
        self.max_retries = max_retries
        self.language_codes = {
            'ta': 'Tamil',
            'en': 'English',
            'hi': 'Hindi'
        }
        self.wiki = WikipediaAPI(
            language='en',
            extract_format='wiki',
            user_agent='CustomTranslationService/1.0'
        )
        self.translation_memory = {}
        
    def get_term_from_wikipedia(self, term: str, target_lang: str) -> Optional[str]:
        """Search for a term in Wikipedia and return the translation"""
        try:
            # First try English Wikipedia
            page = self.wiki.page(term)
            if page.exists():
                # Check if page has equivalent in target language
                lang_links = page.langlinks
                if target_lang.lower() in lang_links:
                    return lang_links[target_lang.lower()].title
                
                # If no direct link, try to find the term in the page text
                text = page.text[:2000]  # Limit to first 2000 chars
                prompt = f"""Find the most relevant translation for "{term}" in {target_lang} from this Wikipedia text:
                
                {text}
                
                Return ONLY the translated term in {target_lang} or "Not found" if not available."""
                
                response = self.llm.invoke(prompt)
                translation = response.content.strip()
                if translation.lower() != "not found":
                    return translation
                
            # Try target language Wikipedia directly
            target_wiki = WikipediaAPI(
                language=target_lang.lower(),
                extract_format='wiki',
                user_agent='CustomTranslationService/1.0'
            )
            search_results = target_wiki.search(term)
            if search_results:
                for result in search_results[:3]:  # Check top 3 results
                    page = target_wiki.page(result)
                    if page.exists():
                        return page.title
                        
            return None
        except Exception as e:
            logger.error(f"Wikipedia search failed: {str(e)}")
            return None
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text using TextBlob"""
        try:
            blob = TextBlob(text)
            sentiment = {
                "polarity": blob.sentiment.polarity,
                "subjectivity": blob.sentiment.subjectivity,
                "assessment": "positive" if blob.sentiment.polarity > 0 else 
                             "negative" if blob.sentiment.polarity < 0 else "neutral"
            }
            return sentiment
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {"polarity": 0, "subjectivity": 0, "assessment": "neutral"}
    
    def check_translation_memory(self, text: str, target_lang: str) -> Optional[str]:
        """Check if translation exists in memory"""
        key = f"{text[:100]}_{target_lang}"
        return self.translation_memory.get(key)
    
    def add_to_translation_memory(self, text: str, target_lang: str, translation: str):
        """Add translation to memory"""
        key = f"{text[:100]}_{target_lang}"
        self.translation_memory[key] = translation
    
    def monolingual_validation(self, text: str, target_lang: str) -> Dict:
        """Validate if text is in the correct target language and makes sense"""
        try:
            # Detect language
            detected_lang = detect(text)
            
            # Convert language code to full name
            lang_map = {
                'ta': 'Tamil',
                'en': 'English',
                'hi': 'Hindi'
            }
            target_lang_name = lang_map.get(target_lang.lower(), target_lang)
            
            # Check if detected language matches target language
            if detected_lang.lower() != target_lang.lower():
                return {
                    "valid": False,
                    "reason": "language_mismatch",
                    "detected_language": detected_lang,
                    "target_language": target_lang,
                    "message": f"Detected language ({detected_lang}) does not match target language ({target_lang})"
                }
            
            # Then check if the text makes sense
            prompt = f"""Does this text make sense in {target_lang}? 
            Respond with ONLY "YES" or "NO":
            
            {text}"""
            
            response = self.llm.invoke(prompt)
            makes_sense = response.content.strip().upper() == "YES"
            
            return {
                "valid": makes_sense,
                "reason": "makes_sense" if makes_sense else "nonsensical_text",
                "detected_language": detected_lang,
                "target_language": target_lang,
                "message": f"Text makes sense in {target_lang}" if makes_sense else 
                          f"Text does not make sense in {target_lang}"
            }
        except Exception as e:
            logger.error(f"Monolingual validation failed: {str(e)}")
            return {
                "valid": False,
                "reason": "validation_error",
                "detected_language": "unknown",
                "target_language": target_lang,
                "message": f"Validation failed: {str(e)}"
            }
    
    def expert_translate(self, text: str, source_lang: str, target_lang: str, 
                        metadata: Dict, framework: str, intensity: int = 3, 
                        feedback: Optional[Dict] = None) -> Dict:
        """Expert translation with all advanced features"""
        # Check translation memory first if enabled
        if st.session_state.get("enable_translation_memory", True):
            cached = self.check_translation_memory(text, target_lang)
            if cached:
                return {
                    'translation': cached,
                    'context': {"source": "translation_memory"},
                    'metadata': metadata
                }
        
        if framework == "LangGraph":
            return self.run_expert_state_graph(text, source_lang, target_lang, metadata, intensity, feedback)
        elif framework == "CrewAI":
            return self.run_expert_crewai(text, source_lang, target_lang, metadata, intensity, feedback)
        else:
            raise ValueError(f"Unsupported framework: {framework}")
    
    def run_expert_state_graph(self, text: str, source_lang: str, target_lang: str,
                             metadata: Dict, intensity: int, feedback: Optional[Dict]) -> Dict:
        """Run expert translation using LangGraph state machine"""
        try:
            # Initialize graph builder
            builder = StateGraph(Dict)
            
            # Define all nodes first
            def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Enhanced search with sentiment analysis"""
                sentiment = self.analyze_sentiment(state["query"])
                
                if not sentiment["polarity"]:
                    # If sentiment analysis failed or neutral, skip terminology and go directly to translation
                    return {
                        **state,
                        "query_sentiment": sentiment,
                        "context": {
                            "source_text": state["query"],
                            "skip_terminology": True,
                            "metadata": {
                                **state["metadata"],
                                "user_feedback": feedback,
                                "languages": {
                                    "source": state["source_lang"],
                                    "target": state["target_lang"]
                                },
                                "expert_agents": {
                                    "terminology_specialist": True,
                                    "coherence_checker": True
                                }
                            }
                        }
                    }
                else:
                    return {
                        **state,
                        "query_sentiment": sentiment,
                        "context": {
                            "source_text": state["query"],
                            "skip_terminology": False,
                            "metadata": {
                                **state["metadata"],
                                "user_feedback": feedback,
                                "languages": {
                                    "source": state["source_lang"],
                                    "target": state["target_lang"]
                                },
                                "expert_agents": {
                                    "terminology_specialist": True,
                                    "coherence_checker": True
                                }
                            }
                        }
                    }
            
            def translate_with_retry(state: Dict[str, Any]) -> Dict[str, Any]:
                """Translation with retry counter"""
                try:
                    translation = self.llm.invoke(state["query"])
                    return {**state, "translation": translation.content}
                except Exception as e:
                    logger.error(f"Translation failed: {str(e)}")
                    if state.get("retry_count", 0) < 3:
                        return {**state, "retry_count": state.get("retry_count", 0) + 1}
                    else:
                        raise Exception("Maximum retries exceeded")

            def terminology_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Handle specialized terminology"""
                # Get terminology specialist preference from context or default to True
                enable_terminology = state.get("context", {}).get("expert_agents", {}).get("terminology_specialist", True)
                if not enable_terminology:
                    return state
                    
                ctx = state["context"]
                text = ctx["source_text"]
                
                # Extract key terms
                prompt = f"""Extract domain-specific terms from this text that might need special translation:
                
                {text}
                
                Domain: {ctx["metadata"].get("domain", "General")}
                
                Return a JSON array of terms."""
                
                response = self.llm.invoke(prompt)
                terms = response.content.strip()
                
                # Parse terms
                try:
                    terms = json.loads(terms)
                    if not isinstance(terms, list):
                        terms = [terms]
                except json.JSONDecodeError:
                    terms = []
                
                term_translations = {}
                
                for term in terms:
                    # Try Wikipedia first
                    wiki_trans = self.get_term_from_wikipedia(term, ctx["languages"]["target"])
                    if wiki_trans:
                        term_translations[term] = wiki_trans
                        continue
                        
                    # Then try general translation
                    general_trans = GoogleTranslator(
                        source='auto',
                        target=ctx["languages"]["target"].lower()
                    ).translate(term)
                    
                    if general_trans and general_trans != term:
                        term_translations[term] = general_trans
            
                return {
                    **state,
                    "context": {
                        **ctx,
                        "term_translations": term_translations
                    }
                }

            def translate_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Expert translation with all features"""
                ctx = state["context"]
                
                # Build prompt with all contextual information
                prompt = f"""**Expert Translation Task**
                Source: {ctx["languages"]["source"]} - Target: {ctx["languages"]["target"]}
                
                Source Text:
                {ctx["source_text"]}
                
                Context:
                - Domain: {ctx["metadata"].get("domain", "General")}
                - Tone: {ctx["metadata"].get("tone", "Neutral")}
                - Audience: {ctx["metadata"].get("audience", "Adults")}
                - Purpose: {ctx["metadata"].get("purpose", "General")}
                
                Term Translations:
                {json.dumps(ctx.get("term_translations", {}), indent=2)}
                
                User Feedback:
                {json.dumps(ctx["metadata"].get("user_feedback", {}), indent=2)}
                
                Instructions:
                1. Use provided term translations where available
                2. Maintain original sentiment and tone
                3. Adapt for target audience and culture
                4. Ensure grammatical correctness
                5. Preserve technical meaning for domain-specific content
                
                Return ONLY the translated text in {ctx["languages"]["target"]}."""
                
                response = self.llm.invoke(prompt)
                translation = response.content.strip()
                
                # Validate language
                detected_lang = detect(translation)
                if detected_lang.lower() != ctx["languages"]["target"].lower():
                    logger.warning(f"Language mismatch detected: Expected {ctx['languages']['target']}, got {detected_lang}")
                    # Try to correct the language
                    prompt = f"Convert this text to proper {ctx['languages']['target']} while maintaining meaning:\n{translation}"
                    response = self.llm.invoke(prompt)
                    translation = response.content.strip()
                    
                    # Double-check after correction
                    detected_lang = detect(translation)
                    if detected_lang.lower() != ctx["languages"]["target"].lower():
                        logger.error(f"Language correction failed: Still not in {ctx['languages']['target']}")
                        return {**state, "translation": None, "error": "Language validation failed"}
                
                return {**state, "translation": translation}

            def coherence_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Check and improve text coherence"""
                # Get coherence checker preference from context or default to True
                enable_coherence = state.get("context", {}).get("expert_agents", {}).get("coherence_checker", True)
                if not enable_coherence:
                    return state
                
                ctx = state["context"]
                translation = state["translation"]
                
                prompt = f"""Improve the coherence and flow of this {ctx["languages"]["target"]} text:
                
                {translation}
                
                Requirements:
                - Maintain original meaning
                - Improve sentence transitions
                - Ensure logical flow
                - Keep {ctx["metadata"].get("tone", "Neutral")} tone
                
                Return ONLY the improved text."""
                
                response = self.llm.invoke(prompt)
                improved = response.content.strip()
                
                # Validate language after coherence improvement
                detected_lang = detect(improved)
                if detected_lang.lower() != ctx["languages"]["target"].lower():
                    logger.warning(f"Language mismatch after coherence improvement: Expected {ctx['languages']['target']}, got {detected_lang}")
                    # Try to correct the language
                    prompt = f"Convert this text to proper {ctx['languages']['target']} while maintaining coherence:\n{improved}"
                    response = self.llm.invoke(prompt)
                    improved = response.content.strip()
                    
                    # Double-check after correction
                    detected_lang = detect(improved)
                    if detected_lang.lower() != ctx["languages"]["target"].lower():
                        logger.error(f"Language correction failed after coherence: Still not in {ctx['languages']['target']}")
                        return {**state, "translation": None, "error": "Language validation failed after coherence"}
                
                return {**state, "translation": improved}

            def cultural_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
                """Analyze cultural fit and provide adaptation suggestions"""
                ctx = state["context"]
                translation = state["translation"]
                
                try:
                    prompt = f"""Analyze the cultural fit of this translation for {ctx["metadata"].get("region", "global")}:
                    
                    Original text: {state["query"]}
                    Translated text: {translation}
                    
                    Requirements:
                    1. Provide a complexity score (1-10)
                    2. List any cultural adaptations needed
                    3. Rate overall cultural fit (high/medium/low)
                    4. Identify any cultural sensitivities
                    
                    Return a JSON object with:
                    - complexity_score: number between 1-10
                    - cultural_adaptations: list of suggested changes
                    - overall_fit: "high", "medium", or "low"
                    - issues: list of cultural concerns
                    
                    Format:
                    {{
                        "complexity_score": 5,
                        "cultural_adaptations": [],
                        "overall_fit": "medium",
                        "issues": []
                    }}"""
                    
                    response = self.llm.invoke(prompt)
                    content = response.content.strip()
                    
                    try:
                        analysis = json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON response: {str(e)}\nContent: {content}")
                        # Return default analysis with error
                        return {**state, "cultural_analysis": {
                            "error": "Invalid JSON response",
                            "complexity_score": 5,
                            "cultural_adaptations": [],
                            "overall_fit": "medium",
                            "issues": ["Invalid JSON format in response"]
                        }}
                    
                    # Validate and sanitize analysis fields
                    if not isinstance(analysis.get("complexity_score"), (int, float)):
                        analysis["complexity_score"] = 5
                    elif not (1 <= analysis["complexity_score"] <= 10):
                        analysis["complexity_score"] = 5
                    
                    if analysis.get("overall_fit") not in ["high", "medium", "low"]:
                        analysis["overall_fit"] = "medium"
                    
                    if not isinstance(analysis.get("cultural_adaptations"), list):
                        analysis["cultural_adaptations"] = []
                    
                    if not isinstance(analysis.get("issues"), list):
                        analysis["issues"] = []
                    
                    return {**state, "cultural_analysis": analysis}
                except Exception as e:
                    logger.error(f"Cultural analysis failed: {str(e)}")
                    return {**state, "cultural_analysis": {
                        "error": str(e),
                        "complexity_score": 5,
                        "cultural_adaptations": [],
                        "overall_fit": "medium",
                        "issues": ["Analysis failed"]
                    }}
            
            # Add nodes to graph
            builder.add_node("search", search_node)
            builder.add_node("translate_with_retry", translate_with_retry)
            builder.add_node("terminology", terminology_node)
            builder.add_node("translate", translate_node)
            builder.add_node("coherence", coherence_node)
            builder.add_node("cultural_analysis", cultural_analysis_node)
            
            # Set entry point and build graph
            builder.set_entry_point("search")
            builder.add_edge("search", "translate_with_retry")
            builder.add_edge("translate_with_retry", "terminology")
            builder.add_edge("terminology", "translate")
            builder.add_edge("translate", "coherence")
            builder.add_edge("coherence", "cultural_analysis")
            
            graph = builder.compile()
            
            # Run graph with initial state
            init_state = {
                "query": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "metadata": metadata,
                "context": {},
                "translation": None
            }
            
            result = graph.invoke(init_state)
            
            return {
                'translation': result.get('translation', ''),
                'context': result.get('context', {}),
                'metadata': metadata,
                'analysis': result.get('cultural_analysis', None)
            }
        except Exception as e:
            logger.error(f"State graph execution failed: {str(e)}")
            return {
                'translation': None,
                'context': {'error': str(e)},
                'metadata': metadata
            }

    def run_expert_crewai(self, text: str, source_lang: str, target_lang: str,
                         metadata: Dict, intensity: int, feedback: Optional[Dict]) -> Dict:
        """Run expert translation using CrewAI orchestrator"""
        try:
            # Run CrewAI translation
            result = run_crewai_translation(
                text, source_lang, target_lang, metadata, intensity, feedback
            )
            
            # Add expert features
            if st.session_state.expert_agents.get("sentiment_analyzer", True):
                sentiment = self.analyze_sentiment(text)
                result["context"]["sentiment_analysis"] = sentiment
            
            if st.session_state.expert_agents.get("terminology_specialist", True):
                term_translations = self.get_term_translations(text, target_lang)
                result["context"]["term_translations"] = term_translations
            
            if st.session_state.expert_agents.get("coherence_checker", True):
                improved = self.improve_coherence(result["translation"])
                result["translation"] = improved
            
            return result
        except Exception as e:
            logger.error(f"CrewAI translation failed: {str(e)}")
            return {
                'translation': None,
                'context': {'error': str(e)},
                'metadata': metadata
            }

    def translate_with_context(self, text: str, source_lang: str, target_lang: str,
                             metadata: Dict) -> str:
        """Translate text with context and metadata"""
        try:
            # Convert language codes to full names
            source_lang_name = self.language_codes.get(source_lang.lower(), source_lang)
            target_lang_name = self.language_codes.get(target_lang.lower(), target_lang)
            
            prompt = f"""Translate this text from {source_lang_name} to {target_lang_name}:
            {text}
            
            Context:
            {json.dumps(metadata, indent=2)}
            
            Return ONLY the translation in {target_lang_name}.
            """
            
            # Add retry logic
            for attempt in range(self.max_retries):
                try:
                    response = self.llm.invoke(prompt)
                    translation = response.content.strip()
                    
                    # Validate language
                    if self.monolingual_validation(translation, target_lang):
                        return translation
                    
                except Exception as e:
                    logger.warning(f"Translation attempt {attempt + 1} failed: {str(e)}")
                    if attempt == self.max_retries - 1:
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            return ""
            
        except Exception as e:
            logger.error(f"Basic translation failed: {str(e)}")
            return ""
        """Translate text with context and metadata"""
        try:
            prompt = f"""Translate this text from {source_lang} to {target_lang}:
            {text}
            
            Context:
            {json.dumps(metadata, indent=2)}
            
            Return ONLY the translation."""
            
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Basic translation failed: {str(e)}")
            return ""

    def translate_text(self, text: str, source_lang: str, target_lang: str, 
                  metadata: Dict, mode: str = "basic", framework: str = "LangGraph", 
                  intensity: int = 3, feedback: Optional[Dict] = None) -> Dict:
        """Main translation function that selects the appropriate translation mode"""
        try:
            if mode == "expert":
                if framework == "LangGraph":
                    return self.run_expert_state_graph(
                        text, source_lang, target_lang, metadata, intensity, feedback
                    )
                elif framework == "CrewAI":
                    return self.run_expert_crewai(
                        text, source_lang, target_lang, metadata, intensity, feedback
                    )
                else:
                    raise ValueError(f"Unsupported framework: {framework}")
            else:
                # Basic translation
                translation = self.translate_with_context(
                    text, source_lang, target_lang, metadata
                )
                return {
                    'translation': translation,
                    'context': {},
                    'metadata': metadata
                }
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return {
                'translation': None,
                'context': {'error': str(e)},
                'metadata': metadata
            }
    # Close ExpertTranslationService class

# Standalone function for compatibility with imports
def translate_text(text: str, source_lang: str, target_lang: str, 
                  metadata: Dict, mode: str = "basic", framework: str = "LangGraph", 
                  intensity: int = 3, feedback: Optional[Dict] = None) -> Dict:
    """Standalone wrapper for the ExpertTranslationService.translate_text method"""
    service = ExpertTranslationService()
    return service.translate_text(
        text, source_lang, target_lang, metadata, mode, framework, intensity, feedback
    )