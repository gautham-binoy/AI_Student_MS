import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  Plus,
  Play,
  Square,
  Video,
  BarChart2,
  Trash2,
  Clock,
  BookOpen
} from 'lucide-react';
import { api } from '../services/api';
import { Session } from '../types';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';

export const SessionsPage: React.FC = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    class_name: '',
    date: new Date().toISOString().split('T')[0],
    start_time: '10:00:00',
    end_time: '11:00:00'
  });
  const [submitting, setSubmitting] = useState<boolean>(false);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const data = await api.getSessions();
      setSessions(data);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;

    try {
      setSubmitting(true);
      await api.createSession(formData);
      setIsModalOpen(false);
      setFormData({
        name: '',
        subject: '',
        class_name: '',
        date: new Date().toISOString().split('T')[0],
        start_time: '10:00:00',
        end_time: '11:00:00'
      });
      fetchSessions();
    } catch (err) {
      alert('Failed to create session.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStart = async (id: number) => {
    try {
      await api.startSession(id);
      fetchSessions();
    } catch (err) {
      alert('Failed to start session.');
    }
  };

  const handleStop = async (id: number) => {
    try {
      await api.stopSession(id);
      fetchSessions();
    } catch (err) {
      alert('Failed to stop session.');
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (confirm(`Delete session "${name}"? This will remove all associated attendance logs.`)) {
      try {
        await api.deleteSession(id);
        fetchSessions();
      } catch (err) {
        alert('Failed to delete session.');
      }
    }
  };

  return (
    <div>
      {/* Header Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 24
      }}>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Schedule, launch, and monitor automated AI attendance sessions.
        </p>

        <button
          className="btn btn-primary"
          onClick={() => setIsModalOpen(true)}
          style={{ gap: 8 }}
        >
          <Plus size={16} />
          <span>New Session</span>
        </button>
      </div>

      {/* Sessions Table */}
      <div className="glass-panel" style={{ padding: 0 }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Session Name</th>
                <th>Subject & Class</th>
                <th>Date & Time</th>
                <th>Status</th>
                <th>Present / Total</th>
                <th>Avg Engagement</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.id}>
                  <td>
                    <div style={{ fontWeight: 600, fontSize: '0.94rem' }}>{s.name}</div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>ID: #{s.id}</span>
                  </td>
                  <td>
                    <div>{s.subject || 'General'}</div>
                    <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{s.class_name || '—'}</span>
                  </td>
                  <td>
                    <div className="font-mono" style={{ fontSize: '0.85rem' }}>{s.date}</div>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      {s.start_time || '—'} {s.end_time ? `to ${s.end_time}` : ''}
                    </span>
                  </td>
                  <td><Badge status={s.status} /></td>
                  <td>
                    <span style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>{s.present_count}</span>
                    <span style={{ color: 'var(--text-muted)' }}> / {s.total_students}</span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600 }}>{Math.round(s.avg_engagement * 100)}%</span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
                      {s.status === 'scheduled' && (
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => handleStart(s.id)}
                          title="Start Session"
                          style={{ padding: '5px 10px', fontSize: '0.75rem' }}
                        >
                          <Play size={13} />
                          <span>Start</span>
                        </button>
                      )}

                      {s.status === 'active' && (
                        <>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => navigate('/live')}
                            title="Monitor Live"
                            style={{ padding: '5px 10px', fontSize: '0.75rem' }}
                          >
                            <Video size={13} />
                            <span>Monitor</span>
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleStop(s.id)}
                            title="Stop Session"
                            style={{ padding: '5px 10px', fontSize: '0.75rem' }}
                          >
                            <Square size={13} />
                            <span>Stop</span>
                          </button>
                        </>
                      )}

                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/analytics?session_id=${s.id}`)}
                        title="View Analytics"
                      >
                        <BarChart2 size={14} />
                      </button>

                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(s.id, s.name)}
                        title="Delete Session"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && !loading && (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: 36, color: 'var(--text-muted)' }}>
                    No sessions scheduled. Click "New Session" to create one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Session Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create Classroom Session"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleCreate} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Session'}
            </button>
          </>
        }
      >
        <form onSubmit={handleCreate}>
          <div className="input-group">
            <label className="input-label">Session / Course Name *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. CS401: Deep Learning Seminar"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div className="input-group">
              <label className="input-label">Subject</label>
              <input
                type="text"
                className="form-input"
                placeholder="Deep Learning"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              />
            </div>
            <div className="input-group">
              <label className="input-label">Class / Batch</label>
              <input
                type="text"
                className="form-input"
                placeholder="S7 AI & DS"
                value={formData.class_name}
                onChange={(e) => setFormData({ ...formData, class_name: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
            <div className="input-group">
              <label className="input-label">Date *</label>
              <input
                type="date"
                className="form-input font-mono"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                required
              />
            </div>
            <div className="input-group">
              <label className="input-label">Start Time</label>
              <input
                type="time"
                className="form-input font-mono"
                value={formData.start_time}
                onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
              />
            </div>
            <div className="input-group">
              <label className="input-label">End Time</label>
              <input
                type="time"
                className="form-input font-mono"
                value={formData.end_time}
                onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
              />
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
};
