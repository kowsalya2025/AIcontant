/* EduAI — Quiz JavaScript v2 */

let currentQuiz     = null;
let currentQuestion = 0;
let selectedAnswers = [];
let timerInterval   = null;
let quizStartTime   = null;
let isSubmittingQuiz = false;

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  await loadQuizHistory();

  // Pre-fill from content page
  const topic   = sessionStorage.getItem('quizTopic');
  const subject = sessionStorage.getItem('quizSubject');
  if (topic)   { document.getElementById('quizTopic').value   = topic;   sessionStorage.removeItem('quizTopic'); }
  if (subject) { document.getElementById('quizSubject').value = subject; sessionStorage.removeItem('quizSubject'); }
});

/* ─────────────────────── Generate ─────────────────────── */
async function generateQuiz(event) {
  event.preventDefault();

  const subject       = document.getElementById('quizSubject').value.trim();
  let topic           = document.getElementById('quizTopic').value.trim();
  const skill_level   = document.querySelector('input[name="quiz_level"]:checked')?.value || 'beginner';
  const num_questions = parseInt(document.getElementById('numQuestions').value) || 5;

  if (!subject) {
    alert('Please enter or select a subject.');
    return;
  }

  if (!topic) {
    topic = `${subject} Fundamentals`;
  }

  const btn       = document.getElementById('startQuizBtn');
  const btnText   = document.getElementById('startBtnText');
  const btnLoader = document.getElementById('startBtnLoader');
  btn.disabled = true;
  btnText.classList.add('hidden');
  btnLoader.classList.remove('hidden');

  const res = await API.post('/quiz/generate/', { subject, topic, skill_level, num_questions });

  btn.disabled = false;
  btnText.classList.remove('hidden');
  btnLoader.classList.add('hidden');

  if (res.ok) {
    currentQuiz     = res.data.quiz;
    selectedAnswers = new Array(currentQuiz.questions.length).fill('');
    currentQuestion = 0;
    startQuiz();
    showToast(`Quiz ready! ${currentQuiz.questions.length} questions generated.`, 'success');
  } else {
    showToast(res.data.error || 'Failed to generate quiz. Please try again.', 'error', 5000);
  }
}

