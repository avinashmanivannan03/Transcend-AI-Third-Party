# main.py
import streamlit as st
from ui.project_hub import render_project_hub
from ui.metadata_studio import render_metadata_studio
from ui.translation_workshop import render_translation_workshop
from ui.results_panel import render_results_panel
from ui.history_view import render_history_view

# Page configuration
st.set_page_config(
    page_title="TranscendAI - Intelligent Translation Studio",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Debug function
def debug_info():
    if st.sidebar.checkbox("Show Debug Info"):
        st.sidebar.subheader("Session State")
        st.sidebar.subheader("Translation Debug")
        if st.session_state.current_step == "results" and st.session_state.project.get("history"):
            latest = st.session_state.project["history"][-1]
            st.sidebar.text_area("Latest Input", 
                                value=f"Source: {latest.get('source_lang')}\nTarget: {latest.get('target_lang')}\nText: {latest.get('text')}",
                                height=200)
            st.sidebar.text_area("Translation Result", 
                                value=latest.get('translation', 'No translation'), 
                                height=200)
        st.sidebar.json(st.session_state)
        
        if st.session_state.get("project"):
            st.sidebar.subheader("Project Data")
            st.sidebar.json(st.session_state.project)

# Initialize session state
if "current_step" not in st.session_state:
    st.session_state.current_step = "project_select"
if "project" not in st.session_state:
    st.session_state.project = None
if "translation_mode" not in st.session_state:
    st.session_state.translation_mode = "agentic"
if "intensity" not in st.session_state:
    st.session_state.intensity = 3
if "framework" not in st.session_state:
    st.session_state.framework = "LangGraph"
if "expert_agents" not in st.session_state:
    st.session_state.expert_agents = {
        "wikipedia_researcher": True,
        "sentiment_analyzer": True,
        "terminology_specialist": True,
        "coherence_checker": True
    }

if st.session_state.current_step == "project_select":
    render_project_hub()
elif st.session_state.current_step == "history_view":
    if st.session_state.project:
        render_history_view(st.session_state.project)
    else:
        st.warning("No project selected. Redirecting to project hub.")
        st.session_state.current_step = "project_select"
        st.rerun()
elif st.session_state.current_step == "metadata_setup":
    if st.session_state.project:
        render_metadata_studio(st.session_state.project)
    else:
        st.warning("No project selected. Redirecting to project hub.")
        st.session_state.current_step = "project_select"
        st.rerun()
elif st.session_state.current_step == "translate":
    if st.session_state.project:
        render_translation_workshop(st.session_state.project)
    else:
        st.warning("No project selected. Redirecting to project hub.")
        st.session_state.current_step = "project_select"
        st.rerun()
elif st.session_state.current_step == "results":
    if st.session_state.project:
        render_results_panel(st.session_state.project)
    else:
        st.warning("No project selected. Redirecting to project hub.")
        st.session_state.current_step = "project_select"
        st.rerun()

# Show debug info
debug_info()