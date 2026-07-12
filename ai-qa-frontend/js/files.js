/* files.js — fetching, uploading, refreshing, and selecting files. */

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
    alert(`Success!\nFile: ${data.title || file.name}\nChunks: ${data.chunks}`);
  } catch (err) {
    setStatus(err.message || 'Upload failed', true);
    alert(`Upload failed:\n${err.message}`);
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