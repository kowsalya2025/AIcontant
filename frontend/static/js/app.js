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

  getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  },

  headers() {
    const h = { 'Content-Type': 'application/json' };
    const t = this.token();
    if (t) h['Authorization'] = `Token ${t}`;
    const csrf = this.getCookie('csrftoken');
    if (csrf) h['X-CSRFToken'] = csrf;
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
  if (event) event.preventDefault();
  const emailEl = document.getElementById('loginEmail');
  const passEl = document.getElementById('loginPassword');
  const errEl = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');

  const email = (emailEl?.value || '').trim();
  const password = passEl?.value || '';

  if (!email) {
    showError(errEl, 'Please enter your email or username.');
    return;
  }
  if (!password) {
    showError(errEl, 'Please enter your password.');
    return;
  }

  setButtonLoading(btn, true);
  if (errEl) errEl.classList.add('hidden');

  const res = await API.post('/auth/login/', { email, password });

  if (res.ok) {
    Storage.set('token', res.data.token);
    Storage.set('user', res.data.user);
    window.location.href = '/dashboard/';
  } else {
    const msg = res.data.non_field_errors?.[0] || res.data.error || 'Login failed. Please check your credentials.';
    showError(errEl, msg);
    setButtonLoading(btn, false);
  }
}

async function handleRegister(event) {
  if (event) event.preventDefault();
  const errEl = document.getElementById('registerError');
  const btn = document.getElementById('registerBtn');

  const nameEl = document.getElementById('regName');
  const emailEl = document.getElementById('regEmail');
  const passEl = document.getElementById('regPassword');
  const pass2El = document.getElementById('regPassword2');
  const skillEl = document.getElementById('regSkill');

  const name = (nameEl?.value || '').trim();
  const email = (emailEl?.value || '').trim();
  const password = passEl?.value || '';
  const password2 = pass2El?.value || '';
  const skill_level = skillEl?.value || 'beginner';

  if (!name) {
    showError(errEl, 'Please enter your full name.');
    return;
  }
  if (!email) {
    showError(errEl, 'Please enter your email address.');
    return;
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    showError(errEl, 'Please enter a complete email address (e.g. yourname@gmail.com).');
    return;
  }
  if (!password) {
    showError(errEl, 'Please enter a password.');
    return;
  }
  if (password.length < 8) {
    showError(errEl, 'Password must be at least 8 characters.');
    return;
  }
  if (password !== password2) {
    showError(errEl, 'Passwords do not match.');
    return;
  }

  const payload = {
    email,
    full_name: name,
    password,
    password2,
    skill_level,
  };
  const regStyle = document.getElementById('regStyle');
  if (regStyle?.value) {
    payload.learning_style = regStyle.value;
  }

  setButtonLoading(btn, true);
  if (errEl) errEl.classList.add('hidden');

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
  if (!el) { alert(msg); return; }
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

// ---- Role-based Admin Nav Visibility ----
function syncAdminNav(user) {
  const adminSection = document.getElementById('adminNavSection');
  if (!adminSection) return;
  const isAdmin = Boolean(user && (user.is_staff || user.is_superuser));
  adminSection.style.display = isAdmin ? '' : 'none';
}

async function refreshAdminNavFromServer() {
  const adminSection = document.getElementById('adminNavSection');
  if (!adminSection || !Storage.get('token')) return;
  try {
    const res = await API.get('/auth/profile/');
    if (res.ok && res.data) {
      const userData = res.data.student || res.data;
      Storage.set('user', userData);
      syncAdminNav(userData);
    }
  } catch (e) {
    // Keep existing visibility (hidden by default for safety)
  }
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  if (path === '/' || path === '') {
    redirectIfLoggedIn();
  } else if (path !== '/') {
    if (requireAuth()) {
      syncAdminNav(Storage.get('user'));
      refreshAdminNavFromServer();
    }
  }
});
