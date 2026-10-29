"""
Сервис построения и ведения персональных маршрутов к профессии (Критерий 2).
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.models import Roadmap, RoadmapStep, CareerHypothesis
from app.services.graph_service import graph_service
from app.database import get_connection

class RoadmapService:
    @staticmethod
    def generate_roadmap_for_hypothesis(student_id: str, hypothesis_id: str) -> Roadmap:
        """
        Генерирует 4-шаговый практико-ориентированный маршрут для гипотезы,
        привязанный к объектам инфраструктуры Свердловской области.
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            # Проверяем, есть ли уже маршрут
            cursor.execute("SELECT id FROM roadmaps WHERE student_id = ? AND hypothesis_id = ?", (student_id, hypothesis_id))
            existing = cursor.fetchone()
            if existing:
                return RoadmapService.get_roadmap_by_id(existing["id"])

            # Получаем гипотезу
            cursor.execute("SELECT * FROM hypotheses WHERE id = ?", (hypothesis_id,))
            hyp_row = cursor.fetchone()
            if not hyp_row:
                raise ValueError(f"Гипотеза {hypothesis_id} не найдена")

            profession_id = hyp_row["profession_id"]
            profession_title = hyp_row["profession_title"]
            roadmap_id = f"rm_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()

            cursor.execute(
                """
                INSERT INTO roadmaps (id, student_id, hypothesis_id, profession_id, profession_title, progress_percentage, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (roadmap_id, student_id, hypothesis_id, profession_id, profession_title, now)
            )

            # Находим доступные профпробы и программы в Свердловской области для этой профессии
            trials = graph_service.get_trials_for_profession(profession_id)
            edu_programs = graph_service.get_edu_programs_for_profession(profession_id)

            chosen_trial = trials[0] if trials else None
            trial_org = graph_service.get_organization(chosen_trial["organization_id"]) if chosen_trial else None
            chosen_edu = edu_programs[0] if edu_programs else None
            edu_org = graph_service.get_organization(chosen_edu["organization_id"]) if chosen_edu else None

            # Партнерское предприятие
            partner_name = "Предприятия промышленного кластера СО"
            if chosen_edu and chosen_edu.get("partner_companies"):
                first_partner_org = graph_service.get_organization(chosen_edu["partner_companies"][0])
                if first_partner_org:
                    partner_name = first_partner_org["name"]

            # Формируем 4 ключевых этапа (Критерий 2)
            steps_data = [
                {
                    "stage": 1,
                    "title": "Этап 1: Экспресс-знакомство с профессией и видеоразбор задач",
                    "desc": f"Изучение реальных кейсов специалиста «{profession_title}», разбор типовых рабочих задач и онлайн-тест на базовые навыки.",
                    "org_id": None,
                    "org_name": "Платформа «Профессиональный навигатор»",
                    "org_city": "Свердловская область",
                    "org_addr": "Онлайн-модуль",
                    "format": "онлайн",
                    "trial_id": None,
                    "status": "in_progress"
                },
                {
                    "stage": 2,
                    "title": f"Этап 2: Реальная профессиональная проба — {chosen_trial['title'] if chosen_trial else 'Очная проба'}",
                    "desc": chosen_trial["description"] if chosen_trial else "Очное практическое занятие в лаборатории технопарка.",
                    "org_id": trial_org["id"] if trial_org else None,
                    "org_name": trial_org["name"] if trial_org else "Детский технопарк «Кванториум»",
                    "org_city": trial_org["city"] if trial_org else "Екатеринбург",
                    "org_addr": trial_org["address"] if trial_org else "г. Екатеринбург",
                    "format": chosen_trial["format"] if chosen_trial else "очно в лаборатории",
                    "trial_id": chosen_trial["id"] if chosen_trial else None,
                    "status": "pending"
                },
                {
                    "stage": 3,
                    "title": "Этап 3: Практический проект в детском технопарке / IT-Кубе",
                    "desc": f"Участие в проектной смене или регулярном инженерном кружке на базе площадки Свердловской области по треку «{profession_title}». Подготовка первого учебного проекта для защиты.",
                    "org_id": trial_org["id"] if trial_org else None,
                    "org_name": trial_org["name"] if trial_org else "Кванториум / IT-Куб",
                    "org_city": trial_org["city"] if trial_org else "Свердловская область",
                    "org_addr": trial_org["address"] if trial_org else "",
                    "format": "проектный интенсив",
                    "trial_id": None,
                    "status": "pending"
                },
                {
                    "stage": 4,
                    "title": f"Этап 4: Профессиональная траектория — {chosen_edu['title'] if chosen_edu else 'Профильное образование'}",
                    "desc": f"Выбор программы ({chosen_edu['level'] if chosen_edu else 'ВПО/СПО'}). Целевое обучение и карьерный трек в партнерстве с «{partner_name}».",
                    "org_id": edu_org["id"] if edu_org else None,
                    "org_name": edu_org["name"] if edu_org else "Ведущий ВУЗ/колледж СО",
                    "org_city": edu_org["city"] if edu_org else "Екатеринбург",
                    "org_addr": edu_org["address"] if edu_org else "",
                    "format": "образовательная траектория",
                    "trial_id": None,
                    "status": "pending"
                }
            ]

            steps: List[RoadmapStep] = []
            for s in steps_data:
                step_id = f"stp_{uuid.uuid4().hex[:8]}"
                cursor.execute(
                    """
                    INSERT INTO roadmap_steps (id, roadmap_id, stage_number, title, description, organization_id, organization_name, organization_city, organization_address, format, trial_id, status, is_custom_by_counselor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (step_id, roadmap_id, s["stage"], s["title"], s["desc"], s["org_id"], s["org_name"], s["org_city"], s["org_addr"], s["format"], s["trial_id"], s["status"])
                )
                steps.append(RoadmapStep(
                    id=step_id,
                    roadmap_id=roadmap_id,
                    stage_number=s["stage"],
                    title=s["title"],
                    description=s["desc"],
                    organization_id=s["org_id"],
                    organization_name=s["org_name"],
                    organization_city=s["org_city"],
                    organization_address=s["org_addr"],
                    format=s["format"],
                    trial_id=s["trial_id"],
                    status=s["status"]
                ))

            conn.commit()

            return Roadmap(
                id=roadmap_id,
                student_id=student_id,
                hypothesis_id=hypothesis_id,
                profession_id=profession_id,
                profession_title=profession_title,
                steps=steps,
                progress_percentage=0,
                created_at=now
            )

    @staticmethod
    def get_roadmap_by_id(roadmap_id: str) -> Optional[Roadmap]:
        """Получает полный маршрут со всеми шагами."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM roadmaps WHERE id = ?", (roadmap_id,))
            rm_row = cursor.fetchone()
            if not rm_row:
                return None

            cursor.execute(
                """
                SELECT * FROM roadmap_steps WHERE roadmap_id = ?
                ORDER BY stage_number ASC, id ASC
                """,
                (roadmap_id,)
            )
            step_rows = cursor.fetchall()
            steps = [
                RoadmapStep(
                    id=r["id"],
                    roadmap_id=r["roadmap_id"],
                    stage_number=r["stage_number"],
                    title=r["title"],
                    description=r["description"],
                    organization_id=r["organization_id"],
                    organization_name=r["organization_name"],
                    organization_city=r["organization_city"],
                    organization_address=r["organization_address"],
                    format=r["format"],
                    trial_id=r["trial_id"],
                    status=r["status"],
                    due_date=r["due_date"],
                    is_custom_by_counselor=bool(r["is_custom_by_counselor"]),
                    counselor_note=r["counselor_note"]
                )
                for r in step_rows
            ]

            completed_count = sum(1 for s in steps if s.status == "completed")
            progress = int((completed_count / len(steps)) * 100) if steps else 0

            return Roadmap(
                id=rm_row["id"],
                student_id=rm_row["student_id"],
                hypothesis_id=rm_row["hypothesis_id"],
                profession_id=rm_row["profession_id"],
                profession_title=rm_row["profession_title"],
                steps=steps,
                progress_percentage=progress,
                created_at=rm_row["created_at"]
            )

    @staticmethod
    def get_roadmaps_for_student(student_id: str) -> List[Roadmap]:
        """Возвращает все созданные маршруты для школьника."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM roadmaps WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
            rows = cursor.fetchall()
            return [RoadmapService.get_roadmap_by_id(r["id"]) for r in rows if r]

    @staticmethod
    def complete_step(step_id: str) -> Optional[RoadmapStep]:
        """Отмечает шаг маршрута как завершенный и обновляет прогресс."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE roadmap_steps SET status = 'completed' WHERE id = ?", (step_id,))
            cursor.execute("SELECT roadmap_id FROM roadmap_steps WHERE id = ?", (step_id,))
            row = cursor.fetchone()
            if not row:
                return None
            roadmap_id = row["roadmap_id"]

            # Пересчитываем прогресс
            cursor.execute("SELECT status FROM roadmap_steps WHERE roadmap_id = ?", (roadmap_id,))
            all_steps = cursor.fetchall()
            completed = sum(1 for s in all_steps if s["status"] == "completed")
            progress = int((completed / len(all_steps)) * 100) if all_steps else 0
            cursor.execute("UPDATE roadmaps SET progress_percentage = ? WHERE id = ?", (progress, roadmap_id))
            conn.commit()

        # Возвращаем обновленный шаг
        rm = RoadmapService.get_roadmap_by_id(roadmap_id)
        if rm:
            for s in rm.steps:
                if s.id == step_id:
                    return s
        return None
