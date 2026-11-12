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

  const subject = document.getElementById('subject').value.trim();
  let topic = document.getElementById('topic').value.trim();
  const skill_level = document.querySelector('input[name="skill_level"]:checked')?.value || 'beginner';
  const content_type = document.querySelector('input[name="content_type"]:checked')?.value || 'notes';
  const custom_instructions = document.getElementById('customInstructions').value.trim();

  if (!subject) {
    alert('Please enter or select a subject.');
    return;
  }

  // Topic is optional: if omitted, default to comprehensive overview
  if (!topic) {
    topic = `${subject} Overview & Fundamentals`;
  }

  // Show loading state
  const btn = document.getElementById('generateBtn');
  const btnText = document.getElementById('generateBtnText');
  const btnLoader = document.getElementById('generateBtnLoader');
  btn.disabled = true;
  btnText.classList.add('hidden');
  btnLoader.classList.remove('hidden');

  document.getElementById('contentPlaceholder').classList.remove('hidden');
  document.getElementById('contentResult').classList.add('hidden');
  document.getElementById('contentPlaceholder').querySelector('h3').textContent = 'AI is generating your content...';
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
    const errMsg = res.data.error || 'Please try again. Make sure your Gemini API key is configured.';
    document.getElementById('contentPlaceholder').querySelector('h3').textContent = '❌ Generation Failed';
    document.getElementById('contentPlaceholder').querySelector('p').textContent = errMsg;
    if (typeof showToast === 'function') {
      showToast(errMsg, 'error', 5000);
    }
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
    if (res.data.bookmarked) {
      btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`;
      btn.title = 'Bookmarked!';
    } else {
      btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>`;
      btn.title = 'Bookmark';
    }
  }
}

function copyContent() {
  const bodyEl = document.getElementById('contentBody');
  if (!bodyEl) return;
  const text = bodyEl.innerText;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById('copyBtn') || document.querySelector('.btn-icon[onclick="copyContent()"]');
    if (btn) {
      btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
      setTimeout(() => {
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
      }, 2000);
    }
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
      <div class="history-topic">
        ${c.is_bookmarked ? `<svg width="13" height="13" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px;margin-right:4px"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>` : ''}
        ${c.topic}
      </div>
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