/* ─────────────────────── Quiz flow ─────────────────────── */
function startQuiz() {
  isSubmittingQuiz = false;
  document.getElementById('quizSetup').classList.add('hidden');
  document.getElementById('activeQuiz').classList.remove('hidden');
  document.getElementById('quizResults').classList.add('hidden');

  quizStartTime = Date.now();
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - quizStartTime) / 1000);
    const m = Math.floor(elapsed / 60);
    const s = elapsed % 60;
    const timerEl = document.getElementById('quizTimer');
    if (timerEl) {
      timerEl.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${m}:${s.toString().padStart(2,'0')}`;
    }
  }, 1000);

  renderQuestion();
}

function renderQuestion() {
  const q     = currentQuiz.questions[currentQuestion];
  const total = currentQuiz.questions.length;

  document.getElementById('questionCounter').textContent = `Question ${currentQuestion + 1} of ${total}`;
  document.getElementById('questionNum').textContent     = `Q${currentQuestion + 1}`;
  document.getElementById('questionText').textContent    = q.question;
  document.getElementById('progressBar').style.width    = `${((currentQuestion + 1) / total) * 100}%`;

  const optionsGrid  = document.getElementById('optionsGrid');
  optionsGrid.innerHTML = (q.options || []).map((opt, idx) => {
    const letter     = ['A', 'B', 'C', 'D'][idx];
    const isSelected = selectedAnswers[currentQuestion] === letter;
    return `
      <button class="option-btn ${isSelected ? 'selected' : ''}"
              onclick="selectOption('${letter}', this)">
        <span class="option-letter">${letter}</span>
        <span>${opt}</span>
      </button>`;
  }).join('');

  document.getElementById('prevBtn').disabled = currentQuestion === 0;
  const nextBtn = document.getElementById('nextBtn');
  if (currentQuestion === total - 1) {
    nextBtn.innerHTML = `<span>Submit Quiz</span>`;
    nextBtn.onclick = submitQuiz;
  } else {
    nextBtn.innerHTML = `<span>Next</span> <span style="font-size:1.1em">&rarr;</span>`;
    nextBtn.onclick = nextQuestion;
  }
}

function selectOption(letter, btn) {
  document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  selectedAnswers[currentQuestion] = letter;
}

function nextQuestion() {
  if (currentQuestion < currentQuiz.questions.length - 1) {
    currentQuestion++;
    renderQuestion();
  }
}

function prevQuestion() {
  if (currentQuestion > 0) {
    currentQuestion--;
    renderQuestion();
  }
}

/* ─────────────────────── Submit ─────────────────────── */
async function submitQuiz() {
  if (isSubmittingQuiz || !currentQuiz) return;

  const unanswered = selectedAnswers.filter(a => !a).length;
  if (unanswered > 0) {
    if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
  }

  isSubmittingQuiz = true;
  clearInterval(timerInterval);
  const timeTaken = Math.floor((Date.now() - quizStartTime) / 1000);

  const nextBtn = document.getElementById('nextBtn');
  const prevBtn = document.getElementById('prevBtn');
  if (nextBtn) {
    nextBtn.disabled = true;
    nextBtn.innerHTML = '<span>Submitting...</span>';
  }
  if (prevBtn) prevBtn.disabled = true;

  try {
    const res = await API.post('/quiz/submit/', {
      quiz_id: currentQuiz.id,
      answers: selectedAnswers,
      time_taken_seconds: timeTaken
    });

    if (res.ok) {
      showResults(res.data);
      await loadQuizHistory();
    } else {
      showToast(res.data.error || 'Failed to submit quiz.', 'error');
      if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.innerHTML = '<span>Submit Quiz</span>';
      }
      if (prevBtn) prevBtn.disabled = currentQuestion === 0;
      isSubmittingQuiz = false;
    }
  } catch (err) {
    showToast('Network error while submitting quiz. Please try again.', 'error');
    if (nextBtn) {
      nextBtn.disabled = false;
      nextBtn.innerHTML = '<span>Submit Quiz</span>';
    }
    if (prevBtn) prevBtn.disabled = currentQuestion === 0;
    isSubmittingQuiz = false;
  }
}

/* ─────────────────────── Results ─────────────────────── */
function showResults(data, options = {}) {
  const isReview = Boolean(options.isReview);
  document.getElementById('quizSetup').classList.add('hidden');
  document.getElementById('activeQuiz').classList.add('hidden');
  document.getElementById('quizResults').classList.remove('hidden');

  const attempt  = data.attempt;
  const score    = Math.round(attempt.score);
  const correct  = attempt.correct_count;
  const total    = attempt.total_questions;
  const wrong    = total - correct;
  const timeSec  = attempt.time_taken_seconds || 0;
  const timeStr  = timeSec >= 60 ? `${Math.floor(timeSec/60)}m ${timeSec%60}s` : `${timeSec}s`;
  const pointsEarned = data.points_earned ?? (Math.floor(attempt.score / 10) * 5);

  // Animated score ring
  const ring = document.getElementById('scoreRing');
  if (ring) {
    const color = score >= 80 ? 'var(--emerald)' : score >= 60 ? 'var(--amber)' : 'var(--rose)';
    ring.style.background = `conic-gradient(${color} ${score}%, rgba(255,255,255,0.05) ${score}%)`;
    ring.style.setProperty('--pct', `${score}%`);
  }
  document.getElementById('scoreNumber').textContent = `${score}%`;
  document.getElementById('correctCount').textContent = correct;
  document.getElementById('wrongCount').textContent   = wrong;
  document.getElementById('timeTaken').textContent    = timeStr;
  document.getElementById('pointsEarned').textContent = `+${pointsEarned}`;

  const titles = score >= 90 ? 'Excellent Work!' : score >= 70 ? 'Great Job!' : score >= 50 ? 'Good Effort!' : 'Keep Going!';
  document.getElementById('resultsTitle').textContent    = isReview ? `Quiz Review: ${attempt.quiz_topic}` : titles;
  document.getElementById('resultsSubtitle').textContent = isReview
    ? `${capitalize(attempt.quiz_subject)} · You scored ${correct} out of ${total} (${new Date(attempt.completed_at).toLocaleDateString()})`
    : `You got ${correct} out of ${total} correct.`;

  // AI Feedback
  const feedbackEl = document.getElementById('aiFeedback');
  if (attempt.feedback) {
    feedbackEl.style.display = 'block';
    feedbackEl.innerHTML = `<strong style="display:inline-flex;align-items:center;gap:6px;margin-bottom:6px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green-600)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg> AI Feedback:</strong><br>${attempt.feedback}`;
  } else {
    feedbackEl.style.display = 'none';
  }

  // Answer review
  const reviewEl = document.getElementById('answersReview');
  reviewEl.innerHTML = (attempt.correct_answers || []).map((a, i) => `
    <div class="answer-item ${a.is_correct ? 'correct' : 'wrong'}">
      <div class="answer-q">${i + 1}. ${a.question}</div>
      <div class="answer-detail">
        Your answer: <span class="${a.is_correct ? 'answer-correct' : 'answer-wrong'}">${a.your_answer || '(skipped)'}</span>
        ${!a.is_correct ? ` · Correct: <span class="answer-correct">${a.correct_answer}</span>` : ' <span style="color:var(--emerald);font-weight:700">✓ Correct</span>'}
      </div>
      ${a.explanation ? `<div class="answer-detail" style="margin-top:.3rem;color:var(--t3)"><strong style="color:var(--green-700)">Explanation:</strong> ${a.explanation}</div>` : ''}
    </div>
  `).join('');

  if (!isReview) {
    showToast(`Quiz submitted! You scored ${score}%`, score >= 60 ? 'success' : 'info');
  }
}

