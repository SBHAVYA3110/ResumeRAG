import React, { useEffect, useState } from 'react';
import { Sparkles, FileText, Activity, ExternalLink, MessageSquare, History } from 'lucide-react';
import { api } from '../services/api';

export default function Navbar({ activeTab, setActiveTab }) {
  const [isBackendHealthy, setIsBackendHealthy] = useState(null);

  useEffect(() => {
    async function verifyHealth() {
      try {
        const res = await api.checkHealth();
        setIsBackendHealthy(res.status === 'healthy');
      } catch (err) {
        setIsBackendHealthy(false);
      }
    }
    verifyHealth();
    const interval = setInterval(verifyHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="card" style={{ padding: '16px 24px', borderRadius: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        {/* Logo & Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
            padding: '10px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(99, 102, 241, 0.4)',
          }}>
            <Sparkles size={22} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
              Resume<span style={{ color: '#818cf8' }}>RAG</span>
            </h1>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: 0 }}>
              AI Resume & Job Match Assistant • Powered by Gemini & ChromaDB
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            className={`btn ${activeTab === 'matcher' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('matcher')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <FileText size={16} />
            Job Matcher
          </button>
          <button
            className={`btn ${activeTab === 'chat' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('chat')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <MessageSquare size={16} />
            RAG Chat
          </button>
          <button
            className={`btn ${activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('history')}
            style={{ fontSize: '0.85rem', padding: '8px 14px' }}
          >
            <History size={16} />
            History
          </button>
        </div>

        {/* Backend Status & API Docs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: isBackendHealthy === true ? '#10b981' : isBackendHealthy === false ? '#ef4444' : '#f59e0b',
                boxShadow: isBackendHealthy ? '0 0 8px #10b981' : 'none',
                display: 'inline-block',
              }}
            />
            <span style={{ color: 'var(--text-secondary)' }}>
              {isBackendHealthy === true ? 'API Connected' : isBackendHealthy === false ? 'API Offline' : 'Connecting...'}
            </span>
          </div>

          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            title="Open FastAPI Swagger Interactive Documentation"
          >
            FastAPI Docs
            <ExternalLink size={14} />
          </a>
        </div>
      </div>
    </header>
  );
}
