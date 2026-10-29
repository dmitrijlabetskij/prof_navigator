"""
Маршрутизация REST API сервиса «Профессиональный навигатор».
"""
import json
from dataclasses import asdict
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse
from app.config import BASE_DIR
from app.models import DiagnosticInput
from app.services.graph_service import graph_service
from app.services.diagnostic_service import DiagnosticService
from app.services.hypothesis_service import HypothesisService
from app.services.roadmap_service import RoadmapService
from app.services.feedback_service import FeedbackService
from app.services.counselor_service import CounselorService
from app.services.partner_service import PartnerService

def json_ok(data=None, status_code=200):
    return JSONResponse({"status": "success", "data": data}, status_code=status_code)

def json_err(message: str, status_code=400):
    return JSONResponse({"status": "error", "message": message}, status_code=status_code)

# --- Системные и диагностические эндпоинты ---

async def health_check(request: Request):
    return json_ok({"status": "healthy", "service": "prof_navigator", "region": "Свердловская область"})

async def graph_stats(request: Request):
    """Проверка согласованности графа возможностей (Критерий 5)."""
    consistency = graph_service.validate_graph_consistency()
    return json_ok(consistency)

async def get_diagnostic_schema(request: Request):
    schema = DiagnosticService.get_diagnostic_schema()
    return json_ok(schema)

async def submit_diagnostic(request: Request):
    """
    Прием результатов диагностики и формирование 3–5 гипотез (Критерий 1).
    """
    try:
        body = await request.json()
        student_name = body.get("student_name", "Школьник").strip()
        city = body.get("city", "Екатеринбург")
        grade = int(body.get("grade", 9))
        student_id = body.get("student_id")

        student = DiagnosticService.register_or_get_student(student_name, city, grade, student_id)
        
        diag_input = DiagnosticInput(
            student_name=student_name,
            city=city,
            grade=grade,
            selected_interests=body.get("selected_interests", []),
            klimov_preferences=body.get("klimov_preferences", []),
            holland_codes=body.get("holland_codes", []),
            notes=body.get("notes", "")
        )

        DiagnosticService.save_diagnostic(student.id, diag_input)
        hypotheses = HypothesisService.generate_hypotheses(student.id, diag_input)

        return json_ok({
            "student": asdict(student),
            "hypotheses_count": len(hypotheses),
            "hypotheses": [asdict(h) for h in hypotheses]
        })
    except Exception as e:
        return json_err(f"Ошибка при обработке диагностики: {str(e)}")

async def get_hypotheses(request: Request):
    student_id = request.query_params.get("student_id")
    if not student_id:
        return json_err("Параметр student_id обязателен")
    hypotheses = HypothesisService.get_hypotheses_for_student(student_id)
    return json_ok([asdict(h) for h in hypotheses])

# --- Маршруты и пробы (Критерий 2 и 3) ---

async def generate_or_get_roadmap(request: Request):
    """Построение персонального маршрута по гипотезе (Критерий 2)."""
    try:
        body = await request.json()
        student_id = body.get("student_id")
        hypothesis_id = body.get("hypothesis_id")
        if not student_id or not hypothesis_id:
            return json_err("Требуются student_id и hypothesis_id")

        roadmap = RoadmapService.generate_roadmap_for_hypothesis(student_id, hypothesis_id)
        return json_ok(asdict(roadmap))
    except Exception as e:
        return json_err(f"Ошибка при формировании маршрута: {str(e)}")

async def get_student_roadmaps(request: Request):
    student_id = request.query_params.get("student_id")
    if not student_id:
        return json_err("Параметр student_id обязателен")
    roadmaps = RoadmapService.get_roadmaps_for_student(student_id)
    return json_ok([asdict(r) for r in roadmaps])

async def complete_step(request: Request):
    step_id = request.path_params.get("step_id")
    step = RoadmapService.complete_step(step_id)
    if not step:
        return json_err("Шаг не найден", 404)
    return json_ok(asdict(step))

