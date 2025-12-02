# metadata_studio.py
import streamlit as st
import json
from services.metadata_service import extract_metadata

def render_metadata_studio(project):
    st.title("⚙️ Translation Settings")
    st.subheader(f"Project: {project['name']}")
    
    st.markdown("### 🧠 Processing Mode")
    translation_mode = st.radio("Translation Mode:", 
                              ["Basic", "Advanced", "Agentic", "Expert"], 
                              horizontal=True, index=0)
    
    st.session_state.translation_model = "gemini-2.5-flash-preview-05-20"
    
    if translation_mode == "Basic":
        st.info("🔍 Basic Mode: Simple translation without metadata customization")
        
        st.markdown("### 🌍 Language Selection")
        col1, col2 = st.columns(2)
        with col1:
            source_lang = st.selectbox("From Language:", 
                                      ["Auto", "English", "Hindi", "Tamil", "Russian", "French"])
        with col2:
            target_lang = st.selectbox("To Language:", 
                                      ["Tamil", "Hindi", "English", "Russian", "French"])
        
        project["source_lang"] = source_lang
        project["target_lang"] = target_lang
        
        if st.button("💾 Save Settings & Continue"):
            st.session_state.translation_mode = translation_mode.lower()
            st.session_state.current_step = "translate"
            st.rerun()
        
        if st.button("← Back to Projects"):
            st.session_state.current_step = "project_select"
            st.rerun()
        return
    
    st.markdown("### 🔍 Metadata Configuration")
    metadata_source = st.radio("Metadata Source:", 
                             ["Auto-Extract", "Manual Input"], 
                             horizontal=True)
    
    metadata = project["metadata"]
    
    if metadata_source == "Auto-Extract":
        source_text = st.text_area("Enter text for metadata analysis:", height=150,
                                 placeholder="Paste some text to analyze...")
        
        if source_text:
            if st.button("Extract Metadata"):
                metadata = extract_metadata(source_text, "advanced")
                st.session_state.project["metadata"] = metadata
                st.success("Metadata extracted successfully!")
    else:
        col1, col2 = st.columns(2)
        with col1:
            metadata["audience"] = st.selectbox("Target Audience", 
                                              ["Adults", "Children", "Teens", "Seniors", "Academics"])
            metadata["complexity"] = st.select_slider("Complexity Level", 
                                                    ["Simple", "Medium", "Advanced"])
            metadata["domain"] = st.selectbox("Domain", 
                                            ["General", "Medical", "Technical", "Legal", "Business"])
            
        with col2:
            metadata["purpose"] = st.selectbox("Purpose", 
                                             ["General", "Entertainment", "Education", "Business", "Legal"])
            metadata["region"] = st.text_input("Region/Culture", "Global")
            metadata["tone"] = st.selectbox("Tone", 
                                          ["Formal", "Informal", "Neutral"])
            metadata["time_period"] = st.selectbox("Time Period", 
                                                 ["Contemporary", "Historical", "Futuristic"])
    
    if translation_mode in ["Agentic", "Expert"]:
        st.markdown("---")
        st.markdown("### 🤖 Agentic Options")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### AI Framework")
            framework = st.radio("Select:", 
                                ["LangGraph", "CrewAI"],
                                horizontal=True,
                                format_func=lambda x: f"{x} (LangGraph)" if x == "LangGraph" else f"{x} (CrewAI)")
        with col2:
            st.markdown("#### Processing Intensity")
            intensity = st.slider("Agent Steps", 1, 4, 3)
        st.session_state.framework = framework
        st.session_state.intensity = intensity
    
    if translation_mode == "Expert":
        st.markdown("---")
        st.markdown("### 🎓 Expert Options")
        st.markdown("#### Specialized Agents")
        
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Wikipedia Researcher", value=True, key="expert_agents.wikipedia_researcher")
            st.checkbox("Sentiment Analyzer", value=True, key="expert_agents.sentiment_analyzer")
        with col2:
            st.checkbox("Terminology Specialist", value=True, key="expert_agents.terminology_specialist")
            st.checkbox("Coherence Checker", value=True, key="expert_agents.coherence_checker")
        
        st.markdown("#### Translation Memory")
        st.checkbox("Enable Translation Memory", value=True, key="enable_translation_memory")
        st.checkbox("Enable Monolingual Validation", value=True, key="enable_monolingual_validation")
    
    st.markdown("### ⚙️ Current Metadata")
    st.json(metadata)
    
    if st.button("💾 Save Settings & Continue"):
        st.session_state.project["metadata"] = metadata
        st.session_state.translation_mode = translation_mode.lower()
        st.session_state.current_step = "translate"
        st.rerun()
    
    if st.button("← Back to Projects"):
        st.session_state.current_step = "project_select"
        st.rerun()