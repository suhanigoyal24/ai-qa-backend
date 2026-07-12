/* ui.js — shared DOM render helpers for index.html. */

function setStatus(text, isError) {
  const statusText = document.getElementById('status-text');
  statusText.textContent = text;
  statusText.className = 'status' + (isError ? ' error' : '');
}

function renderMarkdownLite(text) {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^\* /gm, '• ')
    .replace(/\n/g, '<br>');
}

function renderFileList() {
  const fileListEl = document.getElementById('file-list');
  fileListEl.innerHTML = '';

  if (AppState.files.length === 0) {
    fileListEl.innerHTML = '<p class="empty-note">No files yet</p>';
    return;
  }

  AppState.files.forEach(f => {
    const item = document.createElement('div');
    item.className = 'file-item-row' + (AppState.selectedFile === f.id ? ' active' : '');

    const btn = document.createElement('button');
    btn.className = 'file-item';
    btn.innerHTML = `
      <div class="title">${f.title}</div>
      <div class="meta">${f.file_type} &middot; ${new Date(f.created_at).toLocaleDateString()} &middot; ${f.is_processed ? 'Ready' : 'Processing'}</div>
    `;
    btn.onclick = () => selectFile(f.id);

    const delBtn = document.createElement('button');
    delBtn.className = 'file-delete-btn';
    delBtn.innerHTML = '✕';
    delBtn.title = 'Delete file';
    delBtn.onclick = (e) => {
      e.stopPropagation();
      confirmDeleteFile(f.id, f.title);
    };

    item.appendChild(btn);
    item.appendChild(delBtn);
    fileListEl.appendChild(item);
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
    if (m.role === 'ai') {
      bubble.innerHTML = renderMarkdownLite(m.content);
    } else {
      bubble.textContent = m.content;
    }
    row.appendChild(bubble);
    messagesEl.appendChild(row);
  });

  if (AppState.chatting) {
    const p = document.createElement('p');
    p.className = 'thinking';
    p.textContent = 'AI is thinking...';
    messagesEl.appendChild(p);
  }

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateControls() {
  const hasFile = !!AppState.selectedFile;
  const busy = AppState.summarizing || AppState.uploading;

  const summaryGenerateBtn = document.getElementById('summary-generate-btn');
  const questionInput = document.getElementById('question-input');
  const sendBtn = document.getElementById('send-btn');
  const refreshBtn = document.getElementById('refresh-btn');
  const uploadLabel = document.getElementById('upload-label');
  const topbarFilename = document.getElementById('topbar-filename');
  const timestampNote = document.getElementById('timestamp-note');

  summaryGenerateBtn.disabled = !hasFile || busy;

  questionInput.disabled = !hasFile || AppState.uploading;
  questionInput.placeholder = hasFile ? 'Ask about the document...' : 'Select a file first';
  sendBtn.disabled = !hasFile || AppState.uploading || AppState.chatting || !questionInput.value.trim();

  refreshBtn.disabled = AppState.summarizing || AppState.chatting || AppState.uploading;

  uploadLabel.textContent = AppState.uploading ? 'Processing...' : 'Upload File';
  uploadLabel.className = 'upload-label' + (AppState.uploading ? ' disabled' : '');

  const file = AppState.files.find(f => f.id === AppState.selectedFile);
  topbarFilename.textContent = file ? file.title : 'AI Document Q&A';

  timestampNote.style.display = (AppState.selectedFile && file && file.file_type !== 'pdf') ? 'block' : 'none';
}

function showConfirm(message, onConfirm) {
  let overlay = document.getElementById('confirm-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'confirm-overlay';
    overlay.className = 'toast-overlay';
    document.body.appendChild(overlay);
  }
  overlay.style.pointerEvents = 'auto';
  overlay.style.background = 'rgba(0,0,0,0.35)';
  overlay.innerHTML = `
    <div class="toast-box show confirm-box">
      <div style="font-weight:600; margin-bottom:12px;">${message}</div>
      <div style="display:flex; gap:10px; justify-content:flex-end;">
        <button class="btn-outline" id="confirm-cancel">Cancel</button>
        <button class="btn-green" style="background:#dc2626;" id="confirm-ok">Delete</button>
      </div>
    </div>
  `;

  const close = () => {
    overlay.style.pointerEvents = 'none';
    overlay.style.background = 'transparent';
    overlay.innerHTML = '';
  };

  document.getElementById('confirm-cancel').onclick = close;
  document.getElementById('confirm-ok').onclick = () => {
    close();
    onConfirm();
  };
}