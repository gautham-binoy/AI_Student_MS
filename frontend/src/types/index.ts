export interface Student {
  id: number;
  student_code: string;
  name: string;
  email?: string;
  department?: string;
  year?: string;
  section?: string;
  has_face: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface StudentDetail extends Student {
  attendance_rate: number;
  sessions_attended: number;
  total_sessions: number;
  avg_presence_duration_seconds: number;
  avg_engagement_score: number;
}

export interface Session {
  id: number;
  name: string;
  subject?: string;
  class_name?: string;
  date: string;
  start_time?: string;
  end_time?: string;
  status: 'scheduled' | 'active' | 'completed';
  created_at?: string;
  present_count: number;
  total_students: number;
  avg_engagement: number;
}

export interface AttendanceRecord {
  id: number;
  session_id: number;
  student_id: number;
  student_code: string;
  student_name: string;
  department?: string;
  first_seen?: string;
  last_seen?: string;
  duration_seconds: number;
  status: 'Present' | 'Absent';
  confidence: number;
}

export interface AttendanceSummary {
  total_enrolled: number;
  present_count: number;
  absent_count: number;
  attendance_rate: number;
  records: AttendanceRecord[];
}

export interface AnalyticsOverview {
  total_students: number;
  total_sessions: number;
  active_sessions: number;
  present_today: number;
  absent_today: number;
  avg_attendance_rate: number;
  avg_engagement_score: number;
  attendance_trends: Array<{
    session_id: number;
    session_name: string;
    date: string;
    rate: number;
    present: number;
  }>;
  engagement_distribution: Array<{
    category: string;
    count: number;
  }>;
}

export interface AnalyticsSession {
  session: Session;
  present_count: number;
  absent_count: number;
  attendance_rate: number;
  avg_engagement: number;
  attendance_list: AttendanceRecord[];
  engagement_timeline: Array<{
    time: string;
    engagement: number;
    orientation: number;
    track_id?: number;
  }>;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface LiveDetection {
  track_id: number;
  student_id?: number | null;
  student_name: string;
  confidence: number;
  bbox: BoundingBox;
  orientation_score: number;
  engagement_score: number;
  confirmed_present: boolean;
}

export interface LiveFrameUpdate {
  type: string;
  session_id?: number;
  timestamp: string;
  fps: number;
  metrics: {
    det_ms: number;
    track_ms: number;
    rec_ms: number;
    total_ms: number;
    recognitions_run: number;
  };
  counts: {
    active_tracks: number;
    recognized: number;
    unknown: number;
    present: number;
    total_students: number;
  };
  avg_engagement: number;
  detections: LiveDetection[];
  annotated_image?: string | null;
}
