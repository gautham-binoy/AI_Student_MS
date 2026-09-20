from datetime import datetime, timezone
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.logging import logger
from app.database.models import Attendance, Student, Session as DbSession
from app.services.tracker import Track


def utcnow():
    return datetime.utcnow()


class AttendanceService:
    def __init__(self, min_confirmation_seconds: Optional[float] = None):
        self.min_confirmation_seconds = min_confirmation_seconds or settings.MIN_CONFIRMATION_SECONDS

    def process_track_observation(
        self,
        db: Session,
        session_id: int,
        student_id: int,
        track: Track,
        confidence: float
    ) -> Optional[Attendance]:
        """
        Process a track observation for an identified student.
        Enforces temporal confirmation: requires continuous observation for at least MIN_CONFIRMATION_SECONDS.
        Enforces duplicate prevention: exactly one attendance row per (session_id, student_id).
        """
        if student_id is None or session_id is None:
            return None

        # Check temporal observation duration for confirmation
        track_observed_duration = track.last_seen_time - track.first_seen_time
        if track_observed_duration < self.min_confirmation_seconds:
            # Not confirmed yet (transient or false positive)
            return None

        now = utcnow()
        track.is_confirmed_present = True

        # Check existing attendance record
        record = (
            db.query(Attendance)
            .filter(Attendance.session_id == session_id, Attendance.student_id == student_id)
            .first()
        )

        try:
            if record:
                # Update existing record
                if record.first_seen is None:
                    record.first_seen = now

                # Duration increment: calculate time elapsed since previous last_seen
                if record.last_seen:
                    last_dt = record.last_seen
                    if hasattr(last_dt, "tzinfo") and last_dt.tzinfo is not None:
                        last_dt = last_dt.replace(tzinfo=None)
                    delta = (now - last_dt).total_seconds()
                    if 0 < delta < 10.0:  # smooth continuous stream increment
                        record.duration_seconds += delta
                    elif delta >= 10.0:
                        # Reappearance after absence
                        record.duration_seconds += 1.0
                else:
                    record.duration_seconds = track_observed_duration

                record.last_seen = now
                record.status = "Present"
                record.confidence = max(record.confidence, float(confidence))
                db.commit()
                db.refresh(record)
                return record
            else:
                # Create brand new attendance record
                new_record = Attendance(
                    session_id=session_id,
                    student_id=student_id,
                    first_seen=now,
                    last_seen=now,
                    duration_seconds=max(1.0, float(track_observed_duration)),
                    status="Present",
                    confidence=float(confidence)
                )
                db.add(new_record)
                db.commit()
                db.refresh(new_record)
                return new_record

        except IntegrityError:
            # Concurrent write race condition caught by UniqueConstraint
            db.rollback()
            existing = (
                db.query(Attendance)
                .filter(Attendance.session_id == session_id, Attendance.student_id == student_id)
                .first()
            )
            return existing
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating attendance for student {student_id}: {e}")
            return None

    def initialize_session_roster(self, db: Session, session_id: int):
        """
        Populate absent records for all registered students at session creation/start
        if not already present.
        """
        students = db.query(Student).all()
        for student in students:
            exists = (
                db.query(Attendance)
                .filter(Attendance.session_id == session_id, Attendance.student_id == student.id)
                .first()
            )
            if not exists:
                absent_record = Attendance(
                    session_id=session_id,
                    student_id=student.id,
                    status="Absent",
                    duration_seconds=0.0,
                    confidence=0.0
                )
                db.add(absent_record)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error initializing session roster: {e}")
