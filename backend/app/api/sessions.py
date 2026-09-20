from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.database import get_db
from app.database.models import Session as DbSession, Attendance, Engagement, Student
from app.database.schemas import SessionCreate, SessionUpdate, SessionResponse
from app.services.attendance import AttendanceService
from app.services.video_processor import VideoProcessor

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def format_session_response(s: DbSession, db: Session) -> SessionResponse:
    present_cnt = (
        db.query(Attendance)
        .filter(Attendance.session_id == s.id, Attendance.status == "Present")
        .count()
    )
    total_stu = db.query(Student).count()
    avg_eng = (
        db.query(func.avg(Engagement.engagement_score))
        .filter(Engagement.session_id == s.id)
        .scalar()
    ) or 0.0

    resp = SessionResponse.model_validate(s)
    resp.present_count = present_cnt
    resp.total_students = total_stu
    resp.avg_engagement = round(float(avg_eng), 2)
    return resp


@router.get("", response_model=List[SessionResponse])
def get_sessions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all classroom sessions with attendance and engagement metrics."""
    sessions = db.query(DbSession).order_by(DbSession.id.desc()).offset(skip).limit(limit).all()
    return [format_session_response(s, db) for s in sessions]


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(session_in: SessionCreate, db: Session = Depends(get_db)):
    """Create a new classroom session."""
    session = DbSession(
        name=session_in.name,
        subject=session_in.subject,
        class_name=session_in.class_name,
        date=session_in.date,
        start_time=session_in.start_time,
        end_time=session_in.end_time,
        status="scheduled"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return format_session_response(session, db)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Retrieve details of a specific classroom session."""
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return format_session_response(session, db)


@router.post("/{session_id}/start", response_model=SessionResponse)
def start_session(session_id: int, db: Session = Depends(get_db)):
    """Start an active live classroom session and prepare roster tracking."""
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    session.status = "active"
    if not session.start_time:
        session.start_time = datetime.now().strftime("%H:%M:%S")

    # Initialize roster: ensure all registered students have an entry (defaulting to Absent)
    att_service = AttendanceService()
    att_service.initialize_session_roster(db, session_id)
    db.commit()
    db.refresh(session)

    # Reset video processor tracker state for clean tracking session
    VideoProcessor.get_instance().reset_tracker()
    return format_session_response(session, db)


@router.post("/{session_id}/stop", response_model=SessionResponse)
def stop_session(session_id: int, db: Session = Depends(get_db)):
    """Stop an active session, mark completed, and record end time."""
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    session.status = "completed"
    session.end_time = datetime.now().strftime("%H:%M:%S")
    db.commit()
    db.refresh(session)
    return format_session_response(session, db)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a session and its associated logs."""
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    db.delete(session)
    db.commit()
    return None
