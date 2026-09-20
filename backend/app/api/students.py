import json
from typing import List, Optional
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.database import get_db
from app.database.models import Student, Attendance, Session as DbSession, Engagement
from app.database.schemas import (
    StudentCreate,
    StudentUpdate,
    StudentResponse,
    StudentDetailResponse,
    FaceRegistrationResponse
)
from app.services.face_detector import FaceDetector
from app.services.face_recognition import FaceRecognizer
from app.services.video_processor import VideoProcessor
from app.core.logging import logger

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("", response_model=List[StudentResponse])
def get_students(
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve all students with search and department filtering."""
    query = db.query(Student)
    if department:
        query = query.filter(Student.department == department)
    students = query.offset(skip).limit(limit).all()
    
    result = []
    for s in students:
        resp = StudentResponse.model_validate(s)
        resp.has_face = bool(s.face_embedding)
        result.append(resp)
    return result


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student_in: StudentCreate, db: Session = Depends(get_db)):
    """Create a new student record."""
    existing = db.query(Student).filter(Student.student_code == student_in.student_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with code '{student_in.student_code}' already exists."
        )

    student = Student(
        student_code=student_in.student_code,
        name=student_in.name,
        email=student_in.email,
        department=student_in.department,
        year=student_in.year,
        section=student_in.section
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    resp = StudentResponse.model_validate(student)
    resp.has_face = False
    return resp


@router.get("/{student_id}", response_model=StudentDetailResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    """Retrieve a student profile with aggregated attendance and engagement metrics."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    total_sessions = db.query(DbSession).count()
    attended_records = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id, Attendance.status == "Present")
        .all()
    )
    sessions_attended = len(attended_records)
    attendance_rate = (sessions_attended / total_sessions * 100.0) if total_sessions > 0 else 0.0

    avg_presence = (
        sum(r.duration_seconds for r in attended_records) / sessions_attended
        if sessions_attended > 0 else 0.0
    )

    avg_engagement_val = (
        db.query(func.avg(Engagement.engagement_score))
        .filter(Engagement.student_id == student_id)
        .scalar()
    ) or 0.0

    resp = StudentDetailResponse.model_validate(student)
    resp.has_face = bool(student.face_embedding)
    resp.total_sessions = total_sessions
    resp.sessions_attended = sessions_attended
    resp.attendance_rate = round(attendance_rate, 1)
    resp.avg_presence_duration_seconds = round(avg_presence, 1)
    resp.avg_engagement_score = round(float(avg_engagement_val), 2)
    return resp


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(student_id: int, update_in: StudentUpdate, db: Session = Depends(get_db)):
    """Update student metadata."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    update_data = update_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    db.commit()
    db.refresh(student)

    resp = StudentResponse.model_validate(student)
    resp.has_face = bool(student.face_embedding)
    return resp


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    """Delete a student and remove associated biometric embeddings."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    db.delete(student)
    db.commit()
    # Invalidate embedding cache in video processor
    VideoProcessor.get_instance().reload_student_cache(db)
    return None


@router.post("/{student_id}/face", response_model=FaceRegistrationResponse)
async def register_student_face(
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Register a student face embedding from an uploaded photo.
    Validates:
    - Image format & file content
    - Exactly 1 face detected (rejects 0 faces or multiple faces)
    Generates and securely stores the normalized 512-d embedding.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    # Validate MIME type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a valid image file (JPEG, PNG, WebP)."
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size exceeds 10MB limit."
        )

    # Decode image using OpenCV
    np_arr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decode image data. The file may be corrupt."
        )

    # Detect faces
    detector = FaceDetector.get_instance()
    detections = detector.detect(image)

    if len(detections) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No face detected in the image. Please ensure the student's face is clearly visible, well-lit, and facing the camera."
        )

    if len(detections) > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Multiple faces detected ({len(detections)} found). Registration requires a single portrait of the student."
        )

    face = detections[0]
    recognizer = FaceRecognizer.get_instance()
    embedding = recognizer.generate_embedding(face.crop)

    if embedding is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate face embedding vector."
        )

    # Store normalized embedding as JSON list of floats
    student.face_embedding = json.dumps(embedding.tolist())
    db.commit()

    # Refresh VideoProcessor in-memory cache
    VideoProcessor.get_instance().reload_student_cache(db)

    logger.info(f"Successfully registered face embedding for student {student.name} ({student.student_code}).")

    return FaceRegistrationResponse(
        success=True,
        message=f"Face registered successfully for {student.name}.",
        student_id=student.id,
        face_detected=True,
        confidence=round(float(face.confidence), 3)
    )
