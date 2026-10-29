"""
Сервис кабинета профориентолога (Критерий 4).
Позволяет просматривать подопечных школьников и гибко корректировать их маршруты.
"""
import uuid
from typing import List, Dict, Any, Optional
from app.models import RoadmapStep
from app.database import get_connection
from app.services.roadmap_service import RoadmapService

class CounselorService:
    @staticmethod
    def get_assigned_students(counselor_id: str = "counselor_default") -> List[Dict[str, Any]]:
        """Возвращает список прикрепленных школьников с их текущими статусами."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.name, s.city, s.grade, s.created_at,
                       COUNT(DISTINCT h.id) as hypotheses_count,
                       COUNT(DISTINCT r.id) as roadmaps_count,
                       COALESCE(AVG(r.progress_percentage), 0) as avg_progress
                FROM students s
                LEFT JOIN hypotheses h ON s.id = h.student_id
                LEFT JOIN roadmaps r ON s.id = r.student_id
                WHERE s.counselor_id = ?
                GROUP BY s.id
                ORDER BY s.created_at DESC
                """,
                (counselor_id,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "city": r["city"],
                    "grade": r["grade"],
                    "created_at": r["created_at"],
                    "hypotheses_count": r["hypotheses_count"],
                    "roadmaps_count": r["roadmaps_count"],
                    "avg_progress": int(r["avg_progress"])
                }
                for r in rows
            ]

    @staticmethod
    def add_custom_step_by_counselor(
        roadmap_id: str,
        title: str,
        description: str,
        organization_name: str,
        organization_city: str,
        format_type: str = "очно",
        counselor_note: str = "",
        due_date: str = ""
    ) -> RoadmapStep:
        """
        Профориентолог добавляет персональный шаг в маршрут школьника (Критерий 4).
        """
        step_id = f"stp_c_{uuid.uuid4().hex[:8]}"
        with get_connection() as conn:
            cursor = conn.cursor()
            # Определяем максимальный номер этапа
            cursor.execute("SELECT MAX(stage_number) as max_stage FROM roadmap_steps WHERE roadmap_id = ?", (roadmap_id,))
            max_row = cursor.fetchone()
            stage = (max_row["max_stage"] or 4) + 1

            cursor.execute(
                """
                INSERT INTO roadmap_steps (
                    id, roadmap_id, stage_number, title, description,
                    organization_name, organization_city, format,
                    status, due_date, is_custom_by_counselor, counselor_note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, 1, ?)
                """,
                (step_id, roadmap_id, stage, title, description, organization_name, organization_city, format_type, due_date, counselor_note)
            )
            conn.commit()

        rm = RoadmapService.get_roadmap_by_id(roadmap_id)
        for s in rm.steps:
            if s.id == step_id:
                return s
        raise RuntimeError("Не удалось создать шаг профориентолога")

    @staticmethod
    def update_step_by_counselor(
        step_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        counselor_note: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> bool:
        """Профориентолог корректирует параметры любого существующего шага."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM roadmap_steps WHERE id = ?", (step_id,))
            step = cursor.fetchone()
            if not step:
                return False

            new_title = title if title is not None else step["title"]
            new_desc = description if description is not None else step["description"]
            new_note = counselor_note if counselor_note is not None else step["counselor_note"]
            new_due = due_date if due_date is not None else step["due_date"]

            cursor.execute(
                """
                UPDATE roadmap_steps
                SET title = ?, description = ?, counselor_note = ?, due_date = ?, is_custom_by_counselor = 1
                WHERE id = ?
                """,
                (new_title, new_desc, new_note, new_due, step_id)
            )
            conn.commit()
            return True

    @staticmethod
    def delete_step_by_counselor(step_id: str) -> bool:
        """Профориентолог удаляет неактуальный шаг."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT roadmap_id FROM roadmap_steps WHERE id = ?", (step_id,))
            row = cursor.fetchone()
            if not row:
                return False
            roadmap_id = row["roadmap_id"]

            cursor.execute("DELETE FROM roadmap_steps WHERE id = ?", (step_id,))
            conn.commit()

        # Обновляем прогресс
        RoadmapService.get_roadmap_by_id(roadmap_id)
        return True

