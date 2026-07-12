/* summary.js — generating the AI summary for the selected file. */

async function handleSummarize() {
  if (!AppState.selectedFile) return;

  const summaryContentEl = document.getElementById('summary-content');
  AppState.loading = true;
  setStatus('Generating summary...', false);
  updateControls();

  try {
    const res = await apiFetch(`/summarize/${AppState.selectedFile}/`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Summary failed');

    summaryContentEl.textContent = data.summary;
    summaryContentEl.className = 'summary-text';
    setStatus('Summary ready!', false);
  } catch (err) {
    summaryContentEl.textContent = 'Summary generation failed. Please try again.';
    summaryContentEl.className = 'summary-empty';
    setStatus(err.message || 'Summary failed', true);
  } finally {
    AppState.loading = false;
    updateControls();
  }
}