import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  UserCheck,
  UserX,
  Percent,
  Activity,
  Radio,
  ArrowRight,
  Play,
  Calendar,
  Sparkles
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from 'recharts';
import { api } from '../services/api';
import { AnalyticsOverview, Session } from '../types';
import { StatCard } from '../components/StatCard';
import { Badge } from '../components/Badge';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [ovData, sessData] = await Promise.all([
          api.getAnalyticsOverview(),
          api.getSessions()
        ]);
        setOverview(ovData);
        setSessions(sessData);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const activeSession = sessions.find((s) => s.status === 'active');

  const COLORS = ['#10b981', '#f59e0b', '#f43f5e'];

  return (
    <div>
      {/* Active Session Banner if one is live */}
      {activeSession && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(6, 182, 212, 0.2))',
          border: '1px solid var(--border-accent)',
          borderRadius: 'var(--radius-md)',
          padding: '20px 24px',
          marginBottom: '28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{
              width: 44,
              height: 44,
              borderRadius: 'var(--radius-md)',
              background: 'rgba(6, 182, 212, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-cyan)'
            }}>
              <Radio size={22} className="animate-pulse" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{activeSession.name}</h2>
                <Badge status="active" />
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: 4 }}>
                {activeSession.subject || 'Lecture'} &bull; {activeSession.class_name || 'Classroom'} &bull; Started at {activeSession.start_time || 'Just now'}
              </p>
            </div>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/live')}
            style={{ gap: 8 }}
          >
            <Play size={16} />
            <span>Enter Live Classroom</span>
          </button>
        </div>
      )}

      {/* Top Stat Cards Grid */}
      <div className="stats-grid">
        <StatCard
          label="Total Students"
          value={overview?.total_students ?? 0}
          icon={Users}
          subtext="Enrolled in system"
          color="var(--accent-primary)"
        />
        <StatCard
          label="Present Today"
          value={overview?.present_today ?? 0}
          icon={UserCheck}
          subtext="Verified via CV pipeline"
          color="var(--accent-emerald)"
          trend="+12%"
        />
        <StatCard
          label="Absent Today"
          value={overview?.absent_today ?? 0}
          icon={UserX}
          subtext="Not detected in sessions"
          color="var(--accent-rose)"
        />
        <StatCard
          label="Average Attendance"
          value={`${overview?.avg_attendance_rate ?? 0}%`}
          icon={Percent}
          subtext="Across all sessions"
          color="var(--accent-cyan)"
        />
        <StatCard
          label="Engagement Estimate"
          value={`${Math.round((overview?.avg_engagement_score ?? 0) * 100)}%`}
          icon={Activity}
          subtext="Observable CV signal"
          color="var(--accent-purple)"
        />
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, marginBottom: 28 }}>
        {/* Attendance Trends */}
        <div className="glass-panel">
          <div className="panel-header">
            <div className="panel-title">
              <Calendar size={18} color="var(--accent-primary)" />
              <span>Attendance Rate Trends</span>
            </div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Recent Sessions
            </span>
          </div>
          <div style={{ height: 260 }}>
            {overview?.attendance_trends && overview.attendance_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={overview.attendance_trends}>
                  <defs>
                    <linearGradient id="colorRate" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="session_name"
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    tickFormatter={(val) => val.slice(0, 10) + '...'}
                  />
                  <YAxis
                    domain={[0, 100]}
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#182030',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderRadius: 8,
                      color: '#fff'
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="rate"
                    stroke="#6366f1"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorRate)"
                    name="Attendance %"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                No session trend data available yet
              </div>
            )}
          </div>
        </div>

        {/* Observable Engagement Breakdown */}
        <div className="glass-panel">
          <div className="panel-header">
            <div className="panel-title">
              <Sparkles size={18} color="var(--accent-cyan)" />
              <span>Observable Engagement</span>
            </div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              CV Estimate
            </span>
          </div>
          <div style={{ height: 260 }}>
            {overview?.engagement_distribution ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview.engagement_distribution} layout="vertical">
                  <XAxis type="number" stroke="#475569" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis
                    dataKey="category"
                    type="category"
                    width={100}
                    stroke="#475569"
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#182030',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderRadius: 8,
                      color: '#fff'
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {overview.engagement_distribution.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                No engagement distribution data
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Sessions Table */}
      <div className="glass-panel">
        <div className="panel-header">
          <div className="panel-title">
            <span>Recent Classroom Sessions</span>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate('/sessions')}
          >
            <span>View All Sessions</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Session Name</th>
                <th>Subject</th>
                <th>Class</th>
                <th>Date</th>
                <th>Status</th>
                <th>Attendance</th>
                <th>Engagement</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.slice(0, 5).map((s) => (
                <tr key={s.id}>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td>{s.subject || '—'}</td>
                  <td>{s.class_name || '—'}</td>
                  <td className="font-mono">{s.date}</td>
                  <td><Badge status={s.status} /></td>
                  <td>
                    <span style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>
                      {s.present_count}
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}> / {s.total_students}</span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600 }}>
                      {Math.round(s.avg_engagement * 100)}%
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => navigate(`/analytics?session_id=${s.id}`)}
                    >
                      Details
                    </button>
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: 28, color: 'var(--text-muted)' }}>
                    No sessions found. Create a session or run demo data script.
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