/* ─────────────────────── Reset ─────────────────────── */
function resetQuiz() {
  currentQuiz      = null;
  selectedAnswers  = [];
  currentQuestion  = 0;
  isSubmittingQuiz = false;
  clearInterval(timerInterval);
  document.getElementById('quizSetup').classList.remove('hidden');
  document.getElementById('activeQuiz').classList.add('hidden');
  document.getElementById('quizResults').classList.add('hidden');
  document.getElementById('quizForm').reset();
  document.getElementById('numQLabel').textContent = '5';
}

/* ─────────────────────── History ─────────────────────── */
async function loadQuizHistory() {
  const container = document.getElementById('quizHistoryList');
  if (!container) return;

  const res = await API.get('/quiz/history/');
  if (!res.ok || !res.data.attempts?.length) {
    container.innerHTML = '<div class="empty-state"><span class="empty-icon"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--t4)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg></span><p>No quizzes taken yet. Generate your first quiz!</p></div>';
    return;
  }

  container.innerHTML = res.data.attempts.slice(0, 8).map(a => {
    const color = a.score >= 80 ? '#10b981' : a.score >= 60 ? '#f59e0b' : '#f43f5e';
    return `
      <div class="quiz-history-item" role="button" tabindex="0" onclick="viewQuizAttempt(${a.id})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();viewQuizAttempt(${a.id});}">
        <div class="qh-score" style="color:${color}">${Math.round(a.score)}%</div>
        <div class="qh-info">
          <div class="qh-topic">${a.quiz_topic}</div>
          <div class="qh-meta">${capitalize(a.quiz_subject)} · ${a.correct_count}/${a.total_questions} correct · ${new Date(a.completed_at).toLocaleDateString()}</div>
        </div>
        <div class="qh-review">Review &rarr;</div>
      </div>`;
  }).join('');
}

async function viewQuizAttempt(attemptId) {
  const res = await API.get(`/quiz/history/${attemptId}/`);
  if (res.ok && res.data.attempt) {
    showResults({ attempt: res.data.attempt }, { isReview: true });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    showToast(res.data.error || 'Could not load quiz review.', 'error');
  }
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
