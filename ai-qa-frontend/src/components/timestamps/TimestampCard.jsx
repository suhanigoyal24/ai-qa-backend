function TimestampCard({ selectedFile, files }) {
  const file = files.find(f => f.id === selectedFile);
  if (!selectedFile || file?.file_type === 'pdf') return null;

  return (
    <div style={{ padding: '12px 16px', borderTop: '1px solid #e5e7eb', fontSize: '13px', color: '#6b7280' }}>
      <div style={{ fontWeight: 500, color: '#374151', marginBottom: '4px' }}>⏱ Timestamps</div>
      <div style={{ fontStyle: 'italic', fontSize: '12px' }}>Ask a question about your audio/video — timestamps will appear in chat above.</div>
    </div>
  );
}

export default TimestampCard;