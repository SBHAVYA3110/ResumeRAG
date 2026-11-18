import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, CheckCircle2, AlertCircle, FileText, Sparkles, BookOpen } from 'lucide-react';
import { api } from '../services/api';

export default function ChatWindow({ documents }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I am your AI assistant powered by Gemini and ChromaDB. Ask me any question about your uploaded resumes or job descriptions, and I will answer strictly based on the extracted text with verifiable source citations.',
      citations: [],
      is_grounded: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [queryInput, setQueryInput] = useState('');
  const [selectedDocFilter, setSelectedDocFilter] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll chat to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Suggested prompt handler
  const handleSuggestedPrompt = (promptText) => {
    setQueryInput(promptText);
  };

  // Submit query
  const handleSend = async (e) => {
    if (e) e.preventDefault();
    const trimmed = queryInput.trim();
    if (!trimmed || isLoading) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQueryInput('');
    setIsLoading(true);

    try {
      const response = await api.askQuestion(
        trimmed,
        selectedDocFilter || null,
        4,
      );

      const botMessage = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        citations: response.citations || [],
        is_grounded: response.is_grounded !== false,
        supporting_sources: response.supporting_sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      const errorMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${err.message || 'Unable to retrieve an answer at this time.'}`,
        citations: [],
        is_grounded: false,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '680px', padding: 0, overflow: 'hidden' }}>
      {/* Chat Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        background: 'var(--bg-card)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            background: 'rgba(99, 102, 241, 0.15)',
            padding: '8px',
            borderRadius: '8px',
            display: 'flex',
          }}>
            <Bot size={20} color="var(--primary)" />
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>
              Grounded Conversational RAG
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
              Retrieves top semantic vector chunks & generates grounded responses
            </p>
          </div>
        </div>

        {/* Document Filter Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Filter Document:</span>
          <select
            className="input-field"
            style={{ width: 'auto', padding: '6px 10px', fontSize: '0.8rem' }}
            value={selectedDocFilter}
            onChange={(e) => setSelectedDocFilter(e.target.value)}
          >
            <option value="">All Uploaded Documents</option>
            {documents.map((d) => (
              <option key={d.filename} value={d.filename}>
                {d.filename}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Suggested Prompts Bar */}
      <div style={{
        padding: '10px 20px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        overflowX: 'auto',
      }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Sparkles size={13} color="var(--primary)" />
          Try asking:
        </span>
        <button
          className="badge badge-neutral"
          style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
          onClick={() => handleSuggestedPrompt("Where does Alex Morgan currently work and what are their key responsibilities?")}
        >
          Candidate Current Role
        </button>
        <button
          className="badge badge-neutral"
          style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
          onClick={() => handleSuggestedPrompt("What are the primary technical requirements and backend stack for the job?")}
        >
          Job Tech Stack
        </button>
        <button
          className="badge badge-neutral"
          style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}
          onClick={() => handleSuggestedPrompt("Does the candidate have experience with AI or machine learning systems?")}
        >
          AI/ML Experience
        </button>
      </div>

      {/* Message Feed */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-start',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
            }}
          >
            {msg.role === 'assistant' && (
              <div style={{
                background: 'rgba(99, 102, 241, 0.2)',
                padding: '8px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <Bot size={16} color="var(--primary)" />
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: msg.role === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                  background: msg.role === 'user' ? 'var(--primary)' : 'var(--bg-secondary)',
                  color: '#ffffff',
                  border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
                  boxShadow: 'var(--shadow-sm)',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                }}
              >
                {msg.content}

                {/* Grounding & Citations section for Assistant responses */}
                {msg.role === 'assistant' && msg.id !== 'welcome' && (
                  <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                      {msg.is_grounded ? (
                        <span className="badge badge-success" style={{ fontSize: '0.72rem' }}>
                          <CheckCircle2 size={12} />
                          Grounded in Context
                        </span>
                      ) : (
                        <span className="badge badge-warning" style={{ fontSize: '0.72rem' }}>
                          <AlertCircle size={12} />
                          No Grounding Found
                        </span>
                      )}
                    </div>

                    {msg.citations && msg.citations.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <BookOpen size={12} /> Sources:
                        </span>
                        {msg.citations.map((cite, cIdx) => (
                          <span
                            key={cIdx}
                            className="badge badge-neutral"
                            style={{ fontSize: '0.72rem', color: '#818cf8', borderColor: 'rgba(99, 102, 241, 0.3)' }}
                          >
                            <FileText size={11} />
                            {cite}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <span style={{
                fontSize: '0.7rem',
                color: 'var(--text-muted)',
                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                padding: '0 4px',
              }}>
                {msg.timestamp}
              </span>
            </div>

            {msg.role === 'user' && (
              <div style={{
                background: 'var(--primary)',
                padding: '8px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <User size={16} color="#ffffff" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ background: 'rgba(99, 102, 241, 0.2)', padding: '8px', borderRadius: '50%' }}>
              <Bot size={16} color="var(--primary)" />
            </div>
            <div style={{
              background: 'var(--bg-secondary)',
              padding: '12px 18px',
              borderRadius: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              border: '1px solid var(--border)',
            }}>
              <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} />
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Searching vector chunks & generating grounded answer...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Query Input Bar */}
      <form onSubmit={handleSend} style={{
        padding: '16px 20px',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        gap: '12px',
        background: 'var(--bg-card)',
      }}>
        <input
          type="text"
          className="input-field"
          placeholder="Ask a question about your documents (e.g., 'What is Alex Morgan's salary expectation?')..."
          value={queryInput}
          onChange={(e) => setQueryInput(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!queryInput.trim() || isLoading}
          style={{ flexShrink: 0 }}
        >
          <Send size={16} />
          Send
        </button>
      </form>
    </div>
  );
}
