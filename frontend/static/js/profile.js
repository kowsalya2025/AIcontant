/* EduAI — Profile JavaScript v2 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  await Promise.all([loadProfile(), loadUploadedDocs()]);
});

/* ─────────────────────── Load Profile ─────────────────────── */
async function loadProfile() {
  const res = await API.get('/auth/profile/');
  if (!res.ok) return;

  const student = res.data.student;
  const lp      = res.data.learning_profile || {};

  // Avatar initials
  const initials = (student.full_name || student.display_name || 'S')
    .split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  document.getElementById('avatarInitials').textContent   = initials;
  document.getElementById('profileName').textContent      = student.full_name || student.display_name;
  document.getElementById('profileEmail').textContent     = student.email;
  document.getElementById('profileLevelBadge').textContent = capitalize(student.skill_level);

  document.getElementById('ps-points').textContent  = student.total_points   || 0;
  document.getElementById('ps-streak').textContent  = student.current_streak || 0;
  document.getElementById('ps-quizzes').textContent = lp.total_quizzes_taken || 0;

  // Form
  document.getElementById('editName').value  = student.full_name || '';
  document.getElementById('editEmail').value = student.email     || '';

  const skillInput = document.getElementById(`skill${capitalize(student.skill_level)}`);
  if (skillInput) skillInput.checked = true;

  const styleMap = { visual: 'Visual', reading: 'Reading', kinesthetic: 'Kinesthetic' };
  const styleInput = document.getElementById(`style${styleMap[student.learning_style] || 'Visual'}`);
  if (styleInput) styleInput.checked = true;

  const subjects = student.preferred_subjects || [];
  document.querySelectorAll('#subjectGrid input[type="checkbox"]').forEach(cb => {
    cb.checked = subjects.includes(cb.value);
  });

  const goalSlider = document.getElementById('dailyGoal');
  if (goalSlider && student.daily_goal_minutes) {
    goalSlider.value = student.daily_goal_minutes;
    document.getElementById('goalLabel').textContent = student.daily_goal_minutes;
  }

  Storage.set('user', student);
}

/* ─────────────────────── Save Profile ─────────────────────── */
async function saveProfile(event) {
  if (event) event.preventDefault();

  const skill_level         = document.querySelector('input[name="edit_skill"]:checked')?.value;
  const learning_style      = document.querySelector('input[name="edit_style"]:checked')?.value;
  const preferred_subjects  = Array.from(
    document.querySelectorAll('#subjectGrid input[type="checkbox"]:checked')
  ).map(cb => cb.value);
  const daily_goal_minutes  = parseInt(document.getElementById('dailyGoal').value) || 30;
  const full_name           = document.getElementById('editName').value.trim();

  const payload = { full_name, skill_level, learning_style, preferred_subjects, daily_goal_minutes };
  const btn     = document.getElementById('saveBtn');
  if (btn) btn.disabled = true;

  const res = await API.put('/auth/profile/', payload);
  if (btn) btn.disabled = false;

  if (res.ok) {
    Storage.set('user', res.data.student);
    showToast('Profile saved successfully!', 'success');
    document.getElementById('profileLevelBadge').textContent = capitalize(skill_level);
    if (full_name) document.getElementById('profileName').textContent = full_name;
    document.getElementById('profileSuccess').classList.remove('hidden');
    setTimeout(() => document.getElementById('profileSuccess').classList.add('hidden'), 3000);
  } else {
    const msgs = Object.values(res.data).flat();
    showToast(msgs[0] || 'Failed to save profile.', 'error');
  }
}

/* ─────────────────────── Upload Document ─────────────────────── */
async function uploadDocument(event) {
  event.preventDefault();

  const fileInput = document.getElementById('docFile');
  const file      = fileInput.files[0];
  if (!file) { showToast('Please select a file.', 'error'); return; }

  const formData = new FormData();
  formData.append('file',    file);
  formData.append('title',   document.getElementById('docTitle').value || file.name);
  formData.append('subject', document.getElementById('docSubject').value);

  const btn       = document.getElementById('uploadBtn');
  const btnText   = document.getElementById('uploadBtnText');
  const btnLoader = document.getElementById('uploadBtnLoader');
  if (btn) btn.disabled = true;
  if (btnText)   btnText.classList.add('hidden');
  if (btnLoader) btnLoader.classList.remove('hidden');

  const msgEl = document.getElementById('uploadMsg');
  if (msgEl) { msgEl.className = 'hidden'; }

  const res = await API.upload('/knowledge/upload/', formData);

  if (btn) btn.disabled = false;
  if (btnText)   btnText.classList.remove('hidden');
  if (btnLoader) btnLoader.classList.add('hidden');

  if (res.ok) {
    showToast(res.data.message || 'Document indexed successfully!', 'success');
    document.getElementById('uploadForm').reset();
    document.getElementById('fileUploadLabel').textContent = 'Click to select a file';
    await loadUploadedDocs();
  } else {
    showToast(res.data.error || 'Upload failed. Please try again.', 'error');
  }
}

/* ─────────────────────── Uploaded Docs ─────────────────────── */
async function loadUploadedDocs() {
  const container = document.getElementById('uploadedDocsList');
  if (!container) return;

  const res = await API.get('/knowledge/documents/');
  if (!res.ok || !res.data.documents?.length) {
    container.innerHTML = '<p style="color:var(--t3);font-size:.82rem;padding:.5rem 0">No documents uploaded yet. Upload a PDF or TXT to enhance AI content with RAG.</p>';
    return;
  }

  container.innerHTML = res.data.documents.map(d => `
    <div class="uploaded-doc-item">
      <span class="doc-icon">${d.file_type === 'pdf' ? '📕' : d.file_type === 'docx' ? '📘' : '📄'}</span>
      <div class="doc-info">
        <div class="doc-title">${d.title || d.original_filename || 'Document'}</div>
        <div class="doc-meta">${capitalize(d.subject)} · ${(d.file_type || 'TXT').toUpperCase()}</div>
      </div>
      ${d.is_indexed
        ? `<span class="doc-indexed">✅ ${d.chunk_count} chunks</span>`
        : '<span style="font-size:.72rem;color:var(--t3)">⏳ Indexing…</span>'}
    </div>
  `).join('');
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
