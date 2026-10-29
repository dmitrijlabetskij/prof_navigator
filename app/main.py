"""
Основной модуль приложения Starlette.
"""
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from app.config import BASE_DIR, DEBUG
from app.api.routes import (
    health_check,
    graph_stats,
    get_diagnostic_schema,
    submit_diagnostic,
    get_hypotheses,
    generate_or_get_roadmap,
    get_student_roadmaps,
    complete_step,
    submit_feedback,
    get_counselor_students,
    get_counselor_student_roadmaps,
    add_counselor_step,
    update_counselor_step,
    delete_counselor_step,
    get_partner_trials,
    verify_partner_trial,
    add_partner_slot,
    serve_index
)

routes = [
    # Главная страница (Mobile-first Web App)
    Route("/", endpoint=serve_index, methods=["GET"]),
    
    # API endpoints
    Route("/api/v1/health", endpoint=health_check, methods=["GET"]),
    Route("/api/v1/graph/stats", endpoint=graph_stats, methods=["GET"]),
    Route("/api/v1/diagnostic/schema", endpoint=get_diagnostic_schema, methods=["GET"]),
    Route("/api/v1/diagnostic/submit", endpoint=submit_diagnostic, methods=["POST"]),
    Route("/api/v1/hypotheses", endpoint=get_hypotheses, methods=["GET"]),
    Route("/api/v1/roadmaps/generate", endpoint=generate_or_get_roadmap, methods=["POST"]),
    Route("/api/v1/roadmaps", endpoint=get_student_roadmaps, methods=["GET"]),
    Route("/api/v1/roadmaps/steps/{step_id}/complete", endpoint=complete_step, methods=["POST"]),
    Route("/api/v1/feedback/submit", endpoint=submit_feedback, methods=["POST"]),
    
    # Кабинет профориентолога
    Route("/api/v1/counselor/students", endpoint=get_counselor_students, methods=["GET"]),
    Route("/api/v1/counselor/students/{student_id}/roadmaps", endpoint=get_counselor_student_roadmaps, methods=["GET"]),
    Route("/api/v1/counselor/roadmaps/steps", endpoint=add_counselor_step, methods=["POST"]),
    Route("/api/v1/counselor/roadmaps/steps/{step_id}", endpoint=update_counselor_step, methods=["PUT"]),
    Route("/api/v1/counselor/roadmaps/steps/{step_id}", endpoint=delete_counselor_step, methods=["DELETE"]),
    
    # Кабинет партнера
    Route("/api/v1/partner/trials", endpoint=get_partner_trials, methods=["GET"]),
    Route("/api/v1/partner/trials/{trial_id}/verify", endpoint=verify_partner_trial, methods=["POST"]),
    Route("/api/v1/partner/trials/{trial_id}/slots", endpoint=add_partner_slot, methods=["POST"]),
    
    # Статика
    Mount("/static", app=StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
]

app = Starlette(debug=DEBUG, routes=routes)

