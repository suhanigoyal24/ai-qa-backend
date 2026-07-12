/* main.js — app state, auth guard, event wiring, and init for index.html. */

const AppState = {
  files: [],
  selectedFile: null,
  messages: [],
  loading: false,
  uploading: false
};

document.addEventListener('DOMContentLoaded', () => {
  if (!isLoggedIn()) {
    redirectToLogin();
    return;
  }

  const userBadge = document.getElementById('current-user');
  if (userBadge) userBadge.textContent = getUsername() || '';

  document.getElementById('logout-btn').addEventListener('click', () => {
    clearSession();
    window.location.href = 'login.html';
  });

  document.getElementById('file-upload').addEventListener('change', handleUpload);
  document.getElementById('refresh-btn').addEventListener('click', handleRefresh);
  document.getElementById('summarize-btn').addEventListener('click', handleSummarize);
  document.getElementById('summary-generate-btn').addEventListener('click', handleSummarize);
  document.getElementById('send-btn').addEventListener('click', handleSend);
  document.getElementById('question-input').addEventListener('input', updateControls);
  document.getElementById('question-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSend();
  });

  fetchFiles();
});