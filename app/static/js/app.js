/**
 * Клиентское приложение «Профессиональный навигатор» (Свердловская область).
 * Реализует ролевые сценарии: Школьник, Профориентолог, Предприятие-партнер.
 */

// Глобальное состояние
const state = {
  currentRole: 'student',
  currentStudent: null,
  hypotheses: [],
  selectedHypothesis: null,
  activeRoadmap: null,
  schema: null,
  selectedInterests: new Set(),
  selectedKlimov: new Set(),
  feedbackSelectedRating: 5,
  counselorSelectedStudent: null
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', async () => {
  await loadDiagnosticSchema();
  initRatingStars();
  restoreSession();
});

// Переключение ролей (Школьник, Наставник, Партнёр)
function switchRole(role) {
  state.currentRole = role;
  document.querySelectorAll('.role-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.role-section').forEach(s => s.style.display = 'none');

  if (role === 'student') {
    document.querySelectorAll('.role-tab')[0].classList.add('active');
    document.getElementById('role-student').style.display = 'block';
  } else if (role === 'counselor') {
    document.querySelectorAll('.role-tab')[1].classList.add('active');
    document.getElementById('role-counselor').style.display = 'block';
    loadCounselorData();
  } else if (role === 'partner') {
    document.querySelectorAll('.role-tab')[2].classList.add('active');
    document.getElementById('role-partner').style.display = 'block';
    loadPartnerData();
  }
}

// Загрузка схемы опросника с бэкенда
async function loadDiagnosticSchema() {
  try {
    const res = await fetch('/api/v1/diagnostic/schema');
    const json = await res.json();
    state.schema = json.data;
    renderChips();
  } catch (err) {
    console.error('Ошибка загрузки схемы:', err);
  }
}

// Отрисовка интерактивных чипов интересов и типов Климова
function renderChips() {
  if (!state.schema) return;

  const intContainer = document.getElementById('interests-chips');
  intContainer.innerHTML = '';
  state.schema.interests.forEach(item => {
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.textContent = item.label;
    chip.onclick = () => toggleInterest(chip, item.id);
    intContainer.appendChild(chip);
  });

  const klimovContainer = document.getElementById('klimov-chips');
  klimovContainer.innerHTML = '';
  state.schema.klimov_types.forEach(item => {
    const chip = document.createElement('div');
    chip.className = 'chip';
    chip.textContent = item.label;
    chip.onclick = () => toggleKlimov(chip, item.id);
    klimovContainer.appendChild(chip);
  });
}

function toggleInterest(element, id) {
  if (state.selectedInterests.has(id)) {
    state.selectedInterests.delete(id);
    element.classList.remove('selected');
  } else {
    state.selectedInterests.add(id);
    element.classList.add('selected');
  }
}

function toggleKlimov(element, id) {
  if (state.selectedKlimov.has(id)) {
    state.selectedKlimov.delete(id);
    element.classList.remove('selected');
  } else {
    state.selectedKlimov.add(id);
    element.classList.add('selected');
  }
}

// Заполнение демо-данными в 1 клик
function fillDemoStudent() {
  document.getElementById('diag-name').value = 'Даниил Попов';
  document.getElementById('diag-city').value = 'Екатеринбург';
  document.getElementById('diag-grade').value = '9';

  state.selectedInterests.clear();
  state.selectedKlimov.clear();

  ['программирование', 'математика', 'робототехника'].forEach(id => state.selectedInterests.add(id));
  ['знаковая система', 'техника'].forEach(id => state.selectedKlimov.add(id));

  // Обновляем визуальные классы чипов
  document.querySelectorAll('#interests-chips .chip').forEach(c => {
    c.classList.toggle('selected', ['Программирование и ИТ', 'Математика и аналитика данных', 'Робототехника и мехатроника'].includes(c.textContent));
  });
  document.querySelectorAll('#klimov-chips .chip').forEach(c => {
    c.classList.toggle('selected', c.textContent.includes('Знаковая система') || c.textContent.includes('Техника'));
  });
}

