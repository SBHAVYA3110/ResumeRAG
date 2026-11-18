import React, { useState } from 'react';
import { UploadCloud, File, Trash2, CheckCircle2, AlertCircle, RefreshCw, Layers } from 'lucide-react';
import { api } from '../services/api';

export default function DocumentManager({
  documents,
  onRefreshDocuments,
  selectedResume,
  setSelectedResume,
  selectedJob,
  setSelectedJob,
  onRunMatch,
  isMatching,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // File upload handler
  async function handleFileUpload(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage(`'${file.name}' is not a PDF file. Please upload a .pdf document.`);
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setUploadMessage(null);

    try {
      const result = await api.uploadDocument(file);
      setUploadMessage(`Indexed '${file.name}' (${result.total_pages} pages, ${result.total_chunks} chunks).`);
      await onRefreshDocuments();

      // Auto-select based on filename heuristic
      const lower = file.name.toLowerCase();
      if (lower.includes('resume') && !selectedResume) {
        setSelectedResume(file.name);
      } else if ((lower.includes('job') || lower.includes('jd')) && !selectedJob) {
        setSelectedJob(file.name);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  }

  // File deletion handler
  async function handleDelete(filename) {
    if (!window.confirm(`Delete '${filename}' and remove all its vector embeddings?`)) {
      return;
    }
    try {
      await api.deleteDocument(filename);
      if (selectedResume === filename) setSelectedResume('');
      if (selectedJob === filename) setSelectedJob('');
      await onRefreshDocuments();
    } catch (err) {
      setErrorMessage(err.message || 'Failed to delete document.');
    }
  }

  // Format bytes to human readable string
  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 KB';
    const kb = bytes / 1024;
    return kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB`;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Upload Dropzone */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <UploadCloud size={20} color="var(--primary)" />
            Document Ingestion
          </h2>
          <button
            onClick={onRefreshDocuments}
            className="btn btn-secondary"
            style={{ padding: '6px 10px', fontSize: '0.75rem' }}
            title="Refresh documents list"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        <div
          className={`dropzone ${isDragging ? 'active' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              handleFileUpload(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => document.getElementById('pdf-upload-input').click()}
        >
          <input
            id="pdf-upload-input"
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileUpload(e.target.files[0]);
              }
            }}
          />

          {isUploading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
              <div className="spinner" />
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                Extracting text, chunking & indexing vectors...
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
              <UploadCloud size={32} color="var(--primary)" />
              <p style={{ fontWeight: 600, fontSize: '0.92rem' }}>
                Drag & drop Resume or Job Description PDF here
              </p>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                or click to browse from your computer
              </p>
            </div>
          )}
        </div>

        {uploadMessage && (
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--success)', fontSize: '0.82rem' }}>
            <CheckCircle2 size={16} />
            <span>{uploadMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--danger)', fontSize: '0.82rem' }}>
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}
      </div>

      {/* Uploaded Documents List */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <Layers size={20} color="#818cf8" />
            Indexed Files ({documents.length})
          </h2>
        </div>

        {documents.length === 0 ? (
          <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No documents uploaded yet. Upload a resume and a job description to get started!
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '280px', overflowY: 'auto' }}>
            {documents.map((doc) => {
              const isResume = doc.filename === selectedResume;
              const isJob = doc.filename === selectedJob;

              return (
                <div
                  key={doc.id || doc.filename}
                  style={{
                    background: 'var(--bg-secondary)',
                    border: isResume ? '1px solid #10b981' : isJob ? '1px solid #3b82f6' : '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '10px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                    <File size={20} color={doc.doc_type === 'resume' ? '#10b981' : '#3b82f6'} style={{ flexShrink: 0 }} />
                    <div style={{ minWidth: 0 }}>
                      <p style={{ fontWeight: 600, fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {doc.filename}
                      </p>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '2px' }}>
                        <span className={`badge ${doc.doc_type === 'resume' ? 'badge-success' : 'badge-info'}`}>
                          {doc.doc_type === 'resume' ? 'Resume' : 'Job Desc'}
                        </span>
                        <span className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>
                          {doc.total_pages} {doc.total_pages === 1 ? 'page' : 'pages'}
                        </span>
                        <span className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>
                          {doc.total_chunks} chunks
                        </span>
                        <span className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>
                          {formatBytes(doc.file_size_bytes)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDelete(doc.filename)}
                    className="btn btn-danger"
                    style={{ padding: '6px', borderRadius: '6px' }}
                    title={`Delete ${doc.filename}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Match Configuration Card */}
      <div className="card" style={{ border: '1px solid rgba(99, 102, 241, 0.4)' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '14px', color: 'var(--text-primary)' }}>
          Compare Resume & Job
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
              Select Candidate Resume:
            </label>
            <select
              className="input-field"
              value={selectedResume}
              onChange={(e) => setSelectedResume(e.target.value)}
            >
              <option value="">-- Choose Resume PDF --</option>
              {documents.map((d) => (
                <option key={`resume-${d.filename}`} value={d.filename}>
                  {d.filename}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
              Select Job Description:
            </label>
            <select
              className="input-field"
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
            >
              <option value="">-- Choose Job Description PDF --</option>
              {documents.map((d) => (
                <option key={`job-${d.filename}`} value={d.filename}>
                  {d.filename}
                </option>
              ))}
            </select>
          </div>

          <button
            className="btn btn-primary"
            disabled={!selectedResume || !selectedJob || isMatching}
            onClick={onRunMatch}
            style={{ marginTop: '8px', width: '100%' }}
          >
            {isMatching ? (
              <>
                <div className="spinner" />
                Analyzing Alignment with Gemini...
              </>
            ) : (
              'Run AI Match Analysis'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
