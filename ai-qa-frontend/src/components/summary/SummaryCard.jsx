function SummaryCard({ summary, selectedFile, loading, uploading, onSummarize }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <span style={{ fontWeight: 500, fontSize: '13px', color: '#374151' }}>Summary</span>
        <button onClick={onSummarize}
          disabled={!selectedFile || loading || uploading}
          style={{ padding: '4px 12px', background: (!selectedFile || loading || uploading) ? '#9ca3af' : '#16a34a',
            color: 'white', border: 'none', borderRadius: '6px', cursor: (!selectedFile || loading || uploading) ? 'not-allowed' : 'pointer', fontSize: '12px' }}>
          {loading ? '⏳...' : '✨ Generate'}
        </button>
      </div>
      {summary
        ? <div style={{ whiteSpace: 'pre-wrap', fontSize: '13px', lineHeight: 1.7, color: '#111827' }}>{summary}</div>
        : <p style={{ color: '#6b7280', fontSize: '13px' }}>Select a file and click Generate.</p>}
    </div>
  );
}

export default SummaryCard;