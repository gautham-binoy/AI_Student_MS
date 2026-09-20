import React, { useEffect, useState } from 'react';
import {
  Settings,
  ShieldCheck,
  Cpu,
  Database,
  Sliders,
  AlertTriangle,
  Lock,
  Info,
  Server
} from 'lucide-react';
import { api } from '../services/api';

export const SettingsPage: React.FC = () => {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await api.checkHealth();
        setHealth(data);
      } catch (err) {
        console.error('Failed to get health status:', err);
      }
    };
    fetchHealth();
  }, []);

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      {/* System Health Status */}
      <div className="glass-panel" style={{ marginBottom: 28 }}>
        <div className="panel-header">
          <div className="panel-title">
            <Server size={18} color="var(--accent-primary)" />
            <span>AI Pipeline & Engine Status</span>
          </div>
          <span style={{
            fontSize: '0.75rem',
            background: 'rgba(16, 185, 129, 0.15)',
            color: 'var(--accent-emerald)',
            padding: '4px 10px',
            borderRadius: 999,
            fontWeight: 600
          }}>
            {health?.status === 'healthy' ? 'Engine Online' : 'Connecting...'}
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <div style={{ background: 'var(--bg-surface-elevated)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Face Detector</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fff', marginTop: 4 }}>
              Ultralytics YOLO
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: 2 }}>
              {health?.ai_models?.face_detector || 'Ready'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface-elevated)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Embedding Network</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fff', marginTop: 4 }}>
              FaceNet (InceptionResnetV1)
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: 2 }}>
              {health?.ai_models?.face_recognizer || 'Ready'}
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface-elevated)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Multi-Object Tracking</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fff', marginTop: 4 }}>
              ByteTrack IoU Associator
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: 2 }}>
              Active (Kalman + Hungarian)
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface-elevated)', padding: 16, borderRadius: 'var(--radius-sm)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Database Store</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fff', marginTop: 4 }}>
              SQLite / PostgreSQL Ready
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-cyan)', marginTop: 2 }}>
              {health?.database || 'Connected'}
            </div>
          </div>
        </div>
      </div>

      {/* Model & Algorithm Thresholds */}
      <div className="glass-panel" style={{ marginBottom: 28 }}>
        <div className="panel-header">
          <div className="panel-title">
            <Sliders size={18} color="var(--accent-cyan)" />
            <span>Configured Algorithm Thresholds</span>
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Managed via .env
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
                <span style={{ fontWeight: 500 }}>YOLO Face Detection Threshold</span>
                <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>0.50</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Minimum confidence score required for bounding box extraction.
              </p>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
                <span style={{ fontWeight: 500 }}>Cosine Similarity Match Threshold</span>
                <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>0.55</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Similarity cutoff above which a face is associated with a registered student ID.
              </p>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: 4 }}>
                <span style={{ fontWeight: 500 }}>Temporal Confirmation Window</span>
                <span className="font-mono" style={{ color: 'var(--accent-cyan)' }}>2.0s</span>
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Consecutive observation period required before attendance status flips to "Present".
              </p>
            </div>
          </div>

          <div style={{ background: 'var(--bg-surface-elevated)', padding: 18, borderRadius: 'var(--radius-md)' }}>
            <h4 style={{ fontSize: '0.88rem', fontWeight: 600, marginBottom: 12, color: 'var(--accent-purple)' }}>
              Observable Engagement Formula
            </h4>
            <div className="font-mono" style={{ fontSize: '0.8rem', background: '#0b0f19', padding: 12, borderRadius: 6, color: '#e2e8f0', marginBottom: 12 }}>
              Score = 0.50 &times; Orientation + 0.30 &times; Visibility + 0.20 &times; Presence
            </div>
            <ul style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <li><strong>Orientation (50%):</strong> Bounding-box aspect ratio and bilateral facial gradient symmetry.</li>
              <li><strong>Visibility (30%):</strong> Detection confidence and resolution clarity.</li>
              <li><strong>Presence (20%):</strong> Ratio of active observed time within session window.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Biometric Privacy & Ethics Statement */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <Lock size={18} color="var(--accent-emerald)" />
            <span>Biometric Privacy & Ethical AI Disclosures</span>
          </div>
          <ShieldCheck size={18} color="var(--accent-emerald)" />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <div style={{
            background: 'rgba(99, 102, 241, 0.08)',
            borderLeft: '4px solid var(--accent-primary)',
            padding: '12px 16px',
            borderRadius: '0 6px 6px 0',
            color: '#e0e7ff'
          }}>
            <strong>Important Scientific Clarification:</strong> This software does NOT measure or claim to determine a student's internal mental state, cognitive focus, interest, or psychological concentration. The metric labeled <em>"Engagement Estimate"</em> is strictly an observable computer-vision estimate derived from physical head orientation and camera presence.
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 8 }}>
            <div style={{ background: 'var(--bg-surface-elevated)', padding: 14, borderRadius: 'var(--radius-sm)' }}>
              <h5 style={{ color: '#fff', fontSize: '0.84rem', marginBottom: 6 }}>Biometric Data Protection</h5>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Raw 512-d face embedding vectors are stored securely in database rows and are <strong>strictly omitted from public API schemas</strong>. Embeddings are never transmitted to client browsers or logged.
              </p>
            </div>

            <div style={{ background: 'var(--bg-surface-elevated)', padding: 14, borderRadius: 'var(--radius-sm)' }}>
              <h5 style={{ color: '#fff', fontSize: '0.84rem', marginBottom: 6 }}>Data Deletion & Storage</h5>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Deleting a student permanently purges their biometric embeddings and photo crops via database cascade constraints. Classroom video feeds are processed in-memory and not stored by default.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
