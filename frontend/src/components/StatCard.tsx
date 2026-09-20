import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  subtext?: string;
  color?: string;
  trend?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon: Icon,
  subtext,
  color = 'var(--accent-primary)',
  trend
}) => {
  return (
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-label">{label}</span>
        <div
          className="stat-icon-wrapper"
          style={{ background: `rgba(99, 102, 241, 0.12)`, color }}
        >
          <Icon size={18} color={color} />
        </div>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-footer">
        {trend && (
          <span style={{ color: 'var(--accent-emerald)', fontWeight: 600, marginRight: 4 }}>
            {trend}
          </span>
        )}
        <span>{subtext}</span>
      </div>
    </div>
  );
};
