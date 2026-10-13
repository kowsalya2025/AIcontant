/* ==============================================
   EduAI — Core App JavaScript
   Auth, API helpers, and shared utilities
   ============================================== */

const API_BASE = '/api';

// ---- Storage Helpers ----
const Storage = {
  get: (key) => {
    try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
  },
  set: (key, val) => localStorage.setItem(key, JSON.stringify(val)),
  remove: (key) => localStorage.removeItem(key),
  clear: () => localStorage.clear(),
};

// ---- API Client ----
const API = {
  token: () => Storage.get('token'),

  headers() {
    const h = { 'Content-Type': 'application/json' };
    const t = this.token();
    if (t) h['Authorization'] = `Token ${t}`;
    return h;
  },

  async request(method, endpoint, body = null) {
    const opts = { method, headers: this.headers() };
    if (body) opts.body = JSON.stringify(body);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, opts);
      const data = await res.json();
      return { ok: res.ok, status: res.status, data };
    } catch (err) {
      console.error('API Error:', err);
      return { ok: false, status: 0, data: { error: 'Network error. Please try again.' } };
    }
  },

  get: (endpoint) => API.request('GET', endpoint),
  post: (endpoint, body) => API.request('POST', endpoint, body),
  put: (endpoint, body) => API.request('PUT', endpoint, body),

  async upload(endpoint, formData) {
    const headers = {};
    const t = this.token();
    if (t) headers['Authorization'] = `Token ${t}`;
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST', headers, body: formData
      });
      const data = await res.json();
      return { ok: res.ok, data };
    } catch (err) {
      return { ok: false, data: { error: 'Upload failed.' } };
    }
  }
};

// ---- Auth Guards ----
function requireAuth() {
  if (!Storage.get('token')) {
    window.location.href = '/';
    return false;
  }
  return true;
}

function redirectIfLoggedIn() {
  if (Storage.get('token')) {
    window.location.href = '/dashboard/';
  }
}

// ---- Logout ----
async function logout() {
  await API.post('/auth/logout/');
  Storage.clear();
  window.location.href = '/';
}

// ---- Auth Page Handlers ----
function switchTab(tab) {
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const loginTab = document.getElementById('loginTab');
  const registerTab = document.getElementById('registerTab');
  if (!loginForm) return;

  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
    loginTab.classList.add('active');
    registerTab.classList.remove('active');
  } else {
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
    loginTab.classList.remove('active');
    registerTab.classList.add('active');
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');

  setButtonLoading(btn, true);
  errEl.classList.add('hidden');

  const res = await API.post('/auth/login/', { email, password });

  if (res.ok) {
    Storage.set('token', res.data.token);
    Storage.set('user', res.data.user);
    window.location.href = '/dashboard/';
  } else {
    const msg = res.data.non_field_errors?.[0] || res.data.error || 'Login failed.';
    showError(errEl, msg);
    setButtonLoading(btn, false);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const errEl = document.getElementById('registerError');
  const btn = document.getElementById('registerBtn');

  const password = document.getElementById('regPassword').value;
  const password2 = document.getElementById('regPassword2').value;

  if (password !== password2) {
    showError(errEl, 'Passwords do not match.');
    return;
  }

  const payload = {
    email: document.getElementById('regEmail').value,
    full_name: document.getElementById('regName').value,
    password,
    password2,
    skill_level: document.getElementById('regSkill').value,
    learning_style: document.getElementById('regStyle').value,
  };

  setButtonLoading(btn, true);
  errEl.classList.add('hidden');

  const res = await API.post('/auth/register/', payload);

  if (res.ok) {
    Storage.set('token', res.data.token);
    Storage.set('user', res.data.user);
    window.location.href = '/dashboard/';
  } else {
    const msgs = Object.values(res.data).flat();
    showError(errEl, msgs[0] || 'Registration failed.');
    setButtonLoading(btn, false);
  }
}

// ---- UI Helpers ----
function setButtonLoading(btn, loading) {
  if (!btn) return;
  const text = btn.querySelector('.btn-text');
  const loader = btn.querySelector('.btn-loader');
  btn.disabled = loading;
  if (text) text.classList.toggle('hidden', loading);
  if (loader) loader.classList.toggle('hidden', !loading);
}

function showError(el, msg) {
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function showSuccess(el, msg) {
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 3000);
}

// ---- Simple Markdown Renderer ----
function renderMarkdown(text) {
  if (!text) return '';
  return text
    // Code blocks
    .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Headers
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr>')
    // Blockquote
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // Unordered list items
    .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
    // Wrap consecutive li's in ul
    .replace(/(<li>.*<\/li>(\n|$))+/g, (m) => `<ul>${m}</ul>`)
    // Numbered list
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Paragraphs (double newlines)
    .replace(/\n\n/g, '</p><p>')
    // Single newlines
    .replace(/\n/g, '<br>');
}

// ---- Toast notifications ----
function showToast(msg, type = 'info', duration = 3500) {
  const icons = { success: '✅', error: '❌', info: '💡' };
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || '💡'}</span><span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  if (path === '/' || path === '') {
    redirectIfLoggedIn();
  } else if (path !== '/') {
    requireAuth();
  }
});
