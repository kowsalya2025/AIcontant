/* EduAI — Dashboard JavaScript v2 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  await Promise.all([loadDashboardStats(), loadRecommendations(), loadRecentContent()]);
});

async function loadDashboardStats() {
  const res = await API.get('/auth/dashboard-stats/');
  if (!res.ok) return;

  const s = res.data;
  const user = Storage.get('user') || {};
  const name = s.display_name || user.full_name || user.email?.split('@')[0] || 'Student';

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const el = document.getElementById('greetingText');
  if (el) el.textContent = `${greeting}, ${name}! 👋`;

  animateCounter('streakCount',  s.current_streak || 0);
  animateCounter('pointsCount',  s.total_points || 0);
  animateCounter('contentCount', s.total_content_generated || 0);
  animateCounter('quizCount',    s.total_quizzes_taken || 0);
  animateCounter('topicsCount',  (s.completed_topics || []).length);

  const avgEl = document.getElementById('avgScore');
  if (avgEl) avgEl.textContent = s.total_quizzes_taken > 0 ? `${(s.average_quiz_score || 0).toFixed(0)}%` : '—';

  const skillEl = document.getElementById('skillBadge');
  const styleEl = document.getElementById('styleBadge');
  if (skillEl) skillEl.textContent = capitalize(s.skill_level || '—');
  if (styleEl) {
    const u = Storage.get('user') || {};
    styleEl.textContent = capitalize(s.learning_style || u.learning_style || '—');
  }

  const weakTopics = s.weak_topics || [];
  if (weakTopics.length > 0) {
    const section = document.getElementById('weakTopicsSection');
    const list    = document.getElementById('weakTopicsList');
    if (section) section.style.display = 'block';
    if (list)    list.innerHTML = weakTopics.map(t => `<span class="topic-tag">${t}</span>`).join('');
  }

  const strongTopics = s.strong_topics || [];
  if (strongTopics.length > 0) {
    const section = document.getElementById('strongTopicsSection');
    const list    = document.getElementById('strongTopicsList');
    if (section) section.style.display = 'block';
    if (list)    list.innerHTML = strongTopics.map(t =>
      `<span class="topic-tag" style="background:rgba(16,185,129,.1);border-color:rgba(16,185,129,.25);color:#6ee7b7">${t}</span>`
    ).join('');
  }
}

async function loadRecommendations() {
  const container = document.getElementById('recommendationsContainer');
  if (!container) return;

  const res = await API.get('/recommendations/');
  if (!res.ok) {
    container.innerHTML = '<p style="color:var(--t3);font-size:.85rem">Recommendations unavailable.</p>';
    return;
  }

  const recs = res.data.recommendations;
  container.innerHTML = `
    <div class="rec-list">
      <div class="rec-item">
        <div class="rec-label">💡 Study Tip</div>
        <div class="rec-value">${recs.study_tip || '—'}</div>
      </div>
      <div class="rec-item">
        <div class="rec-label">🎯 Today's Challenge</div>
        <div class="rec-value">${recs.daily_challenge || '—'}</div>
      </div>
      <div class="rec-item">
        <div class="rec-label">📚 Suggested Next Topics</div>
        <div class="rec-topics">
          ${(recs.next_topics || []).map(t =>
            `<a href="/content/" class="rec-topic-chip"
              onclick="sessionStorage.setItem('quickTopic','${t.replace(/'/g,"\\'")}')">
              ${t}
            </a>`
          ).join('')}
        </div>
      </div>
      <div class="rec-motivation">✨ ${recs.motivational_message || 'Keep learning!'}</div>
    </div>
  `;
}

async function loadRecentContent() {
  const container = document.getElementById('recentContentList');
  if (!container) return;

  const res = await API.get('/content/history/');
  if (!res.ok || !res.data.contents?.length) return;

  const items = res.data.contents.slice(0, 5);
  container.innerHTML = items.map(c => `
    <div class="history-item" onclick="window.location='/content/'">
      <div class="history-topic">${c.is_bookmarked ? '⭐ ' : ''}${c.topic}</div>
      <div class="history-meta">
        <span class="history-badge">${capitalize(c.subject)}</span>
        <span>${capitalize(c.skill_level)}</span>
        <span>${capitalize(c.content_type)}</span>
        <span>${new Date(c.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  `).join('');
}

function animateCounter(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  let current = 0;
  const step = Math.max(1, Math.ceil(target / 30));
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(timer);
  }, 30);
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
