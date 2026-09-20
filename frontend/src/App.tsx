import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardPage } from './pages/DashboardPage';
import { LiveClassroomPage } from './pages/LiveClassroomPage';
import { StudentsPage } from './pages/StudentsPage';
import { StudentDetailPage } from './pages/StudentDetailPage';
import { SessionsPage } from './pages/SessionsPage';
import { AttendancePage } from './pages/AttendancePage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';

const AppLayout: React.FC = () => {
  const location = useLocation();

  const getPageTitle = (path: string): string => {
    if (path.startsWith('/dashboard')) return 'Dashboard Overview';
    if (path.startsWith('/live')) return 'AI Classroom Live Monitor';
    if (path.startsWith('/students/')) return 'Student Profile';
    if (path.startsWith('/students')) return 'Student Management';
    if (path.startsWith('/sessions')) return 'Classroom Sessions';
    if (path.startsWith('/attendance')) return 'Attendance Logs';
    if (path.startsWith('/analytics')) return 'Analytics & Insights';
    if (path.startsWith('/settings')) return 'System Settings & Privacy';
    return 'VisionClass AI';
  };

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-wrapper">
        <Header title={getPageTitle(location.pathname)} />
        <main className="content-container">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/live" element={<LiveClassroomPage />} />
            <Route path="/students" element={<StudentsPage />} />
            <Route path="/students/:id" element={<StudentDetailPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/attendance" element={<AttendancePage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
};

export default App;
