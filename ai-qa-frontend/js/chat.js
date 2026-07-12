/* chat.js — sending questions and rendering answers. */

async function handleSend() {
  const questionInput = document.getElementById('question-input');
  const question = questionInput.value.trim();
  if (!question || !AppState.selectedFile) return;

  AppState.messages.push({ role: 'user', content: question });
  questionInput.value = '';
  AppState.loading = true;
  renderMessages();
  updateControls();

  try {
    const res = await apiFetch('/chat/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: AppState.selectedFile, question })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Request failed');

    AppState.messages.push({ role: 'ai', content: data.answer });

    if (data.referenced_timestamp != null) {
      const totalSec = Math.floor(data.referenced_timestamp);
      const mins = Math.floor(totalSec / 60);
      const secs = (totalSec % 60).toString().padStart(2, '0');
      AppState.messages.push({ role: 'system', content: `Jump to ${mins}:${secs} in production player` });
    }
  } catch (err) {
    AppState.messages.push({ role: 'ai', content: err.message || 'Request failed' });
  } finally {
    AppState.loading = false;
    renderMessages();
    updateControls();
  }
}