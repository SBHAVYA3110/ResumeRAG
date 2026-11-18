import React, { useState, useEffect } from 'react';
import { History, FileText, MessageSquare, RefreshCw, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';
import { api } from '../services/api';

export default function HistoryView({ onLoadComparison }) {
  const [historyTab, setHistoryTab] = useState('matches');
  const [matches, setMatches] = useState([]);
  const [chatLogs, setChatLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      if (historyTab === 'matches') {
        const data = await api.getMatchHistory(20);
        setMatches(data);
      } else {
        const data = await api.getChatHistory(30);
        setChatLogs(data);
      }
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [historyTab]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="card">
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2 className="card-title">
              <History size={20} color="var(--primary)" />
              Database Audit History
            </h2>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                className={`btn ${historyTab === 'matches' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                onClick={() => setHistoryTab('matches')}
              >
                Match Reports ({matches.length})
              </button>
              <button
                className={`btn ${historyTab === 'chat' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                onClick={() => setHistoryTab('chat')}
              >
                Chat Logs ({chatLogs.length})
              </button>
            </div>
          </div>

          <button
            onClick={loadData}
            className="btn btn-secondary"
            style={{ padding: '6px 10px', fontSize: '0.75rem' }}
            title="Refresh history"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>
            <div className="spinner" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Loading relational database history...</p>
          </div>
        ) : historyTab === 'matches' ? (
          matches.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0', fontSize: '0.9rem' }}>
              No comparison records found in the database. Run an analysis on the Job Matcher tab!
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {matches.map((item) => {
                const scoreColor = item.match_score >= 80 ? '#10b981' : item.match_score >= 60 ? '#f59e0b' : '#ef4444';
                return (
                  <div
                    key={item.id}
                    style={{
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--border)',
                      borderRadius: '10px',
                      padding: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '16px',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                        <span
                          className="badge"
                          style={{
                            background: `${scoreColor}22`,
                            color: scoreColor,
                            fontWeight: 800,
                            borderColor: `${scoreColor}55`,
                          }}
                        >
                          {item.match_score}% Match
                        </span>
                        <h4 style={{ margin: 0, fontSize: '0.98rem' }}>{item.candidate_name}</h4>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          for <strong>{item.role_title}</strong>
                        </span>
                      </div>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                        Files: {item.resume_filename} ↔ {item.job_filename} • {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>

                    <button
                      className="btn btn-secondary"
                      style={{ fontSize: '0.82rem', padding: '6px 14px' }}
                      onClick={() => onLoadComparison(item)}
                    >
                      View Report
                      <ArrowRight size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          )
        ) : chatLogs.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0', fontSize: '0.9rem' }}>
            No chat history recorded yet. Ask a question on the RAG Chat tab!
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {chatLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: '10px',
                  padding: '14px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <p style={{ fontWeight: 700, fontSize: '0.9rem', color: '#818cf8', margin: 0 }}>
                    Q: {log.query}
                  </p>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-primary)', margin: '0 0 8px 0', lineHeight: 1.5 }}>
                  {log.answer}
                </p>
                {log.citations && log.citations.length > 0 && (
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {log.citations.map((c, i) => (
                      <span key={i} className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                        {c}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
