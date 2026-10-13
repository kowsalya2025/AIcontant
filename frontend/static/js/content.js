/* EduAI — Content Generation JavaScript */

let currentContentId = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  await loadContentHistory();

  // Quick topic from dashboard recommendation click
  const quickTopic = sessionStorage.getItem('quickTopic');
  if (quickTopic) {
    document.getElementById('topic').value = quickTopic;
    sessionStorage.removeItem('quickTopic');
  }
});

async function generateContent(event) {
  event.preventDefault();

  const subject = document.getElementById('subject').value;
  const topic = document.getElementById('topic').value.trim();
  const skill_level = document.querySelector('input[name="skill_level"]:checked')?.value || 'beginner';
  const content_type = document.querySelector('input[name="content_type"]:checked')?.value || 'notes';
  const custom_instructions = document.getElementById('customInstructions').value.trim();

  if (!topic) return;

  // Show loading state
  const btn = document.getElementById('generateBtn');
  const btnText = document.getElementById('generateBtnText');
  const btnLoader = document.getElementById('generateBtnLoader');
  btn.disabled = true;
  btnText.classList.add('hidden');
  btnLoader.classList.remove('hidden');

  document.getElementById('contentPlaceholder').classList.remove('hidden');
  document.getElementById('contentResult').classList.add('hidden');
  document.getElementById('contentPlaceholder').querySelector('h3').textContent = '🤖 AI is generating your content...';
  document.getElementById('contentPlaceholder').querySelector('p').textContent = 'Retrieving knowledge from RAG database and generating personalized content with Gemini AI...';

  const payload = { subject, topic, skill_level, content_type };
  if (custom_instructions) payload.custom_instructions = custom_instructions;

  const res = await API.post('/content/generate/', payload);

  btn.disabled = false;
  btnText.classList.remove('hidden');
  btnLoader.classList.add('hidden');

  if (res.ok) {
    displayContent(res.data.content, res.data.rag_used);
    await loadContentHistory();
  } else {
    document.getElementById('contentPlaceholder').querySelector('h3').textContent = '❌ Generation Failed';
    document.getElementById('contentPlaceholder').querySelector('p').textContent =
      res.data.error || 'Please try again. Make sure your Gemini API key is configured.';
  }
}

function displayContent(content, ragUsed) {
  document.getElementById('contentPlaceholder').classList.add('hidden');
  document.getElementById('contentResult').classList.remove('hidden');

  currentContentId = content.id;
  document.getElementById('resultTopic').textContent = content.topic;
  document.getElementById('resultLevel').textContent = `${capitalize(content.skill_level)} • ${capitalize(content.content_type)}`;

  const ragBadge = document.getElementById('ragBadge');
  if (ragUsed) ragBadge.classList.remove('hidden');
  else ragBadge.classList.add('hidden');

  const bodyEl = document.getElementById('contentBody');
  bodyEl.classList.add('markdown-content');
  bodyEl.innerHTML = renderMarkdown(content.content_body);

  // Scroll into view smoothly
  bodyEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function bookmarkContent() {
  if (!currentContentId) return;
  const btn = document.getElementById('bookmarkBtn');
  const res = await API.post(`/content/${currentContentId}/bookmark/`);
  if (res.ok) {
    btn.textContent = res.data.bookmarked ? '⭐' : '🔖';
    btn.title = res.data.bookmarked ? 'Bookmarked!' : 'Bookmark';
  }
}

function copyContent() {
  const bodyEl = document.getElementById('contentBody');
  if (!bodyEl) return;
  const text = bodyEl.innerText;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.btn-icon[onclick="copyContent()"]');
    if (btn) { btn.textContent = '✅'; setTimeout(() => btn.textContent = '📋', 2000); }
  });
}

function generateQuizFromContent() {
  const topic = document.getElementById('resultTopic')?.textContent;
  const subject = document.getElementById('subject')?.value;
  if (topic) {
    sessionStorage.setItem('quizTopic', topic);
    sessionStorage.setItem('quizSubject', subject || 'python');
  }
  window.location.href = '/quiz/';
}

async function loadContentHistory() {
  const container = document.getElementById('contentHistoryList');
  if (!container) return;

  const res = await API.get('/content/history/');
  if (!res.ok || !res.data.contents?.length) {
    container.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;padding:1rem">No content generated yet. Start by generating your first lesson!</p>';
    return;
  }

  container.innerHTML = res.data.contents.map(c => `
    <div class="history-item" onclick="loadHistoryContent(${c.id})">
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

async function loadHistoryContent(id) {
  const res = await API.get(`/content/${id}/`);
  if (res.ok) {
    displayContent(res.data, false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
