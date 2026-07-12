/* ui.js — shared DOM render helpers for index.html. */

function setStatus(text, isError) {
  const statusText = document.getElementById('status-text');
  statusText.textContent = text;
  statusText.className = 'status' + (isError ? ' error' : '');
}

function renderFileList() {
  const fileListEl = document.getElementById('file-list');
  fileListEl.innerHTML = '';

  if (AppState.files.length === 0) {
    fileListEl.innerHTML = '<p class="empty-note">No files yet</p>';
    return;
  }

  AppState.files.forEach(f => {
    const btn = document.createElement('button');
    btn.className = 'file-item' + (AppState.selectedFile === f.id ? ' active' : '');
    btn.innerHTML = `
      <div class="title">${f.title}</div>
      <div class="meta">${f.file_type} &middot; ${new Date(f.created_at).toLocaleDateString()} &middot; ${f.is_processed ? 'Ready' : 'Processing'}</div>
    `;
    btn.onclick = () => selectFile(f.id);
    fileListEl.appendChild(btn);
  });
}

function renderMessages() {
  const messagesEl = document.getElementById('messages');

  if (AppState.messages.length === 0) {
    messagesEl.innerHTML = '<p class="empty">Ask anything about your document...</p>';
    return;
  }

  messagesEl.innerHTML = '';
  AppState.messages.forEach(m => {
    const row = document.createElement('div');
    row.className = 'msg-row ' + m.role;
    const bubble = document.createElement('span');
    bubble.className = 'bubble ' + m.role;
    bubble.textContent = m.content;
    row.appendChild(bubble);
    messagesEl.appendChild(row);
  });

  if (AppState.loading) {
    const p = document.createElement('p');
    p.className = 'thinking';
    p.textContent = 'AI is thinking...';
    messagesEl.appendChild(p);
  }

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateControls() {
  const canAct = !!AppState.selectedFile && !AppState.loading && !AppState.uploading;

  const summarizeBtn = document.getElementById('summarize-btn');
  const summaryGenerateBtn = document.getElementById('summary-generate-btn');
  const questionInput = document.getElementById('question-input');
  const sendBtn = document.getElementById('send-btn');
  const refreshBtn = document.getElementById('refresh-btn');
  const uploadLabel = document.getElementById('upload-label');
  const topbarFilename = document.getElementById('topbar-filename');
  const timestampNote = document.getElementById('timestamp-note');

  summarizeBtn.disabled = !canAct;
  summaryGenerateBtn.disabled = !canAct;
  questionInput.disabled = !canAct;
  questionInput.placeholder = AppState.selectedFile ? 'Ask about the document...' : 'Select a file first';
  sendBtn.disabled = !canAct || !questionInput.value.trim();
  refreshBtn.disabled = AppState.loading || AppState.uploading;

  uploadLabel.textContent = AppState.uploading ? 'Processing...' : 'Upload File';
  uploadLabel.className = 'upload-label' + (AppState.uploading ? ' disabled' : '');

  const file = AppState.files.find(f => f.id === AppState.selectedFile);
  topbarFilename.textContent = file ? file.title : 'AI Document Q&A';

  timestampNote.style.display = (AppState.selectedFile && file && file.file_type !== 'pdf') ? 'block' : 'none';
}