// Отправка формы диагностики и генерация 3–5 гипотез (Критерий 1)
async function handleDiagnosticSubmit(event) {
  event.preventDefault();

  const name = document.getElementById('diag-name').value.trim();
  const city = document.getElementById('diag-city').value;
  const grade = parseInt(document.getElementById('diag-grade').value, 10);

  if (state.selectedInterests.size === 0) {
    alert('Пожалуйста, выбери хотя бы 1-2 сферы интересов!');
    return;
  }

  const payload = {
    student_name: name,
    city: city,
    grade: grade,
    selected_interests: Array.from(state.selectedInterests),
    klimov_preferences: Array.from(state.selectedKlimov),
    holland_codes: ['I', 'R', 'C']
  };

  try {
    const res = await fetch('/api/v1/diagnostic/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.status !== 'success') {
      alert('Ошибка: ' + json.message);
      return;
    }

    state.currentStudent = json.data.student;
    state.hypotheses = json.data.hypotheses;

    renderHypotheses();
  } catch (err) {
    alert('Сетевая ошибка при отправке: ' + err.message);
  }
}

// Сохранение сессии в localStorage
function saveSession() {
  if (state.currentStudent) {
    localStorage.setItem('prof_nav_student', JSON.stringify(state.currentStudent));
    localStorage.setItem('prof_nav_hypotheses', JSON.stringify(state.hypotheses));
    if (state.selectedHypothesis) {
      localStorage.setItem('prof_nav_selected_hyp', state.selectedHypothesis.id);
    }
  }
}

// Восстановление сессии при обновлении страницы
function restoreSession() {
  try {
    const savedStudent = localStorage.getItem('prof_nav_student');
    const savedHypotheses = localStorage.getItem('prof_nav_hypotheses');
    const savedSelectedHyp = localStorage.getItem('prof_nav_selected_hyp');

    if (savedStudent && savedHypotheses) {
      state.currentStudent = JSON.parse(savedStudent);
      state.hypotheses = JSON.parse(savedHypotheses);
      if (savedSelectedHyp) {
        state.selectedHypothesis = state.hypotheses.find(h => h.id === savedSelectedHyp) || state.hypotheses[0];
      } else if (state.hypotheses.length > 0) {
        state.selectedHypothesis = state.hypotheses[0];
      }
      renderHypotheses();
      if (state.selectedHypothesis) {
        loadRoadmap(state.selectedHypothesis.id, false);
      }
    }
  } catch (err) {
    console.error('Ошибка восстановления сессии:', err);
  }
}

function showToast(message) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 2600);
}

