import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import DocumentManager from './components/DocumentManager';
import MatchDashboard from './components/MatchDashboard';
import ChatWindow from './components/ChatWindow';
import HistoryView from './components/HistoryView';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('matcher');
  const [documents, setDocuments] = useState([]);
  const [selectedResume, setSelectedResume] = useState('');
  const [selectedJob, setSelectedJob] = useState('');
  const [matchReport, setMatchReport] = useState(null);
  const [isMatching, setIsMatching] = useState(false);
  const [globalError, setGlobalError] = useState(null);

  // Fetch document inventory
  async function refreshDocuments() {
    try {
      const docs = await api.listDocuments();
      setDocuments(docs);

      // Auto-populate resume & job dropdowns if not yet set
      if (!selectedResume) {
        const resumeDoc = docs.find((d) => d.doc_type === 'resume' || d.filename.toLowerCase().includes('resume'));
        if (resumeDoc) setSelectedResume(resumeDoc.filename);
      }
      if (!selectedJob) {
        const jobDoc = docs.find((d) => d.doc_type === 'job_description' || d.filename.toLowerCase().includes('job'));
        if (jobDoc) setSelectedJob(jobDoc.filename);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }

  useEffect(() => {
    refreshDocuments();
  }, []);

  // Run resume vs. job matching analysis
  async function handleRunMatch() {
    if (!selectedResume || !selectedJob) return;
    setIsMatching(true);
    setGlobalError(null);

    try {
      const report = await api.compareResumeAndJob(selectedResume, selectedJob);
      setMatchReport(report);
      setActiveTab('matcher');
    } catch (err) {
      setGlobalError(err.message || 'Comparison failed. Ensure both documents have been uploaded.');
    } finally {
      setIsMatching(false);
    }
  }

  return (
    <div className="app-container">
      {/* Top Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Global Error Banner */}
      {globalError && (
        <div style={{
          background: 'var(--danger-bg)',
          color: 'var(--danger)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '10px',
          padding: '12px 18px',
          fontSize: '0.88rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span>{globalError}</span>
          <button
            onClick={() => setGlobalError(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 800 }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Tab 1: Resume & Job Matcher */}
      {activeTab === 'matcher' && (
        <main className="main-grid">
          <DocumentManager
            documents={documents}
            onRefreshDocuments={refreshDocuments}
            selectedResume={selectedResume}
            setSelectedResume={setSelectedResume}
            selectedJob={selectedJob}
            setSelectedJob={setSelectedJob}
            onRunMatch={handleRunMatch}
            isMatching={isMatching}
          />
          <MatchDashboard
            report={matchReport}
            resumeFilename={selectedResume}
            jobFilename={selectedJob}
            onSwitchToChat={() => setActiveTab('chat')}
          />
        </main>
      )}

      {/* Tab 2: Grounded RAG Chat */}
      {activeTab === 'chat' && (
        <main style={{ maxWidth: '900px', margin: '0 auto', width: '100%' }}>
          <ChatWindow documents={documents} />
        </main>
      )}

      {/* Tab 3: Database History */}
      {activeTab === 'history' && (
        <main style={{ maxWidth: '1000px', margin: '0 auto', width: '100%' }}>
          <HistoryView
            onLoadComparison={(item) => {
              setMatchReport(item);
              setSelectedResume(item.resume_filename);
              setSelectedJob(item.job_filename);
              setActiveTab('matcher');
            }}
          />
        </main>
      )}
    </div>
  );
}
