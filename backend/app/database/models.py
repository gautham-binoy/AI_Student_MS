from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True)
    department = Column(String(64), nullable=True)
    year = Column(String(32), nullable=True)
    section = Column(String(32), nullable=True)
    
    # Face embedding stored as JSON serialized array of float values
    # NOTE: Never exposed via public API schemas!
    face_embedding = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    engagements = relationship("Engagement", back_populates="student", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    subject = Column(String(128), nullable=True)
    class_name = Column(String(64), nullable=True)
    date = Column(String(32), nullable=False)  # ISO Date YYYY-MM-DD
    start_time = Column(String(32), nullable=True)
    end_time = Column(String(32), nullable=True)
    status = Column(String(32), default="scheduled", nullable=False)  # scheduled, active, completed
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    attendances = relationship("Attendance", back_populates="session", cascade="all, delete-orphan")
    engagements = relationship("Engagement", back_populates="session", cascade="all, delete-orphan")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, default=0.0, nullable=False)
    status = Column(String(32), default="Absent", nullable=False)  # Present, Absent
    confidence = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Prevent duplicate attendance entries for same student in same session
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_student_attendance"),
    )

    # Relationships
    session = relationship("Session", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")


class Engagement(Base):
    __tablename__ = "engagement"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    tracking_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)
    face_visible = Column(Boolean, default=True, nullable=False)
    orientation_score = Column(Float, default=0.0, nullable=False)
    engagement_score = Column(Float, default=0.0, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="engagements")
    student = relationship("Student", back_populates="engagements")
