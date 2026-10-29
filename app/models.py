"""
Доменные модели данных сервиса «Профессиональный навигатор».
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

def current_utc_iso():
    return datetime.now(timezone.utc).isoformat()

@dataclass
class DiagnosticInput:
    """Входные данные профориентационной диагностики школьника."""
    student_name: str
    city: str
    grade: int  # 8, 9, 10, 11
    selected_interests: List[str]  # ['математика', 'программирование', 'робототехника', ...]
    klimov_preferences: List[str]  # ['знаковая система', 'техника', 'природа', ...]
    holland_codes: List[str]  # ['I', 'R', 'C', ...]
    notes: Optional[str] = ""

@dataclass
class CareerHypothesis:
    """Профессиональная гипотеза для школьника."""
    id: str
    student_id: str
    profession_id: str
    profession_title: str
    industry_id: str
    industry_name: str
    match_score: int  # 0 - 100%
    explanation: str  # Обоснование ИИ-сервиса
    status: str = "active"  # 'active', 'confirmed', 'doubted', 'rejected'
    created_at: str = field(default_factory=current_utc_iso)

@dataclass
class RoadmapStep:
    """Шаг персонального маршрута школьника."""
    id: str
    roadmap_id: str
    stage_number: int  # 1: Знакомство, 2: Профпроба, 3: Допобразование, 4: СПО/ВУЗ + Партнер
    title: str
    description: str
    organization_id: Optional[str]
    organization_name: Optional[str]
    organization_city: Optional[str]
    organization_address: Optional[str]
    format: str  # 'онлайн', 'очно', 'лаборатория', 'экскурсия'
    trial_id: Optional[str] = None
    status: str = "pending"  # 'pending', 'in_progress', 'completed'
    due_date: Optional[str] = None
    is_custom_by_counselor: bool = False
    counselor_note: Optional[str] = None

@dataclass
class Roadmap:
    """Персональный маршрут школьника по конкретной гипотезе."""
    id: str
    student_id: str
    hypothesis_id: str
    profession_id: str
    profession_title: str
    steps: List[RoadmapStep] = field(default_factory=list)
    progress_percentage: int = 0
    created_at: str = field(default_factory=current_utc_iso)

@dataclass
class TrialFeedback:
    """Обратная связь (рефлексия) школьника после профессиональной пробы."""
    id: str
    student_id: str
    step_id: str
    trial_id: str
    rating_interest: int  # 1-5
    difficulty_level: str  # 'легко', 'нормально', 'сложно'
    key_takeaway: str  # Что больше всего запомнилось / понравилось
    future_readiness: str  # 'yes', 'doubt', 'no' (Готов ли продолжать развитие)
    submitted_at: str = field(default_factory=current_utc_iso)

@dataclass
class StudentProfile:
    """Профиль школьника в системе."""
    id: str
    name: str
    city: str
    grade: int
    counselor_id: Optional[str] = "counselor_default"
    hypotheses: List[CareerHypothesis] = field(default_factory=list)
    created_at: str = field(default_factory=current_utc_iso)
