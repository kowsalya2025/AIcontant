/* EduAI — Quiz JavaScript v2 */

let currentQuiz     = null;
let currentQuestion = 0;
let selectedAnswers = [];
let timerInterval   = null;
let quizStartTime   = null;

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

  const subject       = document.getElementById('quizSubject').value;
  const topic         = document.getElementById('quizTopic').value.trim();
  const skill_level   = document.querySelector('input[name="quiz_level"]:checked')?.value || 'beginner';
  const num_questions = parseInt(document.getElementById('numQuestions').value) || 5;

  if (!topic) return;

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
    showToast(res.data.error || 'Failed to generate quiz. Please try again.', 'error');
  }
}

/* ─────────────────────── Quiz flow ─────────────────────── */
function startQuiz() {
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
    if (timerEl) timerEl.textContent = `⏱ ${m}:${s.toString().padStart(2,'0')}`;
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
    nextBtn.textContent = '✅ Submit Quiz';
    nextBtn.onclick = submitQuiz;
  } else {
    nextBtn.textContent = 'Next →';
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
  clearInterval(timerInterval);
  const timeTaken  = Math.floor((Date.now() - quizStartTime) / 1000);
  const unanswered = selectedAnswers.filter(a => !a).length;

  if (unanswered > 0) {
    if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
  }

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
  }
}

/* ─────────────────────── Results ─────────────────────── */
function showResults(data) {
  document.getElementById('activeQuiz').classList.add('hidden');
  document.getElementById('quizResults').classList.remove('hidden');

  const attempt  = data.attempt;
  const score    = Math.round(attempt.score);
  const correct  = attempt.correct_count;
  const total    = attempt.total_questions;
  const wrong    = total - correct;
  const timeSec  = attempt.time_taken_seconds;
  const timeStr  = timeSec >= 60 ? `${Math.floor(timeSec/60)}m ${timeSec%60}s` : `${timeSec}s`;

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
  document.getElementById('pointsEarned').textContent = `+${data.points_earned}`;

  const titles = score >= 90 ? '🏆 Excellent Work!' : score >= 70 ? '🎉 Great Job!' : score >= 50 ? '👍 Good Effort!' : '💪 Keep Going!';
  document.getElementById('resultsTitle').textContent    = titles;
  document.getElementById('resultsSubtitle').textContent = `You got ${correct} out of ${total} correct.`;

  // AI Feedback
  const feedbackEl = document.getElementById('aiFeedback');
  if (attempt.feedback) {
    feedbackEl.style.display = 'block';
    feedbackEl.innerHTML = `<strong>🤖 AI Feedback:</strong><br>${attempt.feedback}`;
  }

  // Answer review
  const reviewEl = document.getElementById('answersReview');
  reviewEl.innerHTML = attempt.correct_answers.map((a, i) => `
    <div class="answer-item ${a.is_correct ? 'correct' : 'wrong'}">
      <div class="answer-q">${i + 1}. ${a.question}</div>
      <div class="answer-detail">
        Your answer: <span class="${a.is_correct ? 'answer-correct' : 'answer-wrong'}">${a.your_answer || '(skipped)'}</span>
        ${!a.is_correct ? ` · Correct: <span class="answer-correct">${a.correct_answer}</span>` : ' ✅'}
      </div>
      ${a.explanation ? `<div class="answer-detail" style="margin-top:.3rem;font-style:italic;color:var(--t3)">💡 ${a.explanation}</div>` : ''}
    </div>
  `).join('');

  showToast(`Quiz submitted! You scored ${score}%`, score >= 60 ? 'success' : 'info');
}

/* ─────────────────────── Reset ─────────────────────── */
function resetQuiz() {
  currentQuiz     = null;
  selectedAnswers = [];
  currentQuestion = 0;
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
    container.innerHTML = '<div class="empty-state"><span class="empty-icon">📝</span><p>No quizzes taken yet. Generate your first quiz!</p></div>';
    return;
  }

  container.innerHTML = res.data.attempts.slice(0, 8).map(a => {
    const color = a.score >= 80 ? '#10b981' : a.score >= 60 ? '#f59e0b' : '#f43f5e';
    return `
      <div class="quiz-history-item">
        <div class="qh-score" style="color:${color}">${Math.round(a.score)}%</div>
        <div class="qh-info">
          <div class="qh-topic">${a.quiz_topic}</div>
          <div class="qh-meta">${capitalize(a.quiz_subject)} · ${a.correct_count}/${a.total_questions} correct · ${new Date(a.completed_at).toLocaleDateString()}</div>
        </div>
      </div>`;
  }).join('');
}

function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, ' ');
}
