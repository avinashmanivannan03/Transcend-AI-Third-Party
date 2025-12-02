from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
import json
import time
import re

load_dotenv()

class GraphState(TypedDict):
    query: str
    context: dict
    metadata: dict
    source_lang: str
    target_lang: str
    translation: Optional[str]
    adapted: Optional[str]
    validation: Optional[str]

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-05-20",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    )

def search_node(state: GraphState) -> GraphState:
    """Enhanced search node with comprehensive metadata collection"""
    return {
        **state,
        "context": {
            "source_text": state["query"],
            "metadata": {
                "domain": state["metadata"].get("domain", "General"),
                "tone": state["metadata"].get("tone", "Neutral"),
                "region": state["metadata"].get("region", "Global"),
                "audience": state["metadata"].get("audience", "Adults"),
                "purpose": state["metadata"].get("purpose", "General"),
                "feedback": state["metadata"].get("user_feedback", {})
            },
            "languages": {
                "source": state["source_lang"],
                "target": state["target_lang"]
            }
        }
    }

def enrich_node(state: GraphState) -> GraphState:
    """Comprehensive context enrichment with structured output"""
    llm = get_llm()
    ctx = state["context"]
    
    prompt = f"""**Context Enrichment Guide**

**Source Text**: {ctx['source_text']}
**Source Language**: {ctx['languages']['source']}
**Target Language**: {ctx['languages']['target']}

**Metadata**:
- Domain: {ctx['metadata']['domain']}
- Tone: {ctx['metadata']['tone']}
- Region: {ctx['metadata']['region']}
- Audience: {ctx['metadata']['audience']}
- Purpose: {ctx['metadata']['purpose']}

**Analysis Instructions**:
1. Analyze the relationship between speakers based on tone and content
2. Identify cultural references and adaptation needs
3. Extract domain-specific terminology requirements
4. Determine appropriate formatting and structure
5. Note any potential translation challenges
6. Consider regional linguistic variations

**Response Format**:
```json
{{
    "relationship_analysis": "Describe the likely relationship between speakers",
    "cultural_considerations": ["List important cultural aspects"],
    "domain_terminology": ["List domain-specific terms"],
    "formatting_requirements": "Note any special formatting needs",
    "translation_challenges": ["List potential translation difficulties"],
    "regional_variations": "Note any regional language variations",
    "communication_medium": "Suggest likely communication medium",
    "expected_response": "Describe the expected response pattern"
}}
Provide your analysis in valid JSON format only."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        print(f"Enrichment raw response: {content}")  # Debug print
        
        # Try to parse JSON
        try:
            enriched_data = json.loads(content)
            if not isinstance(enriched_data, dict):
                raise ValueError("Parsed content is not a dictionary")
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON-like structure
            # Look for JSON-like content in the response
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            if json_match:
                try:
                    enriched_data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    enriched_data = {
                        "error": "Could not parse JSON from response",
                        "raw_response": content
                    }
            else:
                enriched_data = {
                    "error": "No JSON-like content found in response",
                    "raw_response": content
                }
        
    except Exception as e:
        print(f"Enrichment error: {str(e)}")
        enriched_data = {
            "error": f"Enrichment failed: {str(e)}",
            "raw_response": response.content if 'response' in locals() else None
        }

    return {
        **state,
        "context": {
            **ctx,
            "enriched_analysis": enriched_data,
            "enrichment_timestamp": time.time()
        }
    }

def translate_node(state: GraphState) -> GraphState:
    """Enhanced translation with enriched context and language validation"""
    llm = get_llm()
    ctx = state["context"]

    # Build comprehensive translation prompt
    prompt = f"""**Translation Task**
    Source Language: {ctx['languages']['source']}
    Target Language: {ctx['languages']['target']}

    Source Text:
    {ctx['source_text']}

    Contextual Information:

    Domain: {ctx['metadata']['domain']}

    Tone: {ctx['metadata']['tone']}

    Region: {ctx['metadata']['region']}

    Audience: {ctx['metadata']['audience']}

    Purpose: {ctx['metadata']['purpose']}

    Enriched Analysis:
    {json.dumps(ctx.get('enriched_analysis', {}), indent=2)}

    Translation Guidelines:

    Preserve original meaning precisely

    Maintain specified tone and style

    Use appropriate domain terminology

    Adapt for cultural context

    Ensure natural flow in target language

    Strcitly Translate only the text provided in the source text. Don't add any additional text. Translate all text exactly as it is in the source text.


    Validate the translation is actually in {ctx['languages']['target']}

    User Feedback:
    {json.dumps(ctx['metadata']['feedback'], indent=2) if ctx['metadata']['feedback'] else "None"}

    Output Requirements:

    Return ONLY the translated text in {ctx['languages']['target']}

    Include NO additional commentary

    Ensure characters are appropriate for {ctx['languages']['target']}"""

    response = llm.invoke(prompt)
    translation = response.content.strip()

    # Basic language validation
    if not is_language_match(translation, ctx['languages']['target']):
        print("Language validation failed, retrying...")
        response = llm.invoke(f"Correct this translation to proper {ctx['languages']['target']}:\n{translation}")
        translation = response.content.strip()

    return {**state, "translation": translation}

def is_language_match(text: str, target_lang: str) -> bool:
    """Basic language validation"""
    if not text or not target_lang:
        return False

    target_lang = target_lang.lower()

    # Language-specific validation rules
    if "tamil" in target_lang:
        # Check for Tamil Unicode block
        return any('\u0B80' <= char <= '\u0BFF' for char in text)
    elif "hindi" in target_lang:
        # Check for Devanagari Unicode block
        return any('\u0900' <= char <= '\u097F' for char in text)
    elif "russian" in target_lang:
        # Check for Cyrillic Unicode block
        return any('\u0400' <= char <= '\u04FF' for char in text)
    elif "french" in target_lang:
        # Check for French accents
        return any(char in "éèêàùç" for char in text.lower())
    elif "english" in target_lang:
        # Check for common English words
        return any(word in text.lower() for word in ["the", "and", "for", "with"])

    # Default check for non-Latin scripts
    if "latin" not in target_lang:
        return not any(ord(char) < 128 for char in text if char.isalpha())

    return True

def adapt_node(state: GraphState) -> GraphState:
    """Optimized cultural adaptation with validation"""
    llm = get_llm()
    ctx = state["context"]

    prompt = f"""**Cultural Adaptation Task**
    Target Language: {ctx['languages']['target']}
    Target Region: {ctx['metadata']['region']}

    Original Translation:
    {state['translation']}

    Cultural Context:
    {json.dumps(ctx.get('enriched_analysis', {}).get('cultural_considerations', []), indent=2)}

    Adaptation Guidelines:

    Localize expressions and idioms

    Adapt cultural references appropriately

    Maintain original meaning

    Preserve {ctx['metadata']['tone']} tone

    Use region-specific formatting

    Ensure result is in {ctx['languages']['target']}

    User Feedback:
    {json.dumps({k: v for k, v in ctx['metadata']['feedback'].items()
    if 'cultural' in k.lower()}, indent=2) if ctx['metadata']['feedback'] else "None"}

    Output Requirements:

    Return ONLY the culturally adapted text in {ctx['languages']['target']}

    Include NO additional commentary"""

    response = llm.invoke(prompt)
    adapted = response.content.strip()

    # Validate language
    if not is_language_match(adapted, ctx['languages']['target']):
        print("Adaptation language validation failed, retrying...")
        response = llm.invoke(f"Convert this to proper {ctx['languages']['target']}:\n{adapted}")
        adapted = response.content.strip()

    return {**state, "adapted": adapted}

def validate_node(state: GraphState) -> GraphState:
    """Comprehensive quality validation"""
    llm = get_llm()
    text = state.get('adapted', state['translation'])
    ctx = state["context"]

    prompt = f"""**Quality Validation**
    Target Language: {ctx['languages']['target']}
    Target Region: {ctx['metadata']['region']}

    Text to Validate:
    {text}

    Validation Criteria:

    Language accuracy (must be proper {ctx['languages']['target']})

    Cultural appropriateness for {ctx['metadata']['region']}

    Tone consistency ({ctx['metadata']['tone']})

    Terminology correctness ({ctx['metadata']['domain']} domain)

    Natural flow and readability

    Evaluation:
    Respond ONLY with "GOOD" if all criteria pass, otherwise "BAD"."""

    response = llm.invoke(prompt)
    validation = response.content.strip().upper()

    return {**state, "validation": validation}

def build_graph(intensity=3):
    """Build optimized state graph"""
    builder = StateGraph(GraphState)

    # Core nodes
    builder.add_node("search", search_node)
    builder.add_node("enrich", enrich_node)
    builder.add_node("translate", translate_node)

    # Conditional nodes
    if intensity >= 3:
        builder.add_node("adapt", adapt_node)
    if intensity >= 4:
        builder.add_node("validate", validate_node)

    # Build edges
    builder.set_entry_point("search")
    builder.add_edge("search", "enrich")
    builder.add_edge("enrich", "translate")

    current = "translate"
    if intensity >= 3:
        builder.add_edge("translate", "adapt")
        current = "adapt"
    if intensity >= 4:
        builder.add_edge(current, "validate")
        builder.add_conditional_edges(
            "validate",
            lambda state: "restart" if "BAD" in state["validation"] else "end",
            {"restart": "translate", "end": END}
        )
    else:
        builder.add_edge(current, END)

    return builder.compile()

def run_state_graph(query, metadata, source_lang, target_lang, intensity=3):
    """Execute the state graph with comprehensive error handling"""
    start_time = time.time()

    init_state = {
        "query": query,
        "metadata": metadata,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "context": {},
        "translation": None,
        "adapted": None,
        "validation": None
    }

    try:
        graph = build_graph(intensity)
        result = graph.invoke(init_state)
        
        # Final validation
        final_translation = result.get("adapted", result["translation"])
        if not is_language_match(final_translation, target_lang):
            print("Final language validation failed, correcting...")
            llm = get_llm()
            response = llm.invoke(f"Convert this to proper {target_lang}:\n{final_translation}")
            final_translation = response.content.strip()
        
        print(f"Graph completed in {time.time() - start_time:.2f} seconds")
        return {
            'translation': final_translation,
            'context': result.get("context", {}),
            'metadata': metadata
        }
    except Exception as e:
        print(f"Graph error: {str(e)}")
        return {
            'translation': f"Translation error: {str(e)}",
            'context': {"error": str(e)},
            'metadata': metadata
        }