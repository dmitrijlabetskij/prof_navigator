"""
База данных SQLite для хранения состояния пользователей, гипотез, маршрутов и рефлексии.
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from app.config import DATABASE_PATH

@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Инициализация схемы БД."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            grade INTEGER NOT NULL,
            counselor_id TEXT DEFAULT 'counselor_default',
            created_at TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS diagnostics (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hypotheses (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            profession_id TEXT NOT NULL,
            profession_title TEXT NOT NULL,
            industry_id TEXT NOT NULL,
            industry_name TEXT NOT NULL,
            match_score INTEGER NOT NULL,
            explanation TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roadmaps (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            hypothesis_id TEXT NOT NULL,
            profession_id TEXT NOT NULL,
            profession_title TEXT NOT NULL,
            progress_percentage INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (hypothesis_id) REFERENCES hypotheses(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roadmap_steps (
            id TEXT PRIMARY KEY,
            roadmap_id TEXT NOT NULL,
            stage_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            organization_id TEXT,
            organization_name TEXT,
            organization_city TEXT,
            organization_address TEXT,
            format TEXT NOT NULL,
            trial_id TEXT,
            status TEXT DEFAULT 'pending',
            due_date TEXT,
            is_custom_by_counselor INTEGER DEFAULT 0,
            counselor_note TEXT,
            FOREIGN KEY (roadmap_id) REFERENCES roadmaps(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trial_feedbacks (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            trial_id TEXT NOT NULL,
            rating_interest INTEGER NOT NULL,
            difficulty_level TEXT NOT NULL,
            key_takeaway TEXT NOT NULL,
            future_readiness TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (step_id) REFERENCES roadmap_steps(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS partner_trial_overrides (
            trial_id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            verified_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            custom_slots_json TEXT
        )
        """)
        
        conn.commit()

# Инициализируем БД при импорте
init_db()
