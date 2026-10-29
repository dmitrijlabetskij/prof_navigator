"""
Сервис обработки профориентационной диагностики школьника.
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.models import DiagnosticInput, StudentProfile
from app.database import get_connection

class DiagnosticService:
    @staticmethod
    def get_diagnostic_schema() -> Dict[str, Any]:
        """Возвращает структуру формы диагностики для мобильного интерфейса."""
        return {
            "cities": [
                "Екатеринбург",
                "Верхняя Пышма",
                "Первоуральск",
                "Нижний Тагил",
                "Каменск-Уральский",
                "Новоуральск",
                "Верхняя Салда"
            ],
            "grades": [8, 9, 10, 11],
            "interests": [
                {"id": "программирование", "label": "Программирование и ИТ"},
                {"id": "математика", "label": "Математика и аналитика данных"},
                {"id": "робототехника", "label": "Робототехника и мехатроника"},
                {"id": "электроника", "label": "Электроника и микросхемы"},
                {"id": "физика", "label": "Прикладная физика и инженерия"},
                {"id": "химия", "label": "Химия и материаловедение"},
                {"id": "биология", "label": "Биология и биотехнологии"},
                {"id": "медицина", "label": "Медицина и фарминдустрия"},
                {"id": "геология", "label": "Геология и полезные ископаемые"},
                {"id": "3d-моделирование", "label": "3D-моделирование и конструирование"}
            ],
            "klimov_types": [
                {"id": "знаковая система", "label": "Человек — Знаковая система (числа, код, схемы)"},
                {"id": "техника", "label": "Человек — Техника (машины, механизмы, роботы)"},
                {"id": "природа", "label": "Человек — Природа (биология, химия, геология)"},
                {"id": "исследование", "label": "Человек — Исследование (эксперименты, наука)"}
            ],
            "holland_types": [
                {"id": "I", "label": "Исследовательский тип (Investigative)"},
                {"id": "R", "label": "Реалистический / практический тип (Realistic)"},
                {"id": "C", "label": "Конвенциональный / системный тип (Conventional)"},
                {"id": "E", "label": "Предприимчивый / организаторский тип (Enterprising)"}
            ]
        }

    @staticmethod
    def register_or_get_student(name: str, city: str, grade: int, student_id: str = None) -> StudentProfile:
        """Создает профиль школьника или получает существующий."""
        if not student_id:
            student_id = f"st_{uuid.uuid4().hex[:8]}"

        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, city, grade, counselor_id, created_at FROM students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            if row:
                return StudentProfile(
                    id=row["id"],
                    name=row["name"],
                    city=row["city"],
                    grade=row["grade"],
                    counselor_id=row["counselor_id"],
                    created_at=row["created_at"]
                )
            cursor.execute(
                "INSERT INTO students (id, name, city, grade, counselor_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (student_id, name, city, grade, "counselor_default", now)
            )
            conn.commit()

        return StudentProfile(id=student_id, name=name, city=city, grade=grade, counselor_id="counselor_default", created_at=now)

    @staticmethod
    def save_diagnostic(student_id: str, diag_input: DiagnosticInput) -> str:
        """Сохранение диагностической анкеты."""
        diag_id = f"diag_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        data_json = json.dumps({
            "student_name": diag_input.student_name,
            "city": diag_input.city,
            "grade": diag_input.grade,
            "selected_interests": diag_input.selected_interests,
            "klimov_preferences": diag_input.klimov_preferences,
            "holland_codes": diag_input.holland_codes,
            "notes": diag_input.notes
        }, ensure_ascii=False)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO diagnostics (id, student_id, data_json, created_at) VALUES (?, ?, ?, ?)",
                (diag_id, student_id, data_json, now)
            )
            conn.commit()
        return diag_id
