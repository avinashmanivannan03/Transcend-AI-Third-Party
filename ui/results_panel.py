import streamlit as st
import time
import json
from datetime import datetime
from core.database import get_translation_history, save_translation
from services.cultural_adaptation import cultural_adaptation_analysis

def render_results_panel(project):
    # Format history for download
    def format_history(history):
        output = []
        for idx, item in enumerate(history):
            output.append(f"=== Version {item.get('version', idx+1)} ===")
            output.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            output.append(f"Mode: {item.get('mode', 'N/A')}")
            output.append(f"Framework: {item.get('framework', 'N/A')}")
            output.append(f"Intensity: {item.get('intensity', 'N/A')}")
            output.append("\nSource Language: " + str(item.get('source_lang', 'Auto')))
            output.append("Target Language: " + str(item.get('target_lang', 'N/A')))
            output.append("\nSource Text:")
            output.append(str(item.get('text', 'No source text available')))
            output.append("\nTranslation:")
            output.append(str(item.get('translation', 'No translation available')))
            
            if item.get('context'):
                output.append("\n🧠 Enriched Context Analysis")
                context = item['context']
                if isinstance(context, dict):
                    # Source Text
                    output.append("\n📝 Source Text:")
                    output.append(f"- {str(context.get('source_text', 'No source text'))}")
                    
                    # Languages
                    if 'languages' in context:
                        langs = context['languages']
                        output.append("\n🌐 Languages:")
                        output.append(f"- Source: {str(langs.get('source', 'Unknown'))}")
                        output.append(f"- Target: {str(langs.get('target', 'Unknown'))}")
                    
                    # Metadata
                    if 'metadata' in context:
                        output.append("\n📁 Metadata:")
                        metadata = context['metadata']
                        for key, value in metadata.items():
                            output.append(f"- {key}: {str(value)}")
                    
                    # Analysis Breakdown
                    if 'enriched_analysis' in context:
                        analysis = context['enriched_analysis']
                        output.append("\n📊 Analysis Breakdown:")
                        
                        # Relationship Analysis
                        if 'relationship_analysis' in analysis:
                            output.append("\n🔹 Relationship Analysis:")
                            output.append(str(analysis['relationship_analysis']))
                        
                        # Cultural Considerations
                        if 'cultural_considerations' in analysis:
                            output.append("\n🔹 Cultural Considerations:")
                            for idx, consideration in enumerate(analysis['cultural_considerations'], 1):
                                output.append(f"{idx}. {str(consideration)}")
                        
                        # Domain Terminology
                        if 'domain_terminology' in analysis:
                            output.append("\n🔹 Key Terms:")
                            for term in analysis['domain_terminology']:
                                # Split term and translation if present
                                parts = str(term).split('(')
                                if len(parts) > 1:
                                    original = parts[0].strip()
                                    translation = parts[1].strip().rstrip(')')
                                    output.append(f"- {original}: {translation}")
                                else:
                                    output.append(f"- {term}")
                        
                        # Formatting Requirements
                        if 'formatting_requirements' in analysis:
                            output.append("\n🔹 Formatting Needs:")
                            output.append(str(analysis['formatting_requirements']))
                        
                        # Translation Challenges
                        if 'translation_challenges' in analysis:
                            output.append("\n🔹 Translation Challenges:")
                            for idx, challenge in enumerate(analysis['translation_challenges'], 1):
                                output.append(f"{idx}. {str(challenge)}")
                        
                        # Regional Variations
                        if 'regional_variations' in analysis:
                            output.append("\n🔹 Regional Notes:")
                            output.append(str(analysis['regional_variations']))
                        
                        # Communication Medium
                        if 'communication_medium' in analysis:
                            output.append("\n🔹 Best Format:")
                            output.append(str(analysis['communication_medium']))
                        
                        # Expected Response
                        if 'expected_response' in analysis:
                            output.append("\n🔹 Expected Outcome:")
                            output.append(str(analysis['expected_response']))
                else:
                    output.append(str(context))
                
            if item.get('metadata'):
                output.append("\nMetadata:")
                output.append(json.dumps(item['metadata'], indent=2))
            
            if item.get('cultural_analysis'):
                output.append("\nCultural Analysis:")
                output.append(json.dumps(item['cultural_analysis'], indent=2))
                
            if item.get('feedback'):
                output.append("\nUser Feedback:")
                output.append(json.dumps(item['feedback'], indent=2))
                
            output.append("\n" + "="*50 + "\n")
        return "\n".join(output)
    
    # Enhanced language detection
    def detect_language_mismatch(translation, target_lang):
        if not translation or not target_lang:
            return False
            
        # Extract translation text if it's a dictionary
        if isinstance(translation, dict):
            translation = translation.get("translation", "")
        
        if not isinstance(translation, str):
            return False
            
        target_lang = target_lang.lower()
        translation = translation.lower()
        
        # Language-specific character checks
        if "tamil" in target_lang:
            # Tamil Unicode block: 0B80–0BFF
            return not any('\u0B80' <= char <= '\u0BFF' for char in translation)
        elif "hindi" in target_lang:
            # Devanagari Unicode block: 0900–097F
            return not any('\u0900' <= char <= '\u097F' for char in translation)
        elif "russian" in target_lang:
            # Cyrillic Unicode block: 0400–04FF
            return not any('\u0400' <= char <= '\u04FF' for char in translation)
        elif "french" in target_lang:
            # Check for French accents
            return not any(char in "éèêàùç" for char in translation)
        elif "english" in target_lang:
            # Check for common English words
            english_words = ["the", "and", "for", "with", "this", "that"]
            return not any(word in translation for word in english_words)
        
        # Generic check for non-Latin characters
        if "latin" in target_lang or "roman" in target_lang:
            non_latin = any(ord(char) > 127 for char in translation)
            return non_latin
            
        return False
    
    st.title("📝 Translation Results")
    st.subheader(f"Project: {project['name']}")
    
    # Get latest translation
    if not project.get("history", []):
        st.warning("No translations yet. Go back to translate some text.")
        if st.button("← Back to Translation"):
            st.session_state.current_step = "translate"
            st.rerun()
        return
    
    latest = project["history"][-1]
    
    # Display latest translation
    st.markdown(f"### 🔤 Version {latest.get('version', 1)}")
    
    # Always show translation in a text area with default value
    translation_data = latest.get("translation", {"translation": "Translation not available"})
    if isinstance(translation_data, dict):
        translation_text = translation_data.get("translation", "Translation not available")
    else:
        translation_text = str(translation_data)
    
    if not translation_text or str(translation_text).strip() == "":
        translation_text = "Translation is empty - please try again"
    st.text_area("Translated Text:", 
                value=translation_text, 
                height=300, 
                key=f"result_{latest.get('version', 1)}")
    
    # Display agent info if applicable
    if latest.get("framework"):
        st.caption(f"Generated with {latest['framework']} at intensity {latest.get('intensity', 3)}/4")
    
    # Language confirmation and validation
    st.markdown("### 🌍 Language Confirmation")
    col_lang1, col_lang2 = st.columns(2)
    with col_lang1:
        st.info(f"**Source:** {latest.get('source_lang', 'Auto')}")
    with col_lang2:
        st.info(f"**Target:** {latest.get('target_lang', 'Unknown')}")
    
    # Detect potential language mismatch
    if detect_language_mismatch(translation_text, latest.get('target_lang')):
        st.warning("⚠️ Possible language mismatch detected! The translation doesn't appear to be in the target language.")
    
    # Show context and metadata
    with st.expander("🔍 View Context & Metadata", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📝 Source Text")
            st.text(latest.get("text", "No source text available"))
            
        with col2:
            st.markdown("#### 📊 Metadata")
            st.json(latest.get("metadata", {}))
            
            if latest.get("context"):
                st.markdown("#### 🧠 Enriched Context")
                st.text(latest["context"])
            else:
                st.info("No enriched context available for this translation")
    
    # Cultural adaptation analysis
    if (st.session_state.get("translation_mode", "") == "agentic" and 
        latest.get("intensity", 0) >= 3 and 
        project.get("metadata", {}).get("region", "Global") != "Global"):
        
        st.markdown("---")
        st.markdown("### 🌍 Cultural Adaptation Analysis")
        
        # Check if we already have analysis for this version
        if "cultural_analysis" not in latest:
            with st.spinner("Analyzing cultural adaptation..."):
                try:
                    analysis = cultural_adaptation_analysis(
                        translation_text,
                        project["metadata"].get("region", "Global")
                    )
                    # Save analysis to the history entry
                    latest["cultural_analysis"] = analysis
                    # Update session state
                    st.session_state.project = project
                except Exception as e:
                    st.error(f"Cultural analysis failed: {str(e)}")
                    latest["cultural_analysis"] = {
                        "error": f"Analysis failed: {str(e)}"
                    }
        else:
            analysis = latest["cultural_analysis"]
        
        # Display analysis
        analysis = latest.get("cultural_analysis", {})
        if analysis and not analysis.get("error"):
            col1, col2 = st.columns([1, 3])
            with col1:
                score = analysis.get("complexity_score", 5) if isinstance(analysis.get("complexity_score"), (int, float)) else 5
                st.metric("Cultural Fit Score", f"{score}/10", 
                          delta="Excellent" if score >= 8 else "Good" if score >= 6 else "Needs Work",
                          delta_color="normal" if score >= 6 else "inverse")
                
            with col2:
                st.progress(score/10, text=f"Cultural Adaptation: {score}/10")
            
            with st.expander("🔍 Detailed Cultural Analysis"):
                st.markdown("#### 🚩 Cultural Issues")
                if analysis.get("cultural_issues"):
                    for issue in analysis["cultural_issues"]:
                        st.write(f"- {issue}")
                else:
                    st.info("No significant cultural issues detected")
                
                st.markdown("#### 💡 Adaptation Suggestions")
                if analysis.get("adaptation_suggestions"):
                    for suggestion in analysis["adaptation_suggestions"]:
                        st.write(f"- {suggestion}")
                else:
                    st.info("No adaptation suggestions needed")
        elif analysis and analysis.get("error"):
            st.error(analysis["error"])
    
    # Feedback system
    st.markdown("---")
    st.markdown("### 💬 Feedback & Improvement")
    
    # Load previous feedback if exists
    prev_feedback = st.session_state.project.get("user_feedback", {})
    
    satisfaction = st.radio("Satisfaction Level:", 
                          ["😊 Perfect", "🙂 Good", "😐 Needs Improvement"], 
                          index=0, 
                          horizontal=True, 
                          key="satisfaction")
    
    if satisfaction != "😊 Perfect":
        issues = st.multiselect("What should be improved?",
                               ["Accuracy", "Tone", "Formality", "Cultural Relevance", 
                                "Word Choice", "Complexity", "Naturalness"],
                               default=prev_feedback.get("issues", []),
                               key="issues")
        
        custom_feedback = st.text_area("Specific suggestions:", 
                                      value=prev_feedback.get("custom", ""),
                                      key="custom_feedback")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retranslate with Feedback", use_container_width=True):
                # Save feedback to project metadata
                feedback_data = {
                    "issues": issues,
                    "custom": custom_feedback
                }
                
                # Save to project
                st.session_state.project["user_feedback"] = feedback_data
                
                # Save to this version
                latest["feedback"] = feedback_data
                
                # Set flag to use same text for retranslation
                st.session_state.retranslate_text = latest["text"]
                st.session_state.retranslate_mode = True
                
                # Increase agent intensity for retranslation
                if "intensity" in st.session_state:
                    st.session_state.intensity = min(4, st.session_state.intensity + 1)
                
                st.session_state.current_step = "translate"
                st.rerun()
        
        with col2:
            if st.session_state.get("translation_mode", "") == "agentic":
                if st.button("🧠 Switch Agent Framework", use_container_width=True):
                    current_framework = st.session_state.get("framework", "State Machine (LangGraph)")
                    new_framework = "Multi-Agent (CrewAI)" if "LangGraph" in current_framework else "State Machine (LangGraph)"
                    st.session_state.framework = new_framework
                    st.session_state.current_step = "translate"
                    st.rerun()
    
    # Display current feedback settings
    if prev_feedback:
        st.markdown("---")
        st.markdown("### ⚙️ Active Feedback Settings")
        st.info("These preferences will be applied to all translations until changed")
        with st.expander("View Active Feedback"):
            if prev_feedback.get("issues"):
                st.write("**Areas to improve:**")
                for issue in prev_feedback["issues"]:
                    st.write(f"- {issue}")
            if prev_feedback.get("custom"):
                st.write("**Specific instructions:**")
                st.write(prev_feedback["custom"])
            
            if st.button("🧹 Clear Feedback Settings"):
                st.session_state.project["user_feedback"] = {}
                st.rerun()
    
    # Version history
    if len(project["history"]) > 1:
        st.markdown("---")
        st.markdown("### ⏱️ Version History")
        
        # Sort history by version descending
        sorted_history = sorted(project["history"], key=lambda x: x.get("version", 0), reverse=True)
        
        for idx, item in enumerate(sorted_history):
            # Only show the first 5 versions by default
            if idx < 5 or st.session_state.get("show_all_versions", False):
                with st.expander(f"Version {item.get('version', idx+1)} - {item.get('framework', 'Basic')}"):
                    # Show the translation text
                    item_text = item.get("translation", "No translation available")
                    if not item_text or item_text.strip() == "":
                        item_text = "Translation is empty"
                        
                    st.text_area(f"Translation v{item.get('version', idx+1)}", 
                                value=item_text, 
                                height=150,
                                key=f"version_{item.get('version', idx+1)}")
                    
                    # Show language info
                    st.caption(f"From: {item.get('source_lang', 'Auto')} → To: {item.get('target_lang', 'Unknown')}")
                    
                    # Show cultural score if available
                    if "cultural_analysis" in item:
                        score = item["cultural_analysis"].get("complexity_score", 5)
                        st.caption(f"Cultural Fit: {score}/10")
                    
                    # Show feedback if available
                    if item.get("feedback"):
                        st.caption(f"Feedback applied: {', '.join(item['feedback'].get('issues', []))}")
                    
                    if st.button(f"Restore this Version", key=f"restore_{item.get('version', idx+1)}"):
                        # Create a new version based on this one
                        new_version = {
                            **item,
                            "version": latest["version"] + 1,
                            "parent_id": item["version"]
                        }
                        project["history"].append(new_version)
                        # Update session state
                        st.session_state.project = project
                        st.session_state.current_step = "results"
                        st.rerun()
        
        # Show more versions button if there are more than 5
        if len(sorted_history) > 5 and not st.session_state.get("show_all_versions", False):
            if st.button("Show All Versions"):
                st.session_state.show_all_versions = True
                st.rerun()
    
    # Download history button - always visible
    st.markdown("---")
    st.download_button(
        label="📥 Download Full History",
        data=format_history(project["history"]),
        file_name=f"{project['name']}_history.txt",
        mime="text/plain",
        use_container_width=True
    )
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✍️ New Translation", use_container_width=True):
            st.session_state.current_step = "translate"
            st.rerun()
    with col2:
        if st.button("⚙️ Change Settings", use_container_width=True):
            st.session_state.current_step = "metadata_setup"
            st.rerun()
    with col3:
        if st.button("🏁 Finish Session", use_container_width=True):
            st.session_state.current_step = "project_select"
            st.rerun()