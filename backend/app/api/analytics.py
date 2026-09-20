from datetime import datetime, date
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.database import get_db
from app.database.models import Student, Session as DbSession, Attendance, Engagement
from app.database.schemas import AnalyticsOverviewResponse, AnalyticsSessionResponse, AttendanceRecord
from app.api.sessions import format_session_response
from app.api.attendance import format_record

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(db: Session = Depends(get_db)):
    """
    Get aggregated system analytics: total students, sessions, attendance rate,
    observable engagement estimate distribution, and trends over time.
    """
    total_students = db.query(Student).count()
    total_sessions = db.query(DbSession).count()
    active_sessions = db.query(DbSession).filter(DbSession.status == "active").count()

    today_str = date.today().isoformat()
    today_sessions = db.query(DbSession).filter(DbSession.date == today_str).all()
    today_session_ids = [s.id for s in today_sessions]

    if today_session_ids:
        present_today = (
            db.query(Attendance)
            .filter(Attendance.session_id.in_(today_session_ids), Attendance.status == "Present")
            .count()
        )
        total_slots = len(today_session_ids) * total_students
        absent_today = max(0, total_slots - present_today)
    else:
        present_today = 0
        absent_today = 0

    # Overall attendance rate across all sessions
    total_attendance_records = db.query(Attendance).count()
    present_total_records = db.query(Attendance).filter(Attendance.status == "Present").count()
    avg_attendance_rate = (
        (present_total_records / total_attendance_records * 100.0)
        if total_attendance_records > 0 else 0.0
    )

    # Average engagement score across all logged records
    avg_eng = db.query(func.avg(Engagement.engagement_score)).scalar() or 0.0

    # Attendance trends per session
    recent_sessions = db.query(DbSession).order_by(DbSession.id.asc()).limit(10).all()
    trends = []
    for s in recent_sessions:
        p_cnt = (
            db.query(Attendance)
            .filter(Attendance.session_id == s.id, Attendance.status == "Present")
            .count()
        )
        s_rate = (p_cnt / total_students * 100.0) if total_students > 0 else 0.0
        trends.append({
            "session_id": s.id,
            "session_name": s.name,
            "date": s.date,
            "rate": round(s_rate, 1),
            "present": p_cnt
        })

    # Observable engagement distribution
    eng_samples = db.query(Engagement.engagement_score).all()
    scores = [s[0] for s in eng_samples]
    high_cnt = sum(1 for sc in scores if sc >= 0.70)
    mod_cnt = sum(1 for sc in scores if 0.40 <= sc < 0.70)
    low_cnt = sum(1 for sc in scores if sc < 0.40)

    distribution = [
        {"category": "High (>= 0.70)", "count": high_cnt},
        {"category": "Moderate (0.40 - 0.70)", "count": mod_cnt},
        {"category": "Low (< 0.40)", "count": low_cnt}
    ]

    return AnalyticsOverviewResponse(
        total_students=total_students,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        present_today=present_today,
        absent_today=absent_today,
        avg_attendance_rate=round(avg_attendance_rate, 1),
        avg_engagement_score=round(float(avg_eng), 2),
        attendance_trends=trends,
        engagement_distribution=distribution
    )


@router.get("/session/{session_id}", response_model=AnalyticsSessionResponse)
def get_session_analytics(session_id: int, db: Session = Depends(get_db)):
    """
    Get in-depth analytics for a single classroom session: student attendance roster,
    presence counts, and chronological engagement timeline.
    """
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    total_enrolled = db.query(Student).count()
    records = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    formatted_records = [format_record(r) for r in records]

    present_cnt = sum(1 for r in formatted_records if r.status == "Present")
    absent_cnt = max(0, total_enrolled - present_cnt)
    rate = (present_cnt / total_enrolled * 100.0) if total_enrolled > 0 else 0.0

    avg_eng = (
        db.query(func.avg(Engagement.engagement_score))
        .filter(Engagement.session_id == session_id)
        .scalar()
    ) or 0.0

    # Engagement timeline
    engagements = (
        db.query(Engagement)
        .filter(Engagement.session_id == session_id)
        .order_by(Engagement.timestamp.asc())
        .limit(100)
        .all()
    )

    timeline = []
    for e in engagements:
        timeline.append({
            "time": e.timestamp.strftime("%H:%M:%S") if e.timestamp else "00:00:00",
            "engagement": round(e.engagement_score, 2),
            "orientation": round(e.orientation_score, 2),
            "track_id": e.tracking_id
        })

    return AnalyticsSessionResponse(
        session=format_session_response(session, db),
        present_count=present_cnt,
        absent_count=absent_cnt,
        attendance_rate=round(rate, 1),
        avg_engagement=round(float(avg_eng), 2),
        attendance_list=formatted_records,
        engagement_timeline=timeline
    )
