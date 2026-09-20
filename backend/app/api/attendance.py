import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Attendance, Student, Session as DbSession
from app.database.schemas import AttendanceRecord, AttendanceSummary

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def format_record(att: Attendance) -> AttendanceRecord:
    stu = att.student
    return AttendanceRecord(
        id=att.id,
        session_id=att.session_id,
        student_id=att.student_id,
        student_code=stu.student_code if stu else "N/A",
        student_name=stu.name if stu else "Unknown",
        department=stu.department if stu else None,
        first_seen=att.first_seen,
        last_seen=att.last_seen,
        duration_seconds=round(att.duration_seconds, 1),
        status=att.status,
        confidence=round(att.confidence, 2)
    )


@router.get("", response_model=List[AttendanceRecord])
def get_all_attendance(
    session_id: Optional[int] = None,
    student_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db)
):
    """Retrieve attendance logs with optional session, student, or status filters."""
    query = db.query(Attendance)
    if session_id:
        query = query.filter(Attendance.session_id == session_id)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)

    records = query.order_by(Attendance.id.desc()).all()
    return [format_record(r) for r in records]


@router.get("/export/csv")
def export_attendance_csv(session_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Export attendance records to a downloadable CSV spreadsheet."""
    query = db.query(Attendance)
    if session_id:
        query = query.filter(Attendance.session_id == session_id)
    records = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record ID", "Session ID", "Session Name", "Date",
        "Student Code", "Student Name", "Department",
        "Status", "First Seen", "Last Seen", "Presence Duration (s)", "Confidence"
    ])

    for r in records:
        stu = r.student
        sess = r.session
        writer.writerow([
            r.id,
            r.session_id,
            sess.name if sess else "N/A",
            sess.date if sess else "N/A",
            stu.student_code if stu else "N/A",
            stu.name if stu else "Unknown",
            stu.department if stu else "N/A",
            r.status,
            r.first_seen.isoformat() if r.first_seen else "N/A",
            r.last_seen.isoformat() if r.last_seen else "N/A",
            round(r.duration_seconds, 1),
            round(r.confidence, 2)
        ])

    csv_data = output.getvalue()
    filename = f"attendance_session_{session_id}.csv" if session_id else "all_attendance.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{session_id}", response_model=AttendanceSummary)
def get_session_attendance(session_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed attendance summary for a specific classroom session."""
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    records = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    formatted = [format_record(r) for r in records]

    total_enrolled = db.query(Student).count()
    present_cnt = sum(1 for r in formatted if r.status == "Present")
    absent_cnt = max(0, total_enrolled - present_cnt)
    rate = (present_cnt / total_enrolled * 100.0) if total_enrolled > 0 else 0.0

    return AttendanceSummary(
        total_enrolled=total_enrolled,
        present_count=present_cnt,
        absent_count=absent_cnt,
        attendance_rate=round(rate, 1),
        records=formatted
    )
