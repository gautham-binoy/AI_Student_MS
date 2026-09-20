from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -------------------------------------------------------------
# Student Schemas
# -------------------------------------------------------------
class StudentBase(BaseModel):
    student_code: str = Field(..., description="Unique student identifier, e.g., STU-2024-001")
    name: str = Field(..., min_length=1, max_length=128)
    email: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    section: Optional[str] = None


class StudentResponse(StudentBase):
    id: int
    has_face: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudentDetailResponse(StudentResponse):
    attendance_rate: float = 0.0
    sessions_attended: int = 0
    total_sessions: int = 0
    avg_presence_duration_seconds: float = 0.0
    avg_engagement_score: float = 0.0


# -------------------------------------------------------------
# Face Registration Schema
# -------------------------------------------------------------
class FaceRegistrationResponse(BaseModel):
    success: bool
    message: str
    student_id: int
    face_detected: bool
    confidence: float = 0.0


# -------------------------------------------------------------
# Session Schemas
# -------------------------------------------------------------
class SessionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Session name or course title")
    subject: Optional[str] = None
    class_name: Optional[str] = None
    date: str = Field(..., description="Date formatted as YYYY-MM-DD")
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    class_name: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None


class SessionResponse(SessionBase):
    id: int
    status: str
    created_at: Optional[datetime] = None
    present_count: int = 0
    total_students: int = 0
    avg_engagement: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# Attendance Schemas
# -------------------------------------------------------------
class AttendanceRecord(BaseModel):
    id: int
    session_id: int
    student_id: int
    student_code: str
    student_name: str
    department: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: str = "Absent"
    confidence: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AttendanceSummary(BaseModel):
    total_enrolled: int
    present_count: int
    absent_count: int
    attendance_rate: float
    records: List[AttendanceRecord]


# -------------------------------------------------------------
# Engagement Schemas
# -------------------------------------------------------------
class EngagementPoint(BaseModel):
    timestamp: str
    engagement_score: float
    orientation_score: float
    face_visible: bool


class StudentEngagementSummary(BaseModel):
    student_id: int
    student_name: str
    student_code: str
    avg_engagement: float
    avg_orientation: float
    presence_percentage: float


# -------------------------------------------------------------
# Analytics Schemas
# -------------------------------------------------------------
class AnalyticsOverviewResponse(BaseModel):
    total_students: int
    total_sessions: int
    active_sessions: int
    present_today: int
    absent_today: int
    avg_attendance_rate: float
    avg_engagement_score: float
    attendance_trends: List[dict]  # [{"date": "2026-09-18", "rate": 88.5}, ...]
    engagement_distribution: List[dict]  # [{"category": "High", "count": 25}, ...]


class AnalyticsSessionResponse(BaseModel):
    session: SessionResponse
    present_count: int
    absent_count: int
    attendance_rate: float
    avg_engagement: float
    attendance_list: List[AttendanceRecord]
    engagement_timeline: List[dict]  # [{"time": "10:05", "engagement": 0.82}, ...]


# -------------------------------------------------------------
# Live Stream & Inference Schemas
# -------------------------------------------------------------
class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class LiveDetection(BaseModel):
    track_id: Optional[int] = None
    student_id: Optional[int] = None
    student_name: str = "Unknown"
    confidence: float
    bbox: BoundingBox
    orientation_score: float = 0.0
    engagement_score: float = 0.0
    confirmed_present: bool = False


class LiveFrameUpdate(BaseModel):
    type: str = "frame_update"
    session_id: Optional[int] = None
    timestamp: str
    fps: float = 0.0
    present_count: int = 0
    absent_count: int = 0
    total_students: int = 0
    recognized_count: int = 0
    unknown_count: int = 0
    avg_engagement: float = 0.0
    detections: List[LiveDetection] = []
