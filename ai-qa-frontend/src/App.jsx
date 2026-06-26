import { useState, useEffect } from 'react';
import axios from 'axios';
import DashboardLayout from './components/layout/DashboardLayout';
import Sidebar from './components/layout/Sidebar';
import Topbar from './components/layout/Topbar';
import ChatWindow from './components/chat/ChatWindow';
import SummaryCard from './components/summary/SummaryCard';
import TimestampCard from './components/timestamps/TimestampCard';

const API_URL = 'https://gsuhani17-ai-qa-backend.hf.space/api';

function App() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState('');
  const [status, setStatus] = useState('Connected to backend!');

  useEffect(() => { fetchFiles(); }, []);

  const fetchFiles = async () => {
    try {
      setStatus('Loading...');
      const res = await axios.get(`${API_URL}/files/`, { timeout: 10000 });
      setFiles(res.data);
      setStatus(`${res.data.length} file(s) loaded`);
    } catch (err) {
      setStatus(`❌ ${err.message || 'Connection failed'}`);
    }
  };

  const handleRefresh = async () => {
    await fetchFiles();
    if (selectedFile && !files.find(f => f.id === selectedFile)) {
      setSelectedFile(null); setSummary(''); setMessages([]);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setStatus('Uploading...');
    const formData = new FormData();
    formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
    formData.append('file', file);
    try {
      const res = await axios.post(`${API_URL}/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000
      });
      setStatus('Processed!');
      setSelectedFile(res.data.file_id);
      await fetchFiles();
      alert(`✅ Success!\nFile: ${res.data.title}\nChunks: ${res.data.chunks}`);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Upload failed';
      setStatus(`❌ ${msg}`);
      alert(`❌ Upload failed:\n${msg}`);
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (fileId) => {
    setSelectedFile(fileId);
    setSummary(''); setMessages([]);
    setStatus(`Selected: ${files.find(f => f.id === fileId)?.title || 'File'}`);
  };

  const handleSend = async () => {
    if (!question.trim() || !selectedFile) return;
    const userMsg = { role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true); setQuestion('');
    try {
      const res = await axios.post(`${API_URL}/chat/`, { file_id: selectedFile, question: userMsg.content }, { timeout: 30000 });
      setMessages(prev => [...prev, { role: 'ai', content: res.data.answer }]);
      if (res.data.referenced_timestamp != null) {
        const t = Math.floor(res.data.referenced_timestamp);
        const m = Math.floor(t / 60), s = (t % 60).toString().padStart(2, '0');
        setMessages(prev => [...prev, { role: 'system', content: `⏱ Jump to ${m}:${s}` }]);
      }
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Request failed';
      setMessages(prev => [...prev, { role: 'ai', content: `❌ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSummarize = async () => {
    if (!selectedFile) return;
    setLoading(true); setStatus('Generating summary...');
    try {
      const res = await axios.post(`${API_URL}/summarize/${selectedFile}/`, {}, { timeout: 30000 });
      setSummary(res.data.summary);
      setStatus('Summary ready!');
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Summary failed';
      setStatus(`❌ ${msg}`);
      setSummary('• Summary generation failed\n• Please try again');
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout
      sidebar={
        <Sidebar
          files={files}
          selectedFile={selectedFile}
          onSelect={handleFileSelect}
          onUpload={handleUpload}
          uploading={uploading}
        />
      }
      topbar={
        <Topbar
          status={status}
          selectedFile={selectedFile}
          files={files}
          loading={loading}
          uploading={uploading}
          onRefresh={handleRefresh}
          onSummarize={handleSummarize}
        />
      }
    >
      {/* Left: Chat */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'white' }}>
        <ChatWindow
          messages={messages}
          loading={loading}
          question={question}
          setQuestion={setQuestion}
          onSend={handleSend}
          selectedFile={selectedFile}
          uploading={uploading}
        />
        <TimestampCard selectedFile={selectedFile} files={files} />
      </div>

      {/* Right: Summary panel */}
      <div style={{ width: '280px', flexShrink: 0, borderLeft: '1px solid #e5e7eb', padding: '16px', overflowY: 'auto', background: '#fafafa' }}>
        <SummaryCard
          summary={summary}
          selectedFile={selectedFile}
          loading={loading}
          uploading={uploading}
          onSummarize={handleSummarize}
        />
      </div>
    </DashboardLayout>
  );
}

export default App;