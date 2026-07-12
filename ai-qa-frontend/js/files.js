/* files.js — fetching, uploading, refreshing, and selecting files. */

function showToast(message, type = 'success') {
  let overlay = document.getElementById('toast-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'toast-overlay';
    overlay.className = 'toast-overlay';
    document.body.appendChild(overlay);
  }
  const icon = type === 'success' ? '✓' : '⚠';
  overlay.innerHTML = `<div class="toast-box ${type}"><span class="toast-icon">${icon}</span><span>${message}</span></div>`;
  const box = overlay.querySelector('.toast-box');
  requestAnimationFrame(() => box.classList.add('show'));
  setTimeout(() => {
    box.classList.remove('show');
    setTimeout(() => { overlay.innerHTML = ''; }, 200);
  }, 2200);
}

async function fetchFiles() {
  try {
    setStatus('Loading...', false);
    const res = await apiFetch('/files/');
    if (!res.ok) throw new Error('Connection failed');
    AppState.files = await res.json();
    setStatus(`${AppState.files.length} file(s) loaded`, false);
    renderFileList();
    updateControls();
  } catch (err) {
    setStatus(err.message || 'Connection failed', true);
  }
}

async function handleRefresh() {
  await fetchFiles();
  if (AppState.selectedFile && !AppState.files.find(f => f.id === AppState.selectedFile)) {
    AppState.selectedFile = null;
    AppState.messages = [];
    const summaryContentEl = document.getElementById('summary-content');
    summaryContentEl.textContent = 'Select a file and click Generate.';
    summaryContentEl.className = 'summary-empty';
    renderMessages();
    updateControls();
  }
}

async function handleUpload(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;

  AppState.uploading = true;
  updateControls();
  setStatus('Uploading...', false);

  const formData = new FormData();
  formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
  formData.append('file', file);

  try {
    const res = await apiFetch('/upload/', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Upload failed');

    setStatus('Processed!', false);
    AppState.selectedFile = data.file_id;
    await fetchFiles();
    showToast(`File uploaded successfully — ${data.title || file.name}`, 'success');
  } catch (err) {
    setStatus(err.message || 'Upload failed', true);
    showToast(err.message || 'Upload failed', 'error');
  } finally {
    AppState.uploading = false;
    document.getElementById('file-upload').value = '';
    updateControls();
  }
}

function selectFile(fileId) {
  AppState.selectedFile = fileId;
  AppState.messages = [];

  const summaryContentEl = document.getElementById('summary-content');
  summaryContentEl.textContent = 'Select a file and click Generate.';
  summaryContentEl.className = 'summary-empty';

  const file = AppState.files.find(f => f.id === fileId);
  setStatus(`Selected: ${file ? file.title : 'File'}`, false);

  renderFileList();
  renderMessages();
  updateControls();
}

function confirmDeleteFile(fileId, title) {
  showConfirm(`Delete "${title}"? This cannot be undone.`, () => deleteFile(fileId));
}

async function deleteFile(fileId) {
  try {
    setStatus('Deleting...', false);
    const res = await apiFetch(`/files/${fileId}/`, { method: 'DELETE' });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || 'Delete failed');
    }

    if (AppState.selectedFile === fileId) {
      AppState.selectedFile = null;
      AppState.messages = [];
      const summaryContentEl = document.getElementById('summary-content');
      summaryContentEl.textContent = 'Select a file and click Generate.';
      summaryContentEl.className = 'summary-empty';
      renderMessages();
    }

    await fetchFiles();
    showToast('File deleted', 'success');
  } catch (err) {
    setStatus(err.message || 'Delete failed', true);
    showToast(err.message || 'Delete failed', 'error');
  } finally {
    updateControls();
  }
}