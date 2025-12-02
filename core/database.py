import sqlite3
import os
from datetime import datetime
import json

DB_PATH = "transcendai.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create projects table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        project_type TEXT,
        metadata_profile TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create translations table with all columns
    c.execute('''CREATE TABLE IF NOT EXISTS translations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        source_text TEXT NOT NULL,
        source_lang TEXT,
        target_lang TEXT,
        translation TEXT NOT NULL,
        metadata TEXT,
        framework TEXT,
        mode TEXT,
        intensity INTEGER,
        version INTEGER,
        parent_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )''')
    
    conn.commit()
    conn.close()

def create_project(name, project_type="Document", metadata_profile="{}"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO projects (name, project_type, metadata_profile) VALUES (?, ?, ?)",
              (name, project_type, metadata_profile))
    project_id = c.lastrowid
    conn.commit()
    conn.close()
    return project_id

def delete_project(project_id):
    """Delete project and all its translations"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM translations WHERE project_id = ?", (project_id,))
    c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

def get_project(project_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = c.fetchone()
    conn.close()
    return project

def list_projects():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, project_type, created_at FROM projects ORDER BY created_at DESC")
    projects = c.fetchall()
    conn.close()
    return projects

def save_translation(project_id, source_text, source_lang, target_lang, 
                    translation, metadata, framework, mode, intensity, version, parent_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    metadata_str = json.dumps(metadata) if isinstance(metadata, dict) else metadata
    c.execute('''INSERT INTO translations 
              (project_id, source_text, source_lang, target_lang, translation, 
               metadata, framework, mode, intensity, version, parent_id) 
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (project_id, source_text, source_lang, target_lang, translation, 
               metadata_str, framework, mode, intensity, version, parent_id))
    translation_id = c.lastrowid
    conn.commit()
    conn.close()
    return translation_id

def get_translation_history(project_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, source_text, source_lang, target_lang, translation, 
               metadata, framework, mode, intensity, version, 
               datetime(created_at, 'localtime') as formatted_date
        FROM translations 
        WHERE project_id = ? 
        ORDER BY created_at DESC
    """, (project_id,))
    history = c.fetchall()
    conn.close()
    return history

def delete_translation(translation_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM translations WHERE id = ?", (translation_id,))
    conn.commit()
    conn.close()

def get_translation(translation_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM translations WHERE id = ?", (translation_id,))
    translation = c.fetchone()
    conn.close()
    return translation

# Initialize database on import
init_db()