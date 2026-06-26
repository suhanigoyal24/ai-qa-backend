function FileList({ files, selectedFile, onSelect }) {
  if (files.length === 0) {
    return <p style={{ color: '#6b7280', fontSize: '0.9rem', padding: '0.5rem 0' }}>No files yet. Upload one!</p>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {files.map(f => (
        <button key={f.id} onClick={() => onSelect(f.id)}
          style={{ width: '100%', textAlign: 'left', padding: '8px 10px', borderRadius: '8px',
            border: selectedFile === f.id ? '2px solid #2563eb' : '1px solid #e5e7eb',
            background: selectedFile === f.id ? '#eff6ff' : 'white', cursor: 'pointer' }}>
          <div style={{ fontWeight: 500, fontSize: '13px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.title}</div>
          <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
            {f.file_type} • {new Date(f.created_at).toLocaleDateString()} {f.is_processed ? '✅' : '⏳'}
          </div>
        </button>
      ))}
    </div>
  );
}

export default FileList;