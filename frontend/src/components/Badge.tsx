import React from 'react';

interface BadgeProps {
  status: 'Present' | 'Absent' | 'active' | 'scheduled' | 'completed' | string;
}

export const Badge: React.FC<BadgeProps> = ({ status }) => {
  const norm = status.toLowerCase();
  let className = 'badge badge-scheduled';

  if (norm === 'present') className = 'badge badge-present';
  else if (norm === 'absent') className = 'badge badge-absent';
  else if (norm === 'active') className = 'badge badge-active';
  else if (norm === 'completed') className = 'badge badge-completed';

  return <span className={className}>{status}</span>;
};
