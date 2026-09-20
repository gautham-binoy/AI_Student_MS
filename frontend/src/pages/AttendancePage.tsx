import React, { useEffect, useState } from 'react';
import {
  ClipboardCheck,
  Download,
  Filter,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Calendar
} from 'lucide-react';
import { api } from '../services/api';
import { AttendanceRecord, Session } from '../types';
import { Badge } from '../components/Badge';

export const AttendancePage: React.FC = () => {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | ''>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  const fetchFiltersAndData = async () => {
    try {
      setLoading(true);
      const [sessList, attList] = await Promise.all([
        api.getSessions(),
        api.getAttendance(selectedSessionId ? Number(selectedSessionId) : undefined, statusFilter || undefined)
      ]);
      setSessions(sessList);
      setRecords(attList);
    } catch (err) {
      console.error('Failed to load attendance logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiltersAndData();
  }, [selectedSessionId, statusFilter]);

  const filteredRecords = records.filter((r) => {
    return (
      r.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.student_code.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  const presentCount = filteredRecords.filter((r) => r.status === 'Present').length;
  const absentCount = filteredRecords.filter((r) => r.status === 'Absent').length;

  return (
    <div>
      {/* Header and Export Action */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
        marginBottom: 24
      }}>
        {/* Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          {/* Search */}
          <div style={{ position: 'relative', width: 260 }}>
            <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              className="form-input"
              placeholder="Search student..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '100%', paddingLeft: 36 }}
            />
          </div>

          {/* Session Select */}
          <select
            className="form-select"
            value={selectedSessionId}
            onChange={(e) => setSelectedSessionId(e.target.value ? Number(e.target.value) : '')}
            style={{ minWidth: 200 }}
          >
            <option value="">All Sessions</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.date})
              </option>
            ))}
          </select>

          {/* Status Select */}
          <select
            className="form-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="Present">Present Only</option>
            <option value="Absent">Absent Only</option>
          </select>
        </div>

        {/* CSV Export Button */}
        <a
          href={api.getExportUrl(selectedSessionId ? Number(selectedSessionId) : undefined)}
          className="btn btn-secondary"
          download
          style={{ gap: 8 }}
        >
          <Download size={16} />
          <span>Export CSV</span>
        </a>
      </div>

      {/* Summary Chips */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <div style={{
          background: 'var(--bg-surface)',
          padding: '8px 16px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-subtle)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)'
        }}>
          Total Logs: <strong style={{ color: '#fff' }}>{filteredRecords.length}</strong>
        </div>
        <div style={{
          background: 'rgba(16, 185, 129, 0.1)',
          padding: '8px 16px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          fontSize: '0.82rem',
          color: 'var(--accent-emerald)',
          fontWeight: 600
        }}>
          Confirmed Present: {presentCount}
        </div>
        <div style={{
          background: 'rgba(244, 63, 94, 0.1)',
          padding: '8px 16px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(244, 63, 94, 0.25)',
          fontSize: '0.82rem',
          color: 'var(--accent-rose)',
          fontWeight: 600
        }}>
          Absent: {absentCount}
        </div>
      </div>

      {/* Attendance Table */}
      <div className="glass-panel" style={{ padding: 0 }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Student ID</th>
                <th>Department</th>
                <th>Session ID</th>
                <th>First Seen</th>
                <th>Last Seen</th>
                <th>Presence Duration</th>
                <th>CV Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.map((r) => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 600 }}>{r.student_name}</td>
                  <td className="font-mono" style={{ color: 'var(--accent-cyan)' }}>
                    {r.student_code}
                  </td>
                  <td>{r.department || '—'}</td>
                  <td className="font-mono">#{r.session_id}</td>
                  <td>
                    {r.first_seen ? (
                      <span className="font-mono" style={{ fontSize: '0.82rem' }}>
                        {new Date(r.first_seen).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    {r.last_seen ? (
                      <span className="font-mono" style={{ fontSize: '0.82rem' }}>
                        {new Date(r.last_seen).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    {r.duration_seconds > 0 ? (
                      <span>
                        <strong>{Math.round(r.duration_seconds / 60)} min</strong>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}> ({Math.round(r.duration_seconds)}s)</span>
                      </span>
                    ) : (
                      '0s'
                    )}
                  </td>
                  <td>
                    {r.confidence > 0 ? (
                      <span style={{ fontWeight: 600 }}>{Math.round(r.confidence * 100)}%</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td><Badge status={r.status} /></td>
                </tr>
              ))}
              {filteredRecords.length === 0 && !loading && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: 36, color: 'var(--text-muted)' }}>
                    No attendance records match the specified filters.
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
