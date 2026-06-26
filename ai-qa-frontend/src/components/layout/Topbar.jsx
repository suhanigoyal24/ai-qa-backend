function Topbar({ status, selectedFile, files, loading, uploading, onRefresh, onSummarize }) {
  const file = files.find(f => f.id === selectedFile);
  const isError = status.includes('❌') || status.includes('Error');

  return (
    <header style={{ height: '52px', background: 'white', borderBottom: '1px solid #e5e7eb',
      display: 'flex', alignItems: 'center', padding: '0 20px', gap: '12px', flexShrink: 0 }}>

      <div style={{ flex: 1, fontSize: '14px', fontWeight: 500, color: '#111827', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {file ? `📄 ${file.title}` : 'AI Document Q&A'}
      </div>

      <span style={{ fontSize: '12px', color: isError ? '#dc2626' : '#6b7280', flexShrink: 0 }}>{status}</span>

      <button onClick={onRefresh} disabled={loading || uploading}
        style={{ padding: '6px 12px', background: 'white', border: '1px solid #d1d5db', borderRadius: '7px',
          cursor: (loading || uploading) ? 'not-allowed' : 'pointer', fontSize: '12px', color: '#374151', flexShrink: 0 }}>
        🔄 Refresh
      </button>

      <button onClick={onSummarize} disabled={!selectedFile || loading || uploading}
        style={{ padding: '6px 12px', background: (!selectedFile || loading || uploading) ? '#9ca3af' : '#16a34a',
          color: 'white', border: 'none', borderRadius: '7px',
          cursor: (!selectedFile || loading || uploading) ? 'not-allowed' : 'pointer', fontSize: '12px', flexShrink: 0 }}>
        ✨ Summary
      </button>
    </header>
  );
}

export default Topbar;