function Sidebar({ files, selectedFile, onSelect, onUpload, uploading }) {
  return (
    <aside style={{ width: '220px', flexShrink: 0, background: '#f9fafb', borderRight: '1px solid #e5e7eb',
      display: 'flex', flexDirection: 'column', padding: '16px 12px', gap: '2px', height: '100vh', overflowY: 'auto' }}>

      <div style={{ fontSize: '15px', fontWeight: 600, color: '#2563eb', padding: '4px 8px 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        🤖 AI Doc Q&A
      </div>

      <input type="file" onChange={onUpload} disabled={uploading} accept=".pdf,.mp3,.mp4,.wav,.m4a,.ogg" style={{ display: 'none' }} id="sidebar-upload" />
      <label htmlFor="sidebar-upload" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '8px',
        background: uploading ? '#9ca3af' : '#2563eb', color: 'white', cursor: uploading ? 'not-allowed' : 'pointer',
        fontSize: '13px', fontWeight: 500, marginBottom: '8px' }}>
        {uploading ? '⏳ Uploading...' : '📁 Upload File'}
      </label>

      <div style={{ fontSize: '11px', color: '#9ca3af', padding: '8px 10px 4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Your Files</div>

      {files.length === 0
        ? <p style={{ fontSize: '12px', color: '#9ca3af', padding: '0 10px' }}>No files yet</p>
        : files.map(f => (
          <button key={f.id} onClick={() => onSelect(f.id)}
            style={{ width: '100%', textAlign: 'left', padding: '8px 10px', borderRadius: '8px',
              border: 'none', background: selectedFile === f.id ? '#eff6ff' : 'transparent',
              cursor: 'pointer', color: selectedFile === f.id ? '#2563eb' : '#374151', fontWeight: selectedFile === f.id ? 500 : 400 }}>
            <div style={{ fontSize: '13px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {f.file_type === 'pdf' ? '📄' : f.file_type === 'mp3' || f.file_type === 'wav' ? '🎵' : '🎬'} {f.title}
            </div>
            <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>
              {new Date(f.created_at).toLocaleDateString()} {f.is_processed ? '✅' : '⏳'}
            </div>
          </button>
        ))}
    </aside>
  );
}

export default Sidebar;