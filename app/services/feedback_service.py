"""
Сервис рефлексии и обратной связи после профессиональной пробы (Критерий 3).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.models import TrialFeedback
from app.database import get_connection
from app.services.roadmap_service import RoadmapService

class FeedbackService:
    @staticmethod
    def submit_feedback(
        student_id: str,
        step_id: str,
        trial_id: str,
        rating_interest: int,
        difficulty_level: str,
        key_takeaway: str,
        future_readiness: str
    ) -> Dict[str, Any]:
        """
        Сохраняет обратную связь после профессиональной пробы (Критерий 3)
        и пересчитывает статус соответствующей профессиональной гипотезы.
        """
        fb_id = f"fb_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        # Автоматически отмечаем шаг пробы как выполненный
        RoadmapService.complete_step(step_id)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO trial_feedbacks (id, student_id, step_id, trial_id, rating_interest, difficulty_level, key_takeaway, future_readiness, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (fb_id, student_id, step_id, trial_id, rating_interest, difficulty_level, key_takeaway, future_readiness, now)
            )

            # Находим связанную гипотезу через roadmap
            cursor.execute(
                """
                SELECT r.hypothesis_id FROM roadmap_steps rs
                JOIN roadmaps r ON rs.roadmap_id = r.id
                WHERE rs.id = ?
                """,
                (step_id,)
            )
            rm_row = cursor.fetchone()
            new_hypothesis_status = "active"
            hypothesis_id = None

            if rm_row:
                hypothesis_id = rm_row["hypothesis_id"]
                # Определение нового статуса гипотезы на основе отзыва
                if future_readiness == "yes" and rating_interest >= 4:
                    new_hypothesis_status = "confirmed"  # Подтверждена на практике!
                elif future_readiness == "no" or rating_interest <= 2:
                    new_hypothesis_status = "rejected"   # Опровергнута школьником
                else:
                    new_hypothesis_status = "doubted"    # Требуется дополнительное исследование

                cursor.execute(
                    "UPDATE hypotheses SET status = ? WHERE id = ?",
                    (new_hypothesis_status, hypothesis_id)
                )

            conn.commit()

        feedback = TrialFeedback(
            id=fb_id,
            student_id=student_id,
            step_id=step_id,
            trial_id=trial_id,
            rating_interest=rating_interest,
            difficulty_level=difficulty_level,
            key_takeaway=key_takeaway,
            future_readiness=future_readiness,
            submitted_at=now
        )

        return {
            "feedback": feedback,
            "hypothesis_id": hypothesis_id,
            "new_hypothesis_status": new_hypothesis_status,
            "message": f"Обратная связь успешно принята. Статус гипотезы обновлен на: '{new_hypothesis_status}'."
        }

    @staticmethod
    def get_feedbacks_for_student(student_id: str):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM trial_feedbacks WHERE student_id = ? ORDER BY submitted_at DESC",
                (student_id,)
            )
            return [dict(r) for r in cursor.fetchall()]
