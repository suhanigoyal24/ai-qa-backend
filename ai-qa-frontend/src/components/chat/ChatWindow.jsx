import { useRef, useEffect } from 'react';

function ChatWindow({ messages, loading, question, setQuestion, onSend, selectedFile, uploading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {messages.length === 0
          ? <p style={{ color: '#9ca3af', textAlign: 'center', marginTop: '60px', fontSize: '14px' }}>Ask anything about your document...</p>
          : messages.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <span style={{
                display: 'inline-block', padding: '9px 13px', borderRadius: '12px',
                maxWidth: '80%', fontSize: '13px', lineHeight: 1.6,
                background: m.role === 'user' ? '#2563eb' : m.role === 'system' ? '#fef3c7' : '#f3f4f6',
                color: m.role === 'user' ? 'white' : m.role === 'system' ? '#92400e' : '#111827'
              }}>{m.content}</span>
            </div>
          ))}
        {loading && <p style={{ color: '#9ca3af', fontSize: '13px', fontStyle: 'italic' }}>🤔 AI is thinking...</p>}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: '12px 16px', borderTop: '1px solid #e5e7eb', display: 'flex', gap: '8px' }}>
        <input
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onSend()}
          placeholder={selectedFile ? 'Ask about the document...' : 'Select a file first'}
          disabled={!selectedFile || loading || uploading}
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #d1d5db', borderRadius: '8px', fontSize: '13px', outline: 'none' }}
        />
        <button onClick={onSend}
          disabled={!selectedFile || loading || uploading || !question.trim()}
          style={{ padding: '8px 16px', background: (!selectedFile || loading || uploading || !question.trim()) ? '#9ca3af' : '#2563eb',
            color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 500, fontSize: '13px' }}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatWindow;