"""
Сервис кабинета индустриальных и образовательных партнёров (Критерий 6).
Позволяет предприятиям и колледжам/ВУЗам Свердловской области
актуализировать даты, слоты и квоты на профессиональные пробы.
"""
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.services.graph_service import graph_service
from app.database import get_connection

class PartnerService:
    @staticmethod
    def get_partner_trials(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Возвращает список профессиональных проб, сгруппированных по организации-партнеру,
        с учетом переопределений и подтверждений актуальности в БД.
        """
        all_trials = graph_service.get_trials_for_organization(org_id) if org_id else graph_service.get_all_trials()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM partner_trial_overrides")
            overrides = {row["trial_id"]: dict(row) for row in cursor.fetchall()}

        enriched_trials = []
        for t in all_trials:
            t_copy = dict(t)
            trial_id = t["id"]
            org = graph_service.get_organization(t["organization_id"])
            prof = graph_service.get_profession(t["profession_id"])

            t_copy["organization_name"] = org["name"] if org else "Организация СО"
            t_copy["organization_city"] = org["city"] if org else "Свердловская область"
            t_copy["profession_title"] = prof["title"] if prof else "Профессия"

            # Применяем переопределения из базы
            if trial_id in overrides:
                ov = overrides[trial_id]
                t_copy["partner_verified"] = True
                t_copy["verification_date"] = ov["verified_at"]
                t_copy["is_active"] = bool(ov["is_active"])
                if ov["custom_slots_json"]:
                    try:
                        t_copy["available_slots"] = json.loads(ov["custom_slots_json"])
                    except Exception:
                        pass

            enriched_trials.append(t_copy)

        return enriched_trials

    @staticmethod
    def verify_trial(trial_id: str, org_id: str) -> Dict[str, Any]:
        """
        Предприятие или учебное заведение подтверждает актуальность данных (Критерий 6).
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO partner_trial_overrides (trial_id, organization_id, verified_at, is_active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(trial_id) DO UPDATE SET
                    verified_at = excluded.verified_at,
                    is_active = 1
                """,
                (trial_id, org_id, now)
            )
            conn.commit()

        return {
            "trial_id": trial_id,
            "status": "verified",
            "verified_at": now,
            "message": "Данные о профессиональной пробе успешно актуализированы партнером."
        }

    @staticmethod
    def add_trial_slot(trial_id: str, new_slot_datetime: str) -> Dict[str, Any]:
        """
        Партнер открывает новый слот/дату для записи школьников.
        """
        # Сначала получаем текущие слоты
        trials = [t for t in graph_service.get_all_trials() if t["id"] == trial_id]
        if not trials:
            raise ValueError(f"Проба {trial_id} не найдена")

        base_slots = list(trials[0].get("available_slots", []))

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT custom_slots_json FROM partner_trial_overrides WHERE trial_id = ?", (trial_id,))
            row = cursor.fetchone()
            current_slots = base_slots
            if row and row["custom_slots_json"]:
                try:
                    current_slots = json.loads(row["custom_slots_json"])
                except Exception:
                    pass

            if new_slot_datetime not in current_slots:
                current_slots.append(new_slot_datetime)

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO partner_trial_overrides (trial_id, organization_id, verified_at, is_active, custom_slots_json)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(trial_id) DO UPDATE SET
                    verified_at = excluded.verified_at,
                    custom_slots_json = excluded.custom_slots_json
                """,
                (trial_id, trials[0]["organization_id"], now, json.dumps(current_slots, ensure_ascii=False))
            )
            conn.commit()

        return {
            "trial_id": trial_id,
            "slots": current_slots,
            "message": f"Новый слот '{new_slot_datetime}' успешно добавлен."
        }
