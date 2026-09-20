import axios from 'axios';
import {
  Student,
  StudentDetail,
  Session,
  AttendanceRecord,
  AttendanceSummary,
  AnalyticsOverview,
  AnalyticsSession
} from '../types';

const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

export const api = {
  // Health
  checkHealth: async () => {
    const res = await client.get('/health');
    return res.data;
  },

  // Students
  getStudents: async (department?: string): Promise<Student[]> => {
    const res = await client.get('/students', { params: { department } });
    return res.data;
  },
  getStudent: async (id: number): Promise<StudentDetail> => {
    const res = await client.get(`/students/${id}`);
    return res.data;
  },
  createStudent: async (data: Partial<Student>): Promise<Student> => {
    const res = await client.post('/students', data);
    return res.data;
  },
  updateStudent: async (id: number, data: Partial<Student>): Promise<Student> => {
    const res = await client.put(`/students/${id}`, data);
    return res.data;
  },
  deleteStudent: async (id: number): Promise<void> => {
    await client.delete(`/students/${id}`);
  },
  uploadStudentFace: async (id: number, file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post(`/students/${id}/face`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  // Sessions
  getSessions: async (): Promise<Session[]> => {
    const res = await client.get('/sessions');
    return res.data;
  },
  getSession: async (id: number): Promise<Session> => {
    const res = await client.get(`/sessions/${id}`);
    return res.data;
  },
  createSession: async (data: Partial<Session>): Promise<Session> => {
    const res = await client.post('/sessions', data);
    return res.data;
  },
  startSession: async (id: number): Promise<Session> => {
    const res = await client.post(`/sessions/${id}/start`);
    return res.data;
  },
  stopSession: async (id: number): Promise<Session> => {
    const res = await client.post(`/sessions/${id}/stop`);
    return res.data;
  },
  deleteSession: async (id: number): Promise<void> => {
    await client.delete(`/sessions/${id}`);
  },

  // Attendance
  getAttendance: async (sessionId?: number, status?: string): Promise<AttendanceRecord[]> => {
    const res = await client.get('/attendance', { params: { session_id: sessionId, status } });
    return res.data;
  },
  getSessionAttendance: async (sessionId: number): Promise<AttendanceSummary> => {
    const res = await client.get(`/attendance/${sessionId}`);
    return res.data;
  },
  getExportUrl: (sessionId?: number) => {
    return sessionId ? `/api/attendance/export/csv?session_id=${sessionId}` : '/api/attendance/export/csv';
  },

  // Analytics
  getAnalyticsOverview: async (): Promise<AnalyticsOverview> => {
    const res = await client.get('/analytics/overview');
    return res.data;
  },
  getSessionAnalytics: async (sessionId: number): Promise<AnalyticsSession> => {
    const res = await client.get(`/analytics/session/${sessionId}`);
    return res.data;
  },

  // Single Image Inference
  inferImage: async (file: File, sessionId?: number): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (sessionId) formData.append('session_id', String(sessionId));
    const res = await client.post('/inference/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  // Video Upload Inference
  inferVideo: async (file: File, sessionId: number, frameSkip: number = 2): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', String(sessionId));
    formData.append('frame_skip', String(frameSkip));
    const res = await client.post('/inference/video', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  }
};