function scrollToRoadmap() {
  const rmCard = document.getElementById('student-roadmap-card');
  if (rmCard) {
    rmCard.style.display = 'block';
    rmCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function scrollToHypotheses() {
  const hypCard = document.getElementById('student-hypotheses-card');
  if (hypCard) {
    hypCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// Отрисовка карточек гипотез (Критерий 1)
function renderHypotheses() {
  document.getElementById('student-diagnostic-card').style.display = 'none';
  const hypCard = document.getElementById('student-hypotheses-card');
  hypCard.style.display = 'block';

  const list = document.getElementById('hypotheses-list');
  list.innerHTML = '';

  if (!state.selectedHypothesis && state.hypotheses.length > 0) {
    state.selectedHypothesis = state.hypotheses[0];
  }

  state.hypotheses.forEach((hyp, idx) => {
    const isSelected = state.selectedHypothesis && state.selectedHypothesis.id === hyp.id;
    const card = document.createElement('div');
    card.id = `hyp-card-${hyp.id}`;
    card.className = `hypothesis-card ${isSelected ? 'active-selected' : ''}`;
    
    // Метка статуса
    let statusLabel = 'Новая гипотеза';
    let statusColor = '#3b82f6';
    if (hyp.status === 'confirmed') {
      statusLabel = '✅ Подтверждена практикой';
      statusColor = '#10b981';
    } else if (hyp.status === 'rejected') {
      statusLabel = '❌ Опровергнута';
      statusColor = '#ef4444';
    } else if (hyp.status === 'doubted') {
      statusLabel = '❓ Требует доп. проб';
      statusColor = '#f59e0b';
    }

    card.innerHTML = `
      <div class="hyp-header">
        <div class="hyp-title">Гипотеза №${idx + 1}: ${hyp.profession_title}</div>
        <div class="match-badge">${hyp.match_score}% совпадение</div>
      </div>
      <div class="hyp-industry">Кластер: ${hyp.industry_name} • <span style="color: ${statusColor}; font-weight: 700;">${statusLabel}</span></div>
      <div class="hyp-explanation">${hyp.explanation}</div>
      <div style="margin-top: 10px;">
        <button class="btn ${isSelected ? 'btn-success' : 'btn-primary'} btn-sm" id="btn-hyp-${hyp.id}">
          ${isSelected ? '✓ Маршрут открыт (перейти ↓)' : '🚀 Открыть персональный маршрут'}
        </button>
      </div>
    `;

    const btn = card.querySelector(`#btn-hyp-${hyp.id}`);
    btn.onclick = (e) => {
      e.stopPropagation();
      if (state.selectedHypothesis && state.selectedHypothesis.id === hyp.id && state.activeRoadmap) {
        scrollToRoadmap();
      } else {
        handleOpenRoadmap(hyp.id, btn);
      }
    };

    card.onclick = () => {
      if (state.selectedHypothesis && state.selectedHypothesis.id === hyp.id && state.activeRoadmap) {
        scrollToRoadmap();
      } else {
        handleOpenRoadmap(hyp.id, btn);
      }
    };

    list.appendChild(card);
  });

  // Автоматически подготавливаем маршрут для первой гипотезы при первичном входе (без скролла)
  if (state.hypotheses.length > 0 && !state.activeRoadmap) {
    loadRoadmap(state.hypotheses[0].id, false);
  }
}

async function handleOpenRoadmap(hypId, btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '⏳ Формируем маршрут...';
  }
  await loadRoadmap(hypId, true);
}

function updateHypothesesSelection(selectedHypId) {
  state.hypotheses.forEach(hyp => {
    const card = document.getElementById(`hyp-card-${hyp.id}`);
    const btn = document.getElementById(`btn-hyp-${hyp.id}`);
    const isSelected = (hyp.id === selectedHypId);

    if (card) {
      card.classList.toggle('active-selected', isSelected);
    }
    if (btn) {
      btn.disabled = false;
      if (isSelected) {
        btn.className = 'btn btn-success btn-sm';
        btn.innerHTML = '✓ Маршрут открыт (перейти ↓)';
        btn.onclick = (e) => {
          e.stopPropagation();
          scrollToRoadmap();
        };
      } else {
        btn.className = 'btn btn-primary btn-sm';
        btn.innerHTML = '🚀 Открыть персональный маршрут';
        btn.onclick = (e) => {
          e.stopPropagation();
          handleOpenRoadmap(hyp.id, btn);
        };
      }
    }
  });
}

function resetDiagnostic() {
  localStorage.removeItem('prof_nav_student');
  localStorage.removeItem('prof_nav_hypotheses');
  localStorage.removeItem('prof_nav_selected_hyp');
  state.currentStudent = null;
  state.hypotheses = [];
  state.selectedHypothesis = null;
  state.activeRoadmap = null;
  document.getElementById('student-diagnostic-card').style.display = 'block';
  document.getElementById('student-hypotheses-card').style.display = 'none';
  document.getElementById('student-roadmap-card').style.display = 'none';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Загрузка или генерация персонального маршрута (Критерий 2)
async function loadRoadmap(hypothesisId, shouldScroll = true) {
  if (!state.currentStudent) {
    const saved = localStorage.getItem('prof_nav_student');
    if (saved) {
      state.currentStudent = JSON.parse(saved);
    } else {
      alert('Данные школьника не найдены. Пожалуйста, пройдите экспресс-диагностику.');
      return;
    }
  }

  state.selectedHypothesis = state.hypotheses.find(h => h.id === hypothesisId);

  try {
    const res = await fetch('/api/v1/roadmaps/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: state.currentStudent.id,
        hypothesis_id: hypothesisId
      })
    });
    const json = await res.json();
    if (json.status !== 'success') {
      alert('Ошибка формирования маршрута: ' + json.message);
      return;
    }
    state.activeRoadmap = json.data;
    saveSession();
    renderRoadmap();
    updateHypothesesSelection(hypothesisId);

    if (shouldScroll) {
      setTimeout(() => {
        scrollToRoadmap();
      }, 60);
      showToast(`📍 Маршрут открыт: ${state.selectedHypothesis ? state.selectedHypothesis.profession_title : ''}`);
    }
  } catch (err) {
    console.error('Ошибка маршрута:', err);
    alert('Не удалось загрузить маршрут: ' + err.message);
  }
}

// Отрисовка таймлайна персонального маршрута (Критерий 2)
function renderRoadmap() {
  const rm = state.activeRoadmap;
  if (!rm) return;

  const rmCard = document.getElementById('student-roadmap-card');
  rmCard.style.display = 'block';

  document.getElementById('roadmap-card-title').textContent = `📍 Маршрут: ${rm.profession_title}`;
  document.getElementById('roadmap-progress-badge').textContent = `Прогресс: ${rm.progress_percentage}%`;

  const timeline = document.getElementById('roadmap-timeline');
  timeline.innerHTML = '';

  rm.steps.forEach(step => {
    const isCompleted = step.status === 'completed';
    const isTrialStep = Boolean(step.trial_id);

    const stepEl = document.createElement('div');
    stepEl.className = `timeline-step ${isCompleted ? 'completed' : 'in-progress'}`;

    stepEl.innerHTML = `
      <div class="step-marker">
        <div class="step-circle">${isCompleted ? '✓' : step.stage_number}</div>
        <div class="step-line"></div>
      </div>
      <div class="step-content">
        <div class="step-title">${step.title}</div>
        <div class="step-desc">${step.description}</div>
        <div class="step-meta">
          <span class="badge badge-org">🏢 ${step.organization_name || 'Свердловская область'}</span>
          <span class="badge">📍 ${step.organization_city || 'Екатеринбург'}</span>
          <span class="badge">Формат: ${step.format}</span>
          ${step.is_custom_by_counselor ? '<span class="badge badge-custom">🧑‍🏫 Добавлено наставником</span>' : ''}
        </div>
        ${step.counselor_note ? `<div style="font-size: 0.8rem; background: #fef9c3; padding: 6px 10px; border-radius: 6px; margin-bottom: 8px;"><strong>Заметка наставника:</strong> ${step.counselor_note}</div>` : ''}
        <div class="step-action-box"></div>
      </div>
    `;

    const actionBox = stepEl.querySelector('.step-action-box');
    if (!isCompleted) {
      if (isTrialStep) {
        const btn = document.createElement('button');
        btn.className = 'btn btn-success btn-sm';
        btn.innerHTML = '🎯 Пройти пробу и оставить отзыв';
        btn.onclick = () => openFeedbackModal(step.id, step.trial_id, step.title);
        actionBox.appendChild(btn);
      } else {
        const btn = document.createElement('button');
        btn.className = 'btn btn-outline btn-sm';
        btn.innerHTML = '✓ Отметить выполнение';
        btn.onclick = () => completeGenericStep(step.id);
        actionBox.appendChild(btn);
      }
    } else {
      actionBox.innerHTML = `<span style="color: var(--success); font-weight: 700; font-size: 0.85rem;">✓ Выполнено</span>`;
    }

    timeline.appendChild(stepEl);
  });
}

// Завершение обычного шага маршрута
async function completeGenericStep(stepId) {
  try {
    const res = await fetch(`/api/v1/roadmaps/steps/${stepId}/complete`, { method: 'POST' });
    const json = await res.json();
    if (json.status === 'success') {
      await loadRoadmap(state.selectedHypothesis.id, false);
      showToast('✓ Шаг маршрута отмечен выполненным');
    }
  } catch (err) {
    alert('Ошибка завершения шага: ' + err.message);
  }
}

// Модальное окно обратной связи (Критерий 3)
function openFeedbackModal(stepId, trialId, title) {
  document.getElementById('fb-step-id').value = stepId;
  document.getElementById('fb-trial-id').value = trialId;
  document.getElementById('feedback-trial-title').textContent = title;
  document.getElementById('feedback-modal').style.display = 'flex';
}

function closeFeedbackModal() {
  document.getElementById('feedback-modal').style.display = 'none';
}

function initRatingStars() {
  document.querySelectorAll('#rating-stars .star-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('#rating-stars .star-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      state.feedbackSelectedRating = parseInt(btn.getAttribute('data-val'), 10);
    };
  });
}

