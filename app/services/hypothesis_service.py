"""
Сервис генерации 3–5 профессиональных гипотез на основе диагностики (Критерий 1).
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.models import DiagnosticInput, CareerHypothesis
from app.services.graph_service import graph_service
from app.database import get_connection

class HypothesisService:
    @staticmethod
    def generate_hypotheses(student_id: str, diag_input: DiagnosticInput) -> List[CareerHypothesis]:
        """
        Формирует от 3 до 5 ранжированных гипотез (Критерий 1)
        на основе взвешенного матчинга интересов, психотипа и приоритетов Свердловской области.
        """
        student_interests = set(i.lower() for i in diag_input.selected_interests)
        student_klimov = set(k.lower() for k in diag_input.klimov_preferences)
        student_holland = set(diag_input.holland_codes)
        student_city = diag_input.city

        scored_professions = []

        for p_id, prof in graph_service.professions.items():
            # 1. Степень совпадения интересов (40%)
            prof_tags = set(t.lower() for t in prof.get("interest_tags", []))
            common_interests = student_interests.intersection(prof_tags)
            interest_score = (len(common_interests) / max(len(prof_tags), 1)) * 40

            # 2. Совпадение типа Климова (25%)
            prof_klimov = set(k.lower() for k in prof.get("klimov_types", []))
            klimov_match = len(student_klimov.intersection(prof_klimov))
            klimov_score = min(klimov_match * 12.5, 25.0)

            # 3. Совпадение кодов Голланда (15%)
            prof_holland = set(prof.get("holland_codes", []))
            holland_match = len(student_holland.intersection(prof_holland))
            holland_score = min(holland_match * 7.5, 15.0)

            # 4. Региональный приоритет отрасли в Свердловской области (15%)
            industry = graph_service.industries.get(prof["industry_id"], {})
            priority_rank = industry.get("priority_rank", 3)
            # Ранг 1 -> 15 баллов, Ранг 2 -> 10 баллов, Ранг 3 -> 5 баллов
            region_score = 15 if priority_rank == 1 else (10 if priority_rank == 2 else 5)

            # 5. Географическая доступность площадок в Свердловской области (5%)
            trials = graph_service.get_trials_for_profession(p_id)
            geo_score = 5 if any(
                graph_service.get_organization(t["organization_id"]).get("city") == student_city
                for t in trials if graph_service.get_organization(t["organization_id"])
            ) else 3

            # Итоговый скор от 50 до 99%
            raw_score = interest_score + klimov_score + holland_score + region_score + geo_score
            # Нормализация для реалистичного восприятия школьником
            normalized_score = min(int(50 + (raw_score / 100.0) * 48), 98)

            # Генерация персонализированного обоснования
            ind_name = industry.get("name", "Региональная промышленность")
            matched_tags_str = ", ".join(common_interests) if common_interests else "твоим склонностям к анализу и практике"
            explanation = (
                f"Гипотеза сформирована на основе твоего интереса к направлениям ({matched_tags_str}). "
                f"В Свердловской области направление «{prof['title']}» входит в отраслевой кластер «{ind_name}» "
                f"с высоким спросом предприятий (СКБ Контур, ТМК, УГМК) и развитой сетью Кванториумов и ВУЗов."
            )

            scored_professions.append({
                "prof": prof,
                "industry": industry,
                "score": normalized_score,
                "explanation": explanation
            })

        # Сортировка по убыванию релевантности
        scored_professions.sort(key=lambda x: x["score"], reverse=True)

        # Выбираем от 3 до 5 гипотез (ровно 4 по умолчанию, либо 3-5 в зависимости от пула)
        selected_count = max(3, min(4, len(scored_professions)))
        top_candidates = scored_professions[:selected_count]

        hypotheses: List[CareerHypothesis] = []
        now = datetime.now(timezone.utc).isoformat()

        # Сохранение в БД
        with get_connection() as conn:
            cursor = conn.cursor()
            # Очищаем предыдущие гипотезы школьника при повторной диагностике
            cursor.execute("DELETE FROM hypotheses WHERE student_id = ?", (student_id,))

            for item in top_candidates:
                h_id = f"hyp_{uuid.uuid4().hex[:8]}"
                p = item["prof"]
                ind = item["industry"]
                hyp = CareerHypothesis(
                    id=h_id,
                    student_id=student_id,
                    profession_id=p["id"],
                    profession_title=p["title"],
                    industry_id=ind["id"],
                    industry_name=ind["name"],
                    match_score=item["score"],
                    explanation=item["explanation"],
                    status="active",
                    created_at=now
                )
                cursor.execute(
                    """
                    INSERT INTO hypotheses (id, student_id, profession_id, profession_title, industry_id, industry_name, match_score, explanation, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (hyp.id, hyp.student_id, hyp.profession_id, hyp.profession_title, hyp.industry_id, hyp.industry_name, hyp.match_score, hyp.explanation, hyp.status, hyp.created_at)
                )
                hypotheses.append(hyp)

            conn.commit()

        return hypotheses

    @staticmethod
    def get_hypotheses_for_student(student_id: str) -> List[CareerHypothesis]:
        """Получение ранее сохраненных гипотез школьника."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, student_id, profession_id, profession_title, industry_id, industry_name, match_score, explanation, status, created_at
                FROM hypotheses WHERE student_id = ?
                ORDER BY match_score DESC
                """,
                (student_id,)
            )
            rows = cursor.fetchall()
            return [
                CareerHypothesis(
                    id=r["id"],
                    student_id=r["student_id"],
                    profession_id=r["profession_id"],
                    profession_title=r["profession_title"],
                    industry_id=r["industry_id"],
                    industry_name=r["industry_name"],
                    match_score=r["match_score"],
                    explanation=r["explanation"],
                    status=r["status"],
                    created_at=r["created_at"]
                )
                for r in rows
            ]