async def submit_feedback(request: Request):
    """Прием обратной связи после пробы (Критерий 3)."""
    try:
        body = await request.json()
        res = FeedbackService.submit_feedback(
            student_id=body["student_id"],
            step_id=body["step_id"],
            trial_id=body["trial_id"],
            rating_interest=int(body["rating_interest"]),
            difficulty_level=body.get("difficulty_level", "нормально"),
            key_takeaway=body.get("key_takeaway", ""),
            future_readiness=body.get("future_readiness", "yes")
        )
        return json_ok({
            "feedback": asdict(res["feedback"]),
            "hypothesis_id": res["hypothesis_id"],
            "new_hypothesis_status": res["new_hypothesis_status"],
            "message": res["message"]
        })
    except Exception as e:
        return json_err(f"Ошибка при сохранении обратной связи: {str(e)}")

# --- Кабинет профориентолога (Критерий 4) ---

async def get_counselor_students(request: Request):
    students = CounselorService.get_assigned_students()
    return json_ok(students)

async def get_counselor_student_roadmaps(request: Request):
    student_id = request.path_params.get("student_id")
    roadmaps = RoadmapService.get_roadmaps_for_student(student_id)
    feedbacks = FeedbackService.get_feedbacks_for_student(student_id)
    hypotheses = HypothesisService.get_hypotheses_for_student(student_id)
    return json_ok({
        "student_id": student_id,
        "roadmaps": [asdict(r) for r in roadmaps],
        "hypotheses": [asdict(h) for h in hypotheses],
        "feedbacks": feedbacks
    })

async def add_counselor_step(request: Request):
    try:
        body = await request.json()
        step = CounselorService.add_custom_step_by_counselor(
            roadmap_id=body["roadmap_id"],
            title=body["title"],
            description=body.get("description", ""),
            organization_name=body.get("organization_name", "Школа / ЦОПП"),
            organization_city=body.get("organization_city", "Екатеринбург"),
            format_type=body.get("format", "очно"),
            counselor_note=body.get("counselor_note", ""),
            due_date=body.get("due_date", "")
        )
        return json_ok(asdict(step))
    except Exception as e:
        return json_err(f"Ошибка при добавлении шага наставником: {str(e)}")

async def update_counselor_step(request: Request):
    step_id = request.path_params.get("step_id")
    body = await request.json()
    success = CounselorService.update_step_by_counselor(
        step_id=step_id,
        title=body.get("title"),
        description=body.get("description"),
        counselor_note=body.get("counselor_note"),
        due_date=body.get("due_date")
    )
    if not success:
        return json_err("Шаг не найден", 404)
    return json_ok({"updated": True, "step_id": step_id})

async def delete_counselor_step(request: Request):
    step_id = request.path_params.get("step_id")
    success = CounselorService.delete_step_by_counselor(step_id)
    if not success:
        return json_err("Шаг не найден", 404)
    return json_ok({"deleted": True, "step_id": step_id})

# --- Партнерский контур (Критерий 6) ---

async def get_partner_trials(request: Request):
    org_id = request.query_params.get("org_id")
    trials = PartnerService.get_partner_trials(org_id)
    return json_ok(trials)

async def verify_partner_trial(request: Request):
    trial_id = request.path_params.get("trial_id")
    body = await request.json()
    org_id = body.get("org_id", "org_default")
    result = PartnerService.verify_trial(trial_id, org_id)
    return json_ok(result)

async def add_partner_slot(request: Request):
    trial_id = request.path_params.get("trial_id")
    body = await request.json()
    slot = body.get("slot")
    if not slot:
        return json_err("Поле slot обязательно")
    result = PartnerService.add_trial_slot(trial_id, slot)
    return json_ok(result)

# --- Главная страница (Критерий 7: мобильный браузер) ---

async def serve_index(request: Request):
    index_file = BASE_DIR / "app" / "templates" / "index.html"
    with open(index_file, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(html)

