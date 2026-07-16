/* Fetching, uploading, refreshing, and selecting files. */

function showToast(message, type = 'success') {
  let overlay = document.getElementById('toast-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'toast-overlay';
    overlay.className = 'toast-overlay';
    document.body.appendChild(overlay);
  }

  overlay.innerHTML = `<div class="toast-box ${type}"><span>${message}</span></div>`;
  const box = overlay.querySelector('.toast-box');
  requestAnimationFrame(() => box.classList.add('show'));
  setTimeout(() => {
    box.classList.remove('show');
    setTimeout(() => {
      overlay.innerHTML = '';
    }, 200);
  }, 2200);
}

async function fetchFiles() {
  try {
    setStatus('Loading...', false);
    const response = await apiFetch('/files/');
    if (!response.ok) throw new Error('Connection failed');
    AppState.files = await response.json();
    setStatus(`${AppState.files.length} file(s) loaded`, false);
    renderFileList();
    updateControls();
  } catch (error) {
    setStatus(error.message || 'Connection failed', true);
  }
}

async function handleRefresh() {
  await fetchFiles();

  if (
    AppState.selectedFile &&
    !AppState.files.find(file => file.id === AppState.selectedFile)
  ) {
    AppState.selectedFile = null;
    AppState.messages = [];
    const summary = document.getElementById('summary-content');
    summary.textContent = 'Select a file and click Generate.';
    summary.className = 'summary-empty';
    renderMessages();
    updateControls();
  }
}

async function handleUpload(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  AppState.uploading = true;
  updateControls();
  setStatus('Uploading and processing...', false);

  const formData = new FormData();
  formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
  formData.append('file', file);

  try {
    const response = await apiFetch('/upload/', {
      method: 'POST',
      body: formData
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Upload failed');

    setStatus('Processed', false);
    AppState.selectedFile = data.file_id;
    await fetchFiles();
    showToast(`File uploaded successfully: ${data.title || file.name}`);
  } catch (error) {
    setStatus(error.message || 'Upload failed', true);
    showToast(error.message || 'Upload failed', 'error');
  } finally {
    AppState.uploading = false;
    document.getElementById('file-upload').value = '';
    updateControls();
  }
}

function selectFile(fileId) {
  AppState.selectedFile = fileId;
  AppState.messages = [];

  const summary = document.getElementById('summary-content');
  summary.textContent = 'Select a file and click Generate.';
  summary.className = 'summary-empty';

  const file = AppState.files.find(item => item.id === fileId);
  setStatus(`Selected: ${file ? file.title : 'File'}`, false);

  renderFileList();
  renderMessages();
  updateControls();
}

function confirmDeleteFile(fileId, title) {
  showConfirm(
    `Delete "${title}"? This cannot be undone.`,
    () => deleteFile(fileId)
  );
}

async function deleteFile(fileId) {
  try {
    setStatus('Deleting...', false);
    const response = await apiFetch(`/files/${fileId}/`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || 'Delete failed');
    }

    if (AppState.selectedFile === fileId) {
      AppState.selectedFile = null;
      AppState.messages = [];
      const summary = document.getElementById('summary-content');
      summary.textContent = 'Select a file and click Generate.';
      summary.className = 'summary-empty';
      renderMessages();
    }

    await fetchFiles();
    showToast('File deleted');
  } catch (error) {
    setStatus(error.message || 'Delete failed', true);
    showToast(error.message || 'Delete failed', 'error');
  } finally {
    updateControls();
  }
}
