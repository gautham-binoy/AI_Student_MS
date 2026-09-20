import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Video,
  ClipboardCheck,
  GraduationCap,
  Calendar,
  BarChart3,
  Settings,
  Brain,
  Sparkles
} from 'lucide-react';

interface SidebarProps {
  systemStatus?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ systemStatus = 'Operational' }) => {
  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/live', label: 'Live Classroom', icon: Video, badge: 'Live AI' },
    { path: '/attendance', label: 'Attendance', icon: ClipboardCheck },
    { path: '/students', label: 'Students', icon: GraduationCap },
    { path: '/sessions', label: 'Sessions', icon: Calendar },
    { path: '/analytics', label: 'Analytics', icon: BarChart3 },
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-icon">
          <Brain size={22} />
        </div>
        <div className="brand-text">
          <h1>VisionClass AI</h1>
          <span>Attendance & Eng.</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <Icon />
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.badge && (
                <span style={{
                  background: 'rgba(6, 182, 212, 0.2)',
                  color: 'var(--accent-cyan)',
                  fontSize: '0.68rem',
                  padding: '2px 6px',
                  borderRadius: '999px',
                  fontWeight: 600
                }}>
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="system-pill">
          <div className="status-dot" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '0.78rem', color: '#fff', fontWeight: 600 }}>
              AI Pipeline
            </span>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              YOLO + FaceNet + ByteTrack
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
