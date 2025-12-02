# history_view.py
import streamlit as st
from core.database import get_translation_history, delete_translation
from datetime import datetime
import json

def format_history(history):
    """Format history entries for display"""
    formatted = []
    for entry in history:
        formatted.append({
            "id": entry[0],
            "source_text": entry[1],
            "source_lang": entry[2],
            "target_lang": entry[3],
            "translation": entry[4],
            "metadata": json.loads(entry[5]) if entry[5] else {},
            "framework": entry[6],
            "mode": entry[7],
            "intensity": entry[8],
            "version": entry[9],
            "date": entry[10]
        })
    return formatted

def render_history_view(project):
    st.title(f"📜 Translation History - {project['name']}")
    
    # Get history from database
    history = get_translation_history(project["id"])
    formatted_history = format_history(history)
    
    if not formatted_history:
        st.info("No translation history yet. Start translating!")
        if st.button("Start Translating"):
            st.session_state.current_step = "translate"
            st.rerun()
        return
    
    # Download option
    def get_history_text():
        text = f"Translation History for {project['name']}\n"
        text += "="*50 + "\n"
        for entry in formatted_history:
            text += f"\n=== Version {entry['version']} ===\n"
            text += f"Date: {entry['date']}\n"
            text += f"Mode: {entry['mode']}\n"
            text += f"Framework: {entry['framework']}\n"
            text += f"Intensity: {entry['intensity']}\n\n"
            text += f"From: {entry['source_lang']} → To: {entry['target_lang']}\n\n"
            text += "Source Text:\n"
            text += f"{entry['source_text']}\n\n"
            text += "Translation:\n"
            text += f"{entry['translation']}\n\n"
            text += "="*50 + "\n"
        return text
    
    st.download_button(
        label="📥 Download Full History",
        data=get_history_text(),
        file_name=f"{project['name']}_history.txt",
        mime="text/plain"
    )
    
    # Display history
    st.markdown("### Recent Translations")
    for entry in formatted_history:
        with st.expander(f"Version {entry['version']} - {entry['mode']} - {entry['date']}"):
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("**Source Text**")
                st.text(entry["source_text"])
            with col2:
                st.markdown("**Translation**")
                st.text(entry["translation"])
            
            st.markdown(f"**Details:** {entry['framework']} | Intensity: {entry['intensity']}")
            
            if st.button(f"Delete this version", key=f"delete_{entry['id']}"):
                delete_translation(entry["id"])
                st.success("Translation deleted!")
                time.sleep(1)
                st.rerun()
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✍️ New Translation"):
            st.session_state.current_step = "translate"
            st.rerun()
    with col2:
        if st.button("← Back to Projects"):
            st.session_state.current_step = "project_select"
            st.rerun()