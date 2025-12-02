# project_hub.py (updated)
import streamlit as st
from core.database import create_project, list_projects, get_project, delete_project
import time
from datetime import datetime

def render_project_hub():
    st.title("🚀 Translation Studio")
    st.subheader("Start or Continue a Translation Project")
    
    # Initialize session state
    if "current_step" not in st.session_state:
        st.session_state.current_step = "project_select"
    if "project" not in st.session_state:
        st.session_state.project = None
    
    # Project selection UI
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🆕 New Project")
        project_name = st.text_input("Project Name", "My Translation Project")
        project_type = st.selectbox("Project Type", 
                                  ["Document", "Website", "Book", "Marketing", "Other"])
        
        if st.button("Create Project"):
            project_id = create_project(project_name, project_type)
            st.session_state.project = {
                "id": project_id,
                "name": project_name,
                "type": project_type,
                "metadata": {},
                "history": []
            }
            st.session_state.current_step = "metadata_setup"
            st.rerun()
    
    with col2:
        st.markdown("### 📂 Existing Projects")
        projects = list_projects()
        
        if projects:
            selected_project = st.selectbox(
                "Select Project",
                [f"{p[1]} ({p[2]}) - {datetime.strptime(p[3], '%Y-%m-%d %H:%M:%S').strftime('%b %d, %Y')}" for p in projects],
                key="project_select"
            )
            
            if st.button("Open Project"):
                project_idx = [p[1] for p in projects].index(selected_project.split(' (')[0])
                project_data = get_project(projects[project_idx][0])
                st.session_state.project = {
                    "id": project_data[0],
                    "name": project_data[1],
                    "type": project_data[2],
                    "metadata": eval(project_data[3]) if project_data[3] else {},
                    "history": []
                }
                st.session_state.current_step = "history_view"  # Changed to history view first
                st.rerun()
                
            if st.button("Delete Project", type="primary"):
                project_idx = [p[1] for p in projects].index(selected_project.split(' (')[0])
                delete_project(projects[project_idx][0])
                st.success("Project deleted successfully!")
                time.sleep(1)
                st.rerun()
        else:
            st.info("No projects found. Create a new one!")
        
        st.markdown("---")
        st.markdown("### ⚡ Quick Session")
        if st.button("Temporary Translation (Not Saved)"):
            st.session_state.project = {
                "id": None,
                "name": "Temporary Session",
                "type": "Temporary",
                "metadata": {},
                "history": []
            }
            st.session_state.current_step = "metadata_setup"
            st.rerun()