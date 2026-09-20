import React, { useEffect, useState } from 'react';
import { Clock, Radio, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';
import { Session } from '../types';

interface HeaderProps {
  title: string;
}

export const Header: React.FC<HeaderProps> = ({ title }) => {
  const [timeStr, setTimeStr] = useState<string>('');
  const [activeSession, setActiveSession] = useState<Session | null>(null);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchActive = async () => {
      try {
        const sessions = await api.getSessions();
        const active = sessions.find((s) => s.status === 'active');
        setActiveSession(active || null);
      } catch (err) {
        // backend might be starting
      }
    };
    fetchActive();
    const sInterval = setInterval(fetchActive, 10000);
    return () => clearInterval(sInterval);
  }, []);

  return (
    <header className="top-header">
      <div className="page-title">{title}</div>

      <div className="header-actions">
        {activeSession && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            background: 'rgba(6, 182, 212, 0.12)',
            border: '1px solid rgba(6, 182, 212, 0.3)',
            padding: '6px 14px',
            borderRadius: '999px',
            fontSize: '0.8rem',
            color: 'var(--accent-cyan)',
            fontWeight: 600
          }}>
            <Radio size={14} className="animate-pulse" />
            <span>Active: {activeSession.name}</span>
          </div>
        )}

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
          background: 'var(--bg-surface-elevated)',
          padding: '6px 14px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--border-subtle)'
        }}>
          <Clock size={15} color="var(--accent-primary)" />
          <span className="font-mono">{timeStr}</span>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: '0.82rem',
          color: 'var(--accent-emerald)',
          background: 'rgba(16, 185, 129, 0.1)',
          padding: '6px 12px',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(16, 185, 129, 0.2)'
        }}>
          <ShieldCheck size={16} />
          <span>Local Engine</span>
        </div>
      </div>
    </header>
  );
};
