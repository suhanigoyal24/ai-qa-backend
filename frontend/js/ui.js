/* Shared DOM render helpers for index.html. */

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

  AppState.files.forEach(file => {
    const item = document.createElement('div');
    item.className = 'file-item-row' + (
      AppState.selectedFile === file.id ? ' active' : ''
    );

    const button = document.createElement('button');
    button.className = 'file-item';

    const title = document.createElement('div');
    title.className = 'title';
    title.textContent = file.title;

    const metadata = document.createElement('div');
    metadata.className = 'meta';
    const state = file.is_processed ? 'Ready' : 'Processing';
    metadata.textContent = `${file.file_type} · ${new Date(file.created_at).toLocaleDateString()} · ${state}`;

    button.appendChild(title);
    button.appendChild(metadata);
    button.onclick = () => selectFile(file.id);

    const deleteButton = document.createElement('button');
    deleteButton.className = 'file-delete-btn';
    deleteButton.textContent = 'x';
    deleteButton.title = 'Delete file';
    deleteButton.onclick = event => {
      event.stopPropagation();
      confirmDeleteFile(file.id, file.title);
    };

    item.appendChild(button);
    item.appendChild(deleteButton);
    fileListEl.appendChild(item);
  });
}

function renderMessages() {
  const messagesEl = document.getElementById('messages');

  if (AppState.messages.length === 0) {
    messagesEl.innerHTML = '<p class="empty">Ask anything about your selected file...</p>';
    return;
  }

  messagesEl.innerHTML = '';
  AppState.messages.forEach(message => {
    const row = document.createElement('div');
    row.className = 'msg-row ' + message.role;
    const bubble = document.createElement('span');
    bubble.className = 'bubble ' + message.role;

    if (message.role === 'ai') {
      bubble.innerHTML = renderMarkdownLite(message.content);
    } else {
      bubble.textContent = message.content;
    }

    row.appendChild(bubble);
    messagesEl.appendChild(row);
  });

  if (AppState.chatting) {
    const thinking = document.createElement('p');
    thinking.className = 'thinking';
    thinking.textContent = 'AI is thinking...';
    messagesEl.appendChild(thinking);
  }

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateControls() {
  const hasFile = Boolean(AppState.selectedFile);
  const busy = AppState.summarizing || AppState.uploading;
  const summaryButton = document.getElementById('summary-generate-btn');
  const questionInput = document.getElementById('question-input');
  const sendButton = document.getElementById('send-btn');
  const refreshButton = document.getElementById('refresh-btn');
  const uploadLabel = document.getElementById('upload-label');
  const topbarFilename = document.getElementById('topbar-filename');
  const timestampNote = document.getElementById('timestamp-note');

  summaryButton.disabled = !hasFile || busy;
  questionInput.disabled = !hasFile || AppState.uploading;
  questionInput.placeholder = hasFile
    ? 'Ask about the selected file...'
    : 'Select a file first';
  sendButton.disabled = (
    !hasFile ||
    AppState.uploading ||
    AppState.chatting ||
    !questionInput.value.trim()
  );
  refreshButton.disabled = (
    AppState.summarizing ||
    AppState.chatting ||
    AppState.uploading
  );

  uploadLabel.textContent = AppState.uploading
    ? 'Processing...'
    : 'Upload File';
  uploadLabel.className = 'upload-label' + (
    AppState.uploading ? ' disabled' : ''
  );

  const file = AppState.files.find(
    item => item.id === AppState.selectedFile
  );
  topbarFilename.textContent = file ? file.title : 'AI Document Q&A';

  const hasTimestamps = file && (
    file.file_type === 'audio' || file.file_type === 'video'
  );
  timestampNote.style.display = hasTimestamps ? 'block' : 'none';
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
