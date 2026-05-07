// src/App.jsx - FINAL WORKING VERSION
import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState('');
  const [status, setStatus] = useState('✅ Connected to backend!');

  // Fetch files on mount
  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      const res = await axios.get(`${API_URL}/files/`);
      setFiles(res.data);
      setStatus(`✅ Loaded ${res.data.length} file(s)`);
    } catch (err) {
      setStatus(`❌ Error: ${err.message}`);
      console.error('Fetch failed:', err);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setStatus('⏳ Uploading...');
    
    const formData = new FormData();
    formData.append('title', file.name);
    formData.append('file', file);
    
    try {
      const res = await axios.post(`${API_URL}/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setStatus('✅ Processed!');
      setSelectedFile(res.data.file_id);
      fetchFiles(); // Refresh list
      alert(`✅ Success! File ID: ${res.data.file_id}`);
    } catch (err) {
      setStatus(`❌ Error: ${err.response?.data?.error || err.message}`);
      alert('❌ Upload failed');
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
      });
      setMessages(prev => [...prev, { role: 'ai', content: res.data.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: `❌ ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSummarize = async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/summarize/${selectedFile}/`);
      setSummary(res.data.summary);
    } catch (err) {
      alert('Summary failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '1.5rem', fontFamily: 'system-ui, sans-serif', maxWidth: '1100px', margin: '0 auto' }}>
      {/* Header */}
      <header style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '2px solid #e5e7eb' }}>
        <h1 style={{ margin: 0, color: '#2563eb', fontSize: '1.8rem' }}>🤖 AI Document Q&A</h1>
        <p style={{ margin: '0.5rem 0 0', color: '#6b7280', fontSize: '0.95rem' }}>{status}</p>
      </header>

      {/* Upload Section */}
      <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', marginBottom: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <input type="file" onChange={handleUpload} disabled={uploading} accept=".pdf,.mp3,.mp4,.wav" style={{ display: 'none' }} id="file-upload" />
          <label htmlFor="file-upload" style={{ 
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.6rem 1.2rem', background: uploading ? '#9ca3af' : '#2563eb', 
            color: 'white', borderRadius: '8px', cursor: uploading ? 'not-allowed' : 'pointer', fontWeight: 500
          }}>
            {uploading ? '⏳ Processing...' : '📁 Upload File'}
          </label>
          <button onClick={fetchFiles} style={{ padding: '0.6rem 1rem', background: '#6b7280', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
            🔄 Refresh
          </button>
          <span style={{ fontSize: '0.9rem', color: '#6b7280' }}>Supports: PDF, MP3, MP4</span>
        </div>
      </div>

      {/* Files + Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {/* File List */}
        <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '1.1rem' }}>📁 Your Files</h3>
          {files.length === 0 ? (
            <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>No files yet. Upload one!</p>
          ) : files.map(f => (
            <button key={f.id} onClick={() => { setSelectedFile(f.id); setSummary(''); setMessages([]); }}
              style={{ width: '100%', textAlign: 'left', padding: '0.75rem', marginBottom: '0.5rem', borderRadius: '8px', border: selectedFile === f.id ? '2px solid #2563eb' : '1px solid #e5e7eb', background: selectedFile === f.id ? '#eff6ff' : 'white', cursor: 'pointer' }}>
              <div style={{ fontWeight: 500 }}>{f.title}</div>
              <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>{f.file_type} • {new Date(f.created_at).toLocaleDateString()}</div>
            </button>
          ))}
        </div>

        {/* Summary */}
        <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>📝 Summary</h3>
            <button onClick={handleSummarize} disabled={!selectedFile || loading} style={{ padding: '0.4rem 0.9rem', background: !selectedFile || loading ? '#9ca3af' : '#16a34a', color: 'white', border: 'none', borderRadius: '6px', cursor: (!selectedFile || loading) ? 'not-allowed' : 'pointer' }}>
              {loading ? '...' : '✨ Generate'}
            </button>
          </div>
          {summary ? <p style={{ whiteSpace: 'pre-wrap', fontSize: '0.95rem', lineHeight: 1.6 }}>{summary}</p> : <p style={{ color: '#6b7280', fontSize: '0.9rem' }}>Select a file to generate AI summary</p>}
        </div>
      </div>

      {/* Chat */}
      <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
        <h3 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '1.1rem' }}>💬 Ask Questions</h3>
        <div style={{ height: '220px', overflowY: 'auto', background: '#f9fafb', padding: '0.75rem', borderRadius: '8px', marginBottom: '0.75rem', border: '1px solid #e5e7eb' }}>
          {messages.length === 0 ? (
            <p style={{ color: '#6b7280', textAlign: 'center', marginTop: '3.5rem' }}>Ask anything about your document...</p>
          ) : messages.map((m, i) => (
            <div key={i} style={{ marginBottom: '0.6rem', textAlign: m.role === 'user' ? 'right' : 'left' }}>
              <span style={{ display: 'inline-block', padding: '0.5rem 0.8rem', borderRadius: m.role === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px', background: m.role === 'user' ? '#2563eb' : '#e5e7eb', color: m.role === 'user' ? 'white' : '#111827', maxWidth: '85%', fontSize: '0.95rem' }}>{m.content}</span>
            </div>
          ))}
          {loading && <p style={{ color: '#6b7280', fontSize: '0.9rem', fontStyle: 'italic' }}>🤔 AI is thinking...</p>}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input value={question} onChange={(e) => setQuestion(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleSend()} placeholder="Ask about the document..." disabled={!selectedFile} style={{ flex: 1, padding: '0.6rem 0.9rem', border: '1px solid #d1d5db', borderRadius: '8px', fontSize: '1rem' }} />
          <button onClick={handleSend} disabled={!selectedFile || loading || !question.trim()} style={{ padding: '0.6rem 1.2rem', background: (!selectedFile || loading || !question.trim()) ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '8px', cursor: (!selectedFile || loading || !question.trim()) ? 'not-allowed' : 'pointer', fontWeight: 500 }}>Send</button>
        </div>
      </div>

      {/* Timestamp Demo */}
      {selectedFile && (
        <div style={{ background: 'white', padding: '1.25rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)', marginTop: '1.5rem' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1.1rem' }}>⏱️ Timestamps (Demo)</h3>
          <p style={{ margin: '0 0 0.75rem', color: '#6b7280', fontSize: '0.9rem' }}>Click to jump to relevant section:</p>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <button onClick={() => alert('🎯 Would jump to 0:00 in production')} style={{ padding: '0.4rem 0.9rem', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem' }}>0:00 Intro</button>
            <button onClick={() => alert('🎯 Would jump to 0:45 in production')} style={{ padding: '0.4rem 0.9rem', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem' }}>0:45 Key Point</button>
            <button onClick={() => alert('🎯 Would jump to 2:00 in production')} style={{ padding: '0.4rem 0.9rem', background: '#e5e7eb', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '0.85rem' }}>2:00 Conclusion</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;