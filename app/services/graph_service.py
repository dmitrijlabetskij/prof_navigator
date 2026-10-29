"""
Сервис работы с Графом возможностей Свердловской области.
Обеспечивает индексацию, проверку согласованности данных (Критерий 5)
и предоставление сущностей для алгоритмов маршрутизации.
"""
import json
from typing import Dict, List, Optional, Any
from app.config import GRAPH_DATA_PATH

class OpportunityGraphService:
    def __init__(self, data_path=GRAPH_DATA_PATH):
        self.data_path = data_path
        self._raw_data: Dict[str, Any] = {}
        self.industries: Dict[str, Dict] = {}
        self.professions: Dict[str, Dict] = {}
        self.organizations: Dict[str, Dict] = {}
        self.vocational_trials: Dict[str, Dict] = {}
        self.educational_programs: Dict[str, Dict] = {}
        self.load_graph()

    def load_graph(self):
        """Загрузка и индексация графа из JSON-файла."""
        with open(self.data_path, "r", encoding="utf-8") as f:
            self._raw_data = json.load(f)

        self.industries = {item["id"]: item for item in self._raw_data.get("industries", [])}
        self.professions = {item["id"]: item for item in self._raw_data.get("professions", [])}
        self.organizations = {item["id"]: item for item in self._raw_data.get("organizations", [])}
        self.vocational_trials = {item["id"]: item for item in self._raw_data.get("vocational_trials", [])}
        self.educational_programs = {item["id"]: item for item in self._raw_data.get("educational_programs", [])}

    def validate_graph_consistency(self) -> Dict[str, Any]:
        """
        Проверка согласованности графа возможностей (Критерий 5):
        - Все профессии принадлежат существующим отраслям;
        - Все профпробы привязаны к существующим профессиям и организациям;
        - Все образовательные программы привязаны к существующим ВУЗам/колледжам, профессиям и предприятиям-партнерам.
        """
        errors = []
        
        # 1. Профессии -> Отрасли
        for p_id, p in self.professions.items():
            if p["industry_id"] not in self.industries:
                errors.append(f"Профессия {p_id} ссылается на неизвестную отрасль {p['industry_id']}")

        # 2. Профпробы -> Профессии и Организации
        for t_id, t in self.vocational_trials.items():
            if t["profession_id"] not in self.professions:
                errors.append(f"Профпроба {t_id} ссылается на неизвестную профессию {t['profession_id']}")
            if t["organization_id"] not in self.organizations:
                errors.append(f"Профпроба {t_id} ссылается на неизвестную организацию {t['organization_id']}")

        # 3. Образовательные программы -> Организации, Профессии, Предприятия
        for edu_id, edu in self.educational_programs.items():
            if edu["profession_id"] not in self.professions:
                errors.append(f"Программа {edu_id} ссылается на неизвестную профессию {edu['profession_id']}")
            if edu["organization_id"] not in self.organizations:
                errors.append(f"Программа {edu_id} ссылается на неизвестную организацию {edu['organization_id']}")
            for partner_org_id in edu.get("partner_companies", []):
                if partner_org_id not in self.organizations:
                    errors.append(f"Программа {edu_id} ссылается на неизвестного индустриального партнера {partner_org_id}")

        is_consistent = len(errors) == 0
        return {
            "is_consistent": is_consistent,
            "errors": errors,
            "counts": {
                "industries": len(self.industries),
                "professions": len(self.professions),
                "organizations": len(self.organizations),
                "vocational_trials": len(self.vocational_trials),
                "educational_programs": len(self.educational_programs)
            }
        }

    def get_profession(self, profession_id: str) -> Optional[Dict]:
        return self.professions.get(profession_id)

    def get_organization(self, organization_id: str) -> Optional[Dict]:
        return self.organizations.get(organization_id)

    def get_trials_for_profession(self, profession_id: str) -> List[Dict]:
        return [t for t in self.vocational_trials.values() if t["profession_id"] == profession_id]

    def get_trials_for_organization(self, organization_id: str) -> List[Dict]:
        return [t for t in self.vocational_trials.values() if t["organization_id"] == organization_id]

    def get_edu_programs_for_profession(self, profession_id: str) -> List[Dict]:
        return [e for e in self.educational_programs.values() if e["profession_id"] == profession_id]

    def get_all_trials(self) -> List[Dict]:
        return list(self.vocational_trials.values())

# Глобальный синглтон сервиса графа
graph_service = OpportunityGraphService()

