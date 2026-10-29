"""
Комплексный автоматический тест соответствия 7 критериям диплома
«Профессиональный навигатор» (Свердловская область).
"""
import unittest
import os
import json
from app.config import DATABASE_PATH
from app.database import init_db, get_connection
from app.models import DiagnosticInput
from app.services.graph_service import graph_service
from app.services.diagnostic_service import DiagnosticService
from app.services.hypothesis_service import HypothesisService
from app.services.roadmap_service import RoadmapService
from app.services.feedback_service import FeedbackService
from app.services.counselor_service import CounselorService
from app.services.partner_service import PartnerService

class TestProfNavigatorCriteria(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Инициализируем чистую БД
        init_db()

    def test_criterion_5_opportunity_graph_consistency(self):
        """Критерий 5: Граф возможностей содержит согласованный набор данных."""
        validation = graph_service.validate_graph_consistency()
        self.assertTrue(validation["is_consistent"], f"Ошибки связности графа: {validation['errors']}")
        counts = validation["counts"]
        self.assertGreaterEqual(counts["industries"], 3, "Должно быть не менее 3 отраслей")
        self.assertGreaterEqual(counts["professions"], 5, "Должно быть не менее 5 профессий")
        self.assertGreaterEqual(counts["organizations"], 8, "Должно быть не менее 8 ключевых организаций СО")
        self.assertGreaterEqual(counts["vocational_trials"], 5, "Должно быть не менее 5 профпроб")
        self.assertGreaterEqual(counts["educational_programs"], 5, "Должно быть не менее 5 программ")

    def test_criterion_1_hypotheses_generation(self):
        """Критерий 1: Сервис принимает результаты диагностики и формирует 3–5 профессиональных гипотез."""
        student = DiagnosticService.register_or_get_student(
            name="Иван Уральский",
            city="Екатеринбург",
            grade=9
        )
        diag_input = DiagnosticInput(
            student_name=student.name,
            city=student.city,
            grade=student.grade,
            selected_interests=["программирование", "математика", "робототехника"],
            klimov_preferences=["знаковая система", "техника"],
            holland_codes=["I", "R", "C"]
        )
        DiagnosticService.save_diagnostic(student.id, diag_input)
        hypotheses = HypothesisService.generate_hypotheses(student.id, diag_input)

        # Проверка критерия 1: ровно от 3 до 5 гипотез
        self.assertGreaterEqual(len(hypotheses), 3, "Должно быть сформировано как минимум 3 гипотезы")
        self.assertLessEqual(len(hypotheses), 5, "Должно быть сформировано не более 5 гипотез")

        # Проверка свойств гипотез
        for hyp in hypotheses:
            self.assertEqual(hyp.student_id, student.id)
            self.assertGreater(hyp.match_score, 0)
            self.assertTrue(len(hyp.explanation) > 10, "Должно присутствовать содержательное объяснение")
            self.assertEqual(hyp.status, "active")

        # Сохраняем для последующих тестов
        self.__class__.test_student = student
        self.__class__.test_hypotheses = hypotheses

    def test_criterion_2_roadmap_generation(self):
        """Критерий 2: Для каждой гипотезы строится персональный маршрут."""
        student = self.__class__.test_student
        hypotheses = self.__class__.test_hypotheses

        roadmaps = []
        for hyp in hypotheses:
            rm = RoadmapService.generate_roadmap_for_hypothesis(student.id, hyp.id)
            self.assertIsNotNone(rm)
            self.assertEqual(rm.hypothesis_id, hyp.id)
            self.assertGreaterEqual(len(rm.steps), 4, "Маршрут должен содержать не менее 4 шагов")
            
            # Проверяем последовательность этапов
            stages = [s.stage_number for s in rm.steps]
            self.assertIn(1, stages, "Должен быть этап 1 (Знакомство)")
            self.assertIn(2, stages, "Должен быть этап 2 (Профпроба)")
            self.assertIn(3, stages, "Должен быть этап 3 (Допобразование/проект)")
            self.assertIn(4, stages, "Должен быть этап 4 (ВУЗ/СПО + предприятие)")

            # Проверяем наличие площадки Свердловской области
            trial_step = next((s for s in rm.steps if s.stage_number == 2), None)
            self.assertIsNotNone(trial_step)
            self.assertIsNotNone(trial_step.organization_name)
            roadmaps.append(rm)

        self.__class__.test_roadmaps = roadmaps

    def test_criterion_3_trial_feedback_and_hypothesis_update(self):
        """Критерий 3: После профессиональной пробы школьник может дать обратную связь."""
        student = self.__class__.test_student
        roadmap = self.__class__.test_roadmaps[0]

        # Находим шаг пробы
        trial_step = next(s for s in roadmap.steps if s.trial_id is not None)
        
        # Отправляем положительную рефлексию
        result = FeedbackService.submit_feedback(
            student_id=student.id,
            step_id=trial_step.id,
            trial_id=trial_step.trial_id,
            rating_interest=5,
            difficulty_level="нормально",
            key_takeaway="Очень понравилось программировать контроллер на стенде!",
            future_readiness="yes"
        )

        self.assertIsNotNone(result["feedback"])
        self.assertEqual(result["new_hypothesis_status"], "confirmed", "При высокой оценке гипотеза должна подтвердиться")

        # Проверяем отметку о выполнении шага
        updated_rm = RoadmapService.get_roadmap_by_id(roadmap.id)
        updated_step = next(s for s in updated_rm.steps if s.id == trial_step.id)
        self.assertEqual(updated_step.status, "completed")
        self.assertGreater(updated_rm.progress_percentage, 0)

    def test_criterion_4_counselor_management(self):
        """Критерий 4: Профориентолог видит маршруты подопечных и может корректировать их."""
        student = self.__class__.test_student
        roadmap = self.__class__.test_roadmaps[0]

        # 1. Профориентолог видит список подопечных
        counselor_students = CounselorService.get_assigned_students("counselor_default")
        student_ids = [s["id"] for s in counselor_students]
        self.assertIn(student.id, student_ids, "Школьник должен быть виден в кабинете профориентолога")

        # 2. Профориентолог добавляет персональный шаг
        custom_step = CounselorService.add_custom_step_by_counselor(
            roadmap_id=roadmap.id,
            title="Индивидуальная консультация по целевому договору с СКБ Контур",
            description="Обсудить условия целевого набора в ИРИТ-РТФ УрФУ",
            organization_name="СКБ Контур / УрФУ",
            organization_city="Екатеринбург",
            counselor_note="Подготовить портфолио грамот олимпиад"
        )
        self.assertIsNotNone(custom_step)
        self.assertTrue(custom_step.is_custom_by_counselor)

        # 3. Проверяем, что шаг появился в маршруте школьника
        updated_rm = RoadmapService.get_roadmap_by_id(roadmap.id)
        step_ids = [s.id for s in updated_rm.steps]
        self.assertIn(custom_step.id, step_ids)

        # 4. Профориентолог может скорректировать шаг
        update_ok = CounselorService.update_step_by_counselor(
            step_id=custom_step.id,
            counselor_note="Срок подачи заявления: до 15 мая"
        )
        self.assertTrue(update_ok)

    def test_criterion_6_partner_freshness(self):
        """Критерий 6: Партнёры предоставляют актуальные данные."""
        # Получаем пробы
        trials = PartnerService.get_partner_trials()
        self.assertGreater(len(trials), 0)
        target_trial = trials[0]
        trial_id = target_trial["id"]

        # 1. Подтверждение актуальности данных
        verify_res = PartnerService.verify_trial(trial_id, "org_kontur")
        self.assertEqual(verify_res["status"], "verified")
        self.assertIsNotNone(verify_res["verified_at"])

        # 2. Добавление нового слота даты
        new_slot = "2026-12-25 15:00"
        slot_res = PartnerService.add_trial_slot(trial_id, new_slot)
        self.assertIn(new_slot, slot_res["slots"])

        # Проверяем, что обновленный слот возвращается в общем каталоге
        updated_trials = PartnerService.get_partner_trials()
        matching = next(t for t in updated_trials if t["id"] == trial_id)
        self.assertTrue(matching["partner_verified"])
        self.assertIn(new_slot, matching["available_slots"])

    def test_criterion_7_mobile_web_interface(self):
        """Критерий 7: Сервис работает в браузере на мобильных устройствах."""
        index_path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "index.html")
        self.assertTrue(os.path.exists(index_path), "Файл шаблона index.html должен существовать")

        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Проверка обязательных мобильных метатегов
        self.assertIn('name="viewport"', html)
        self.assertIn('width=device-width', html)
        self.assertIn('role-tabs', html)
        self.assertIn('styles.css', html)
        self.assertIn('app.js', html)

if __name__ == "__main__":
    unittest.main()

