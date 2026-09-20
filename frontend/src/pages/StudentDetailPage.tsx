import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  GraduationCap,
  Calendar,
  Clock,
  Activity,
  CheckCircle2,
  XCircle,
  Mail,
  Building,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { StudentDetail, AttendanceRecord } from '../types';
import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';

export const StudentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [student, setStudent] = useState<StudentDetail | null>(null);
  const [attendanceLogs, setAttendanceLogs] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!id) return;
      try {
        setLoading(true);
        const [profile, logs] = await Promise.all([
          api.getStudent(Number(id)),
          api.getAttendance(undefined, undefined)
        ]);
        setStudent(profile);
        setAttendanceLogs(logs.filter((l) => l.student_id === Number(id)));
      } catch (err) {
        console.error('Failed to load student profile:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [id]);

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading student profile...</div>;
  }

  if (!student) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p style={{ color: 'var(--accent-rose)', fontSize: '1.1rem' }}>Student not found.</p>
        <button className="btn btn-secondary" onClick={() => navigate('/students')} style={{ marginTop: 16 }}>
          Back to Students
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Top Back Navigation */}
      <button
        className="btn btn-secondary btn-sm"
        onClick={() => navigate('/students')}
        style={{ marginBottom: 20, gap: 6 }}
      >
        <ArrowLeft size={14} />
        <span>Back to Students</span>
      </button>

      {/* Student Profile Card */}
      <div className="glass-panel" style={{ marginBottom: 28, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-cyan))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: '1.8rem',
            fontWeight: 700
          }}>
            {student.name.charAt(0)}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>{student.name}</h2>
              <span className="font-mono" style={{
                background: 'var(--bg-surface-elevated)',
                padding: '3px 8px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.8rem',
                color: 'var(--accent-cyan)'
              }}>
                {student.student_code}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8, fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Building size={14} />
                <span>{student.department || 'General'}</span>
              </span>
              <span>&bull;</span>
              <span>{student.year} {student.section}</span>
              {student.email && (
                <>
                  <span>&bull;</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Mail size={14} />
                    <span>{student.email}</span>
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Biometric Status Pill */}
        <div style={{
          background: student.has_face ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
          border: `1px solid ${student.has_face ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          padding: '8px 16px',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          gap: 10
        }}>
          <ShieldCheck size={20} color={student.has_face ? 'var(--accent-emerald)' : 'var(--accent-rose)'} />
          <div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Face Recognition</div>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: student.has_face ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
              {student.has_face ? 'Biometrics Registered' : 'Pending Enrollment'}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="stats-grid">
        <StatCard
          label="Attendance Rate"
          value={`${student.attendance_rate}%`}
          icon={CheckCircle2}
          subtext={`${student.sessions_attended} of ${student.total_sessions} sessions`}
          color="var(--accent-emerald)"
        />
        <StatCard
          label="Sessions Attended"
          value={student.sessions_attended}
          icon={Calendar}
          subtext="Total confirmed presences"
          color="var(--accent-primary)"
        />
        <StatCard
          label="Avg Presence Time"
          value={`${Math.round(student.avg_presence_duration_seconds / 60)} min`}
          icon={Clock}
          subtext={`${student.avg_presence_duration_seconds} seconds`}
          color="var(--accent-cyan)"
        />
        <StatCard
          label="Observable Engagement"
          value={`${Math.round(student.avg_engagement_score * 100)}%`}
          icon={Activity}
          subtext="CV orientation estimate"
          color="var(--accent-purple)"
        />
      </div>

      {/* Session Attendance Logs */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <span>Session Attendance History</span>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Session ID</th>
                <th>First Seen</th>
                <th>Last Seen</th>
                <th>Duration</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {attendanceLogs.map((log) => (
                <tr key={log.id}>
                  <td className="font-mono">#{log.session_id}</td>
                  <td>{log.first_seen ? new Date(log.first_seen).toLocaleTimeString() : '—'}</td>
                  <td>{log.last_seen ? new Date(log.last_seen).toLocaleTimeString() : '—'}</td>
                  <td>{Math.round(log.duration_seconds / 60)} mins ({log.duration_seconds}s)</td>
                  <td>{Math.round(log.confidence * 100)}%</td>
                  <td><Badge status={log.status} /></td>
                </tr>
              ))}
              {attendanceLogs.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: 28, color: 'var(--text-muted)' }}>
                    No session logs found for this student.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