async function handleFeedbackSubmit(event) {
  event.preventDefault();
  const stepId = document.getElementById('fb-step-id').value;
  const trialId = document.getElementById('fb-trial-id').value;
  const difficulty = document.getElementById('fb-difficulty').value;
  const takeaway = document.getElementById('fb-key-takeaway').value.trim();
  const readiness = document.getElementById('fb-readiness').value;

  const payload = {
    student_id: state.currentStudent.id,
    step_id: stepId,
    trial_id: trialId,
    rating_interest: state.feedbackSelectedRating,
    difficulty_level: difficulty,
    key_takeaway: takeaway,
    future_readiness: readiness
  };

  try {
    const res = await fetch('/api/v1/feedback/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.status === 'success') {
      closeFeedbackModal();
      showToast('✓ ' + json.data.message);

      // Обновляем список гипотез и маршрут
      const hypRes = await fetch(`/api/v1/hypotheses?student_id=${state.currentStudent.id}`);
      const hypJson = await hypRes.json();
      state.hypotheses = hypJson.data;
      saveSession();
      renderHypotheses();
      await loadRoadmap(state.selectedHypothesis.id, false);
    }
  } catch (err) {
    alert('Ошибка отправки рефлексии: ' + err.message);
  }
}

// ================= КАБИНЕТ ПРОФОРИЕНТОЛОГА (Критерий 4) =================
async function loadCounselorData() {
  try {
    const res = await fetch('/api/v1/counselor/students');
    const json = await res.json();
    const students = json.data || [];
    const tbody = document.getElementById('counselor-students-table');
    tbody.innerHTML = '';

    if (students.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Пока нет зарегистрированных школьников. Пройдите диагностику в роли Школьника.</td></tr>`;
      return;
    }

    students.forEach(st => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${st.name}</strong></td>
        <td>${st.city}, ${st.grade} класс</td>
        <td>${st.hypotheses_count} гипотез</td>
        <td>${st.roadmaps_count} активных</td>
        <td>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="flex-grow: 1; height: 6px; background: #e2e8f0; border-radius: 3px;">
              <div style="width: ${st.avg_progress}%; height: 100%; background: var(--success); border-radius: 3px;"></div>
            </div>
            <span>${st.avg_progress}%</span>
          </div>
        </td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="openCounselorStudentDetails('${st.id}', '${escapeHtml(st.name)}')">
            👁 Маршруты
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Ошибка загрузки данных профориентолога:', err);
  }
}

async function openCounselorStudentDetails(studentId, name) {
  state.counselorSelectedStudent = studentId;
  const container = document.getElementById('counselor-student-details');
  container.style.display = 'block';
  document.getElementById('counselor-student-heading').textContent = `Маршруты и гипотезы: ${name}`;

  try {
    const res = await fetch(`/api/v1/counselor/students/${studentId}/roadmaps`);
    const json = await res.json();
    const content = document.getElementById('counselor-student-content');
    content.innerHTML = '';

    const roadmaps = json.data.roadmaps || [];
    if (roadmaps.length === 0) {
      content.innerHTML = `<div style="color: var(--text-muted); padding: 10px;">У школьника пока нет открытых маршрутов.</div>`;
      return;
    }

    // Сохраняем первый roadmap_id для модалки добавления шага
    document.getElementById('counselor-modal-roadmap-id').value = roadmaps[0].id;

    roadmaps.forEach(rm => {
      const rmDiv = document.createElement('div');
      rmDiv.style.marginBottom = '20px';
      rmDiv.innerHTML = `
        <h4 style="margin-bottom: 8px; color: var(--primary);">Профессия: ${rm.profession_title} (Прогресс: ${rm.progress_percentage}%)</h4>
        <div class="timeline">
          ${rm.steps.map(s => `
            <div class="timeline-step ${s.status === 'completed' ? 'completed' : 'in-progress'}">
              <div class="step-marker">
                <div class="step-circle">${s.status === 'completed' ? '✓' : s.stage_number}</div>
                <div class="step-line"></div>
              </div>
              <div class="step-content">
                <div style="display: flex; justify-content: space-between;">
                  <span class="step-title">${s.title}</span>
                  <button class="btn btn-outline btn-sm" style="color: var(--danger); border-color: #fca5a5;" onclick="deleteCounselorStep('${s.id}')">Удалить</button>
                </div>
                <div class="step-desc">${s.description}</div>
                <div class="step-meta">
                  <span class="badge badge-org">🏢 ${s.organization_name || 'СО'}</span>
                  ${s.is_custom_by_counselor ? '<span class="badge badge-custom">✏️ Задано профориентологом</span>' : ''}
                </div>
                ${s.counselor_note ? `<div style="font-size: 0.8rem; background: #fef9c3; padding: 4px 8px; border-radius: 6px;">Рекомендация: ${s.counselor_note}</div>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      `;
      content.appendChild(rmDiv);
    });
  } catch (err) {
    console.error('Ошибка деталей школьника:', err);
  }
}

function openAddStepModal() {
  document.getElementById('add-step-modal').style.display = 'flex';
}

function closeAddStepModal() {
  document.getElementById('add-step-modal').style.display = 'none';
}

async function handleAddStepSubmit(event) {
  event.preventDefault();
  const roadmapId = document.getElementById('counselor-modal-roadmap-id').value;
  const title = document.getElementById('cs-step-title').value.trim();
  const desc = document.getElementById('cs-step-desc').value.trim();
  const org = document.getElementById('cs-step-org').value.trim();
  const city = document.getElementById('cs-step-city').value.trim();
  const note = document.getElementById('cs-step-note').value.trim();

  const payload = {
    roadmap_id: roadmapId,
    title: title,
    description: desc,
    organization_name: org,
    organization_city: city,
    counselor_note: note,
    format: 'очно'
  };

  try {
    const res = await fetch('/api/v1/counselor/roadmaps/steps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.status === 'success') {
      closeAddStepModal();
      alert('Персональный шаг успешно добавлен в маршрут школьника!');
      openCounselorStudentDetails(state.counselorSelectedStudent, 'Школьник');
    }
  } catch (err) {
    alert('Ошибка добавления шага: ' + err.message);
  }
}

async function deleteCounselorStep(stepId) {
  if (!confirm('Удалить данный шаг из маршрута?')) return;
  try {
    const res = await fetch(`/api/v1/counselor/roadmaps/steps/${stepId}`, { method: 'DELETE' });
    const json = await res.json();
    if (json.status === 'success') {
      openCounselorStudentDetails(state.counselorSelectedStudent, 'Школьник');
    }
  } catch (err) {
    alert('Ошибка удаления: ' + err.message);
  }
}

// ================= КАБИНЕТ ПАРТНЕРА (Критерий 6) =================
async function loadPartnerData() {
  try {
    const res = await fetch('/api/v1/partner/trials');
    const json = await res.json();
    const trials = json.data || [];
    const tbody = document.getElementById('partner-trials-table');
    tbody.innerHTML = '';

    trials.forEach(t => {
      const tr = document.createElement('tr');
      const slotsList = (t.available_slots || []).map(s => `• ${s.replace('T', ' ')}`).join('<br>');
      const isVerified = t.partner_verified;

      tr.innerHTML = `
        <td><strong>${t.title}</strong><br><small style="color: var(--text-muted);">${t.profession_title}</small></td>
        <td>${t.organization_name}<br><small style="color: var(--text-muted);">${t.organization_city}</small></td>
        <td><span class="badge">${t.format}</span></td>
        <td style="font-size: 0.8rem;">${slotsList || 'По запросу'}</td>
        <td>
          <span class="status-dot ${isVerified ? 'dot-green' : 'dot-orange'}"></span>
          ${isVerified ? `Актуально (проверено ${t.verification_date || 'недавно'})` : 'Требует подтверждения'}
        </td>
        <td>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <button class="btn btn-outline btn-sm" onclick="verifyPartnerTrial('${t.id}')">
              ✓ Подтвердить
            </button>
            <button class="btn btn-outline btn-sm" onclick="addSlotPrompt('${t.id}')">
              ➕ Добавить слот
            </button>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Ошибка загрузки программ партнера:', err);
  }
}

async function verifyPartnerTrial(trialId) {
  try {
    const res = await fetch(`/api/v1/partner/trials/${trialId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ org_id: 'org_partner' })
    });
    const json = await res.json();
    if (json.status === 'success') {
      alert('Данные актуализированы и подтверждены!');
      loadPartnerData();
    }
  } catch (err) {
    alert('Ошибка подтверждения: ' + err.message);
  }
}

async function addSlotPrompt(trialId) {
  const slot = prompt('Введите дату и время нового слота (например: 2026-12-10 15:00):', '2026-12-10 15:00');
  if (!slot) return;

  try {
    const res = await fetch(`/api/v1/partner/trials/${trialId}/slots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot: slot.trim() })
    });
    const json = await res.json();
    if (json.status === 'success') {
      alert(json.data.message);
      loadPartnerData();
    }
  } catch (err) {
    alert('Ошибка добавления слота: ' + err.message);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

