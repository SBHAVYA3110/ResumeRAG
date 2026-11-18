import React from 'react';
import { Award, CheckCircle2, AlertTriangle, Lightbulb, UserCheck, Briefcase, Sparkles, ArrowRight } from 'lucide-react';

export default function MatchDashboard({ report, resumeFilename, jobFilename, onSwitchToChat }) {
  if (!report) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'rgba(99, 102, 241, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px',
        }}>
          <Sparkles size={32} color="var(--primary)" />
        </div>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '8px' }}>
          Ready for Intelligent Resume Alignment
        </h3>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '500px', margin: '0 auto 24px', fontSize: '0.9rem' }}>
          Select an uploaded candidate resume and a job description on the left pane, then click
          <strong style={{ color: 'var(--text-primary)' }}> "Run AI Match Analysis" </strong>
          to generate an instant, deep semantic comparison.
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', flexWrap: 'wrap' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '12px 18px', borderRadius: '8px', fontSize: '0.82rem', border: '1px solid var(--border)' }}>
            1. Upload Resume & JD (PDF)
          </div>
          <div style={{ background: 'var(--bg-secondary)', padding: '12px 18px', borderRadius: '8px', fontSize: '0.82rem', border: '1px solid var(--border)' }}>
            2. Run Semantic Vector Comparison
          </div>
          <div style={{ background: 'var(--bg-secondary)', padding: '12px 18px', borderRadius: '8px', fontSize: '0.82rem', border: '1px solid var(--border)' }}>
            3. Review Skill Gaps & Action Items
          </div>
        </div>
      </div>
    );
  }

  // Calculate score colors
  const score = report.match_score;
  const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
  const scoreBadgeClass = score >= 80 ? 'badge-success' : score >= 60 ? 'badge-warning' : 'badge-danger';
  const scoreLabel = score >= 80 ? 'Strong Candidate Match' : score >= 60 ? 'Moderate Match (Gaps Detected)' : 'Low Match (Significant Gaps)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner: Score & Candidate Info */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          {/* Circular Score Visualizer */}
          <div style={{
            position: 'relative',
            width: '90px',
            height: '90px',
            borderRadius: '50%',
            background: `conic-gradient(${scoreColor} ${score * 3.6}deg, var(--bg-secondary) 0deg)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 0 20px ${scoreColor}33`,
            flexShrink: 0,
          }}>
            <div style={{
              width: '74px',
              height: '74px',
              borderRadius: '50%',
              background: 'var(--bg-card)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <span style={{ fontSize: '1.45rem', fontWeight: 800, color: scoreColor, lineHeight: 1 }}>
                {score}%
              </span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Match
              </span>
            </div>
          </div>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className={`badge ${scoreBadgeClass}`}>{scoreLabel}</span>
            </div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 800, margin: '2px 0' }}>
              {report.candidate_name || 'Candidate'}
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Briefcase size={15} color="var(--primary)" />
              Target Position: <strong style={{ color: 'var(--text-primary)' }}>{report.role_title || 'Target Role'}</strong>
            </p>
          </div>
        </div>

        {/* Quick action button to chat about this comparison */}
        <button
          onClick={onSwitchToChat}
          className="btn btn-secondary"
          style={{ padding: '8px 16px', fontSize: '0.85rem' }}
        >
          Ask Questions About This Candidate
          <ArrowRight size={15} />
        </button>
      </div>

      {/* Executive Summary */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Lightbulb size={18} color="#f59e0b" />
            Executive Alignment Summary
          </h3>
        </div>
        <p style={{ fontSize: '0.92rem', color: 'var(--text-primary)', lineHeight: 1.7 }}>
          {report.summary}
        </p>
      </div>

      {/* Side-by-Side Skills Analysis Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {/* Matching Skills */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title" style={{ color: '#10b981' }}>
              <CheckCircle2 size={18} color="#10b981" />
              Matching Skills ({report.matching_skills?.length || 0})
            </h3>
          </div>
          {report.matching_skills && report.matching_skills.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {report.matching_skills.map((skill, idx) => (
                <span key={idx} className="badge badge-success" style={{ fontSize: '0.82rem', padding: '6px 12px' }}>
                  ✓ {skill}
                </span>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No direct skill overlaps identified.</p>
          )}
        </div>

        {/* Missing Skills */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title" style={{ color: '#f59e0b' }}>
              <AlertTriangle size={18} color="#f59e0b" />
              Missing Skills / Gaps ({report.missing_skills?.length || 0})
            </h3>
          </div>
          {report.missing_skills && report.missing_skills.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {report.missing_skills.map((skill, idx) => (
                <span key={idx} className="badge badge-warning" style={{ fontSize: '0.82rem', padding: '6px 12px' }}>
                  ⚠ {skill}
                </span>
              ))}
            </div>
          ) : (
            <p style={{ color: '#10b981', fontSize: '0.85rem' }}>Outstanding! Candidate meets all primary listed requirements.</p>
          )}
        </div>
      </div>

      {/* Tailored Actionable Recommendations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Award size={18} color="var(--primary)" />
              Actionable Resume Tailoring Advice
            </h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {report.recommendations.map((rec, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  background: 'var(--bg-secondary)',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                }}
              >
                <span style={{
                  background: 'var(--primary)',
                  color: '#ffffff',
                  fontSize: '0.75rem',
                  fontWeight: 800,
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  marginTop: '2px',
                }}>
                  {idx + 1}
                </span>
                <p style={{ fontSize: '0.88rem', color: 'var(--text-primary)', margin: 0, lineHeight: 1.6 }}>
                  {rec}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
