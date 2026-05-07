import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = '/api';

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState('');
  const [status, setStatus] = useState('✅ Connected to backend!');

  useEffect(() => { fetchFiles(); }, []);

  const fetchFiles = async () => {
    try {
      setStatus('🔄 Loading...');
      const res = await axios.get(`${API_URL}/files/`, { timeout: 10000 });
      setFiles(res.data);
      setStatus(`✅ Loaded ${res.data.length} file(s)`);
      return true;
    } catch (err) {
      console.error('Fetch error:', err);
      setStatus(`❌ Error: ${err.message || 'Connection failed'}`);
      return false;
    }
  };

  const handleRefresh = async () => {
    await fetchFiles();
    if (selectedFile && !files.find(f => f.id === selectedFile)) {
      setSelectedFile(null);
      setSummary('');
      setMessages([]);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setStatus('⏳ Uploading...');
    
    const formData = new FormData();
    formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
    formData.append('file', file);
    
    try {
      const res = await axios.post(`${API_URL}/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      });
      setStatus('✅ Processed!');
      setSelectedFile(res.data.file_id);
      await fetchFiles();
      alert(`✅ Success!\nFile: ${res.data.title}\nChunks: ${res.data.chunks}`);
    } catch (err) {
      console.error('Upload error:', err);
      const msg = err.response?.data?.error || err.message || 'Upload failed';
      setStatus(`❌ Error: ${msg}`);
      alert(`❌ Upload failed:\n${msg}`);
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async () => {
    if (!question.trim() || !selectedFile) return;
    const userMsg = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setQuestion('');
    
    try {
      const res = await axios.post(`${API_URL}/chat/`, {
        file_id: selectedFile,
        question: userMsg.content
      }, { timeout: 30000 });
      
      setMessages(prev => [...prev, { role: 'ai', content: res.data.answer }]);
      
      // ✅ Show timestamp if backend returns it
      if (res.data.referenced_timestamp != null) {
        const totalSec = Math.floor(res.data.referenced_timestamp);
        const mins = Math.floor(totalSec / 60);
        const secs = (totalSec % 60).toString().padStart(2, '0');
        setMessages(prev => [...prev, { 
          role: 'system', 
          content: `⏱️ Jump to ${mins}:${secs} in production player` 
        }]);
      }
    } catch (err) {
      console.error('Chat error:', err);
      const msg = err.response?.data?.error || err.message || 'Request failed';
      setMessages(prev => [...prev, { role: 'ai', content: `❌ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSummarize = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setStatus('✨ Generating...');
    try {
      const res = await axios.post(`${API_URL}/summarize/${selectedFile}/`, {}, { timeout: 30000 });
      setSummary(res.data.summary);
      setStatus('✅ Summary generated!');
    } catch (err) {
      console.error('Summary error:', err);
      const msg = err.response?.data?.error || err.message || 'Summary failed';
      setStatus(`❌ Error: ${msg}`);
      setSummary('• Summary generation encountered an error\n• Please try again');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (fileId) => {
    setSelectedFile(fileId);
    setSummary('');
    setMessages([]);
    setStatus(`📄 Selected: ${files.find(f => f.id === fileId)?.title || 'File'}`);
  };

  return (
    <div style={{ padding: '1.5rem', fontFamily: 'system-ui, sans-serif', maxWidth: '1100px', margin: '0 auto' }}>
      <header style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '2px solid #e5e7eb' }}>
        <h1 style={{ margin: 0, color: '#2563eb', fontSize: '1.8rem' }}>🤖 AI Document Q&A</h1>
        <p style={{ margin: '0.5rem 0 0', color: status.includes('❌') ? '#dc2626' : '#6b7280', fontSize: '0.95rem' }}>{status}</p>
      </header>

      <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', marginBottom: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <input type="file" onChange={handleUpload} disabled={uploading} accept=".pdf,.mp3,.mp4,.wav,.m4a,.ogg" style={{ display: 'none' }} id="file-upload" />
          <label htmlFor="file-upload" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.2rem', background: uploading ? '#9ca3af' : '#2563eb', color: 'white', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer', fontWeight: 500 }}>{uploading ? '⏳ Processing...' : '📁 Upload File'}</label>
          <button onClick={handleRefresh} disabled={loading || uploading} style={{ padding: '0.6rem 1rem', background: (loading || uploading) ? '#9ca3af' : '#6b7280', color: 'white', border: 'none', borderRadius: '8px', cursor: (loading || uploading) ? 'not-allowed' : 'pointer' }}>🔄 Refresh</button>
          <span style={{ fontSize: '0.9rem', color: '#6b7280' }}>Supports: PDF, MP3, MP4, WAV</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '1.1rem' }}>📁 Your Files</h3>
          {files.length === 0 ? <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>No files yet. Upload one!</p> : files.map(f => (
            <button key={f.id} onClick={() => handleFileSelect(f.id)} style={{ width: '100%', textAlign: 'left', padding: '0.75rem', marginBottom: '0.5rem', borderRadius: '8px', border: selectedFile === f.id ? '2px solid #2563eb' : '1px solid #e5e7eb', background: selectedFile === f.id ? '#eff6ff' : 'white', cursor: 'pointer' }}>
              <div style={{ fontWeight: 500 }}>{f.title}</div>
              <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>{f.file_type} • {new Date(f.created_at).toLocaleDateString()} {f.is_processed ? '• ✅' : '• ⏳'}</div>
            </button>
          ))}
        </div>
        <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>📝 Summary</h3>
            <button onClick={handleSummarize} disabled={!selectedFile || loading || uploading} style={{ padding: '0.4rem 0.9rem', background: (!selectedFile || loading || uploading) ? '#9ca3af' : '#16a34a', color: 'white', border: 'none', borderRadius: '6px', cursor: (!selectedFile || loading || uploading) ? 'not-allowed' : 'pointer' }}>{loading ? '⏳...' : '✨ Generate'}</button>
          </div>
          {summary ? <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', lineHeight: 1.6 }}>{summary}</div> : <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>Select a file to generate AI summary</p>}
        </div>
      </div>

      <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <h3 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '1.1rem' }}>💬 Ask Questions</h3>
        <div style={{ height: '220px', overflowY: 'auto', background: '#f9fafb', padding: '0.75rem', borderRadius: '8px', marginBottom: '0.75rem', border: '1px solid #e5e7eb' }}>
          {messages.length === 0 ? <p style={{ color: '#6b7280', textAlign: 'center', marginTop: '3.5rem' }}>Ask anything about your document...</p> : messages.map((m, i) => (
            <div key={i} style={{ marginBottom: '0.6rem', textAlign: m.role === 'user' ? 'right' : 'left' }}>
              <span style={{ display: 'inline-block', padding: '0.5rem 0.8rem', borderRadius: m.role === 'user' ? '14px 14px 2px 14px' : (m.role === 'system' ? '14px 2px 14px 14px' : '14px 14px 14px 2px'), background: m.role === 'user' ? '#2563eb' : (m.role === 'system' ? '#fef3c7' : '#e5e7eb'), color: m.role === 'user' ? 'white' : (m.role === 'system' ? '#92400e' : '#111827'), maxWidth: '85%', fontSize: '0.95rem' }}>{m.content}</span>
            </div>
          ))}
          {loading && <p style={{ color: '#6b7280', fontSize: '0.9rem', fontStyle: 'italic' }}>🤔 AI is thinking...</p>}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input value={question} onChange={(e) => setQuestion(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleSend()} placeholder="Ask about the document..." disabled={!selectedFile || loading || uploading} style={{ flex: 1, padding: '0.6rem 0.9rem', border: '1px solid #d1d5db', borderRadius: '8px', fontSize: '1rem' }} />
          <button onClick={handleSend} disabled={!selectedFile || loading || uploading || !question.trim()} style={{ padding: '0.6rem 1.2rem', background: (!selectedFile || loading || uploading || !question.trim()) ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '8px', cursor: (!selectedFile || loading || uploading || !question.trim()) ? 'not-allowed' : 'pointer', fontWeight: 500 }}>Send</button>
        </div>
      </div>

      {/* Timestamps section - only show for audio/video */}
      {selectedFile && files.find(f => f.id === selectedFile)?.file_type !== 'pdf' && (
        <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', marginTop: '1.5rem' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1.1rem' }}>⏱️ Timestamps</h3>
          <p style={{ margin: '0 0 0.75rem', color: '#6b7280', fontSize: '0.9rem' }}>When AI answers, relevant timestamps appear in chat for playback navigation.</p>
          <div style={{ fontSize: '0.85rem', color: '#6b7280', fontStyle: 'italic' }}>💡 Ask a question about your audio/video to see timestamp results in chat above.</div>
        </div>
      )}
    </div>
  );
}

export default App;