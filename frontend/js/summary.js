/* Generate a plain-text AI summary for the selected file. */

async function handleSummarize() {
  if (!AppState.selectedFile) return;

  const summaryContent = document.getElementById('summary-content');
  AppState.summarizing = true;
  setStatus('Generating summary...', false);
  updateControls();

  try {
    const response = await apiFetch(
      `/summarize/${AppState.selectedFile}/`,
      { method: 'POST' }
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Summary failed');

    summaryContent.textContent = data.summary;
    summaryContent.className = 'summary-text';
    setStatus('Summary ready', false);
  } catch (error) {
    summaryContent.textContent = (
      'Summary generation failed. Please try again.'
    );
    summaryContent.className = 'summary-empty';
    setStatus(error.message || 'Summary failed', true);
  } finally {
    AppState.summarizing = false;
    updateControls();
  }
}
