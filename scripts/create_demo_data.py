"""
AI Attendance & Engagement Analyzer — Safe Synthetic Demo Data Generator
Creates sample student records, realistic attendance logs, engagement metrics,
and a synthetic demo classroom video for testing without real-world biometric data.
"""

import os
import sys
import json
import random
from datetime import datetime, timedelta, timezone
import numpy as np
import cv2

# Set backend in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database.database import engine, Base, SessionLocal
from app.database.models import Student, Session as DbSession, Attendance, Engagement
from app.services.face_recognition import FaceRecognizer


def utcnow():
    return datetime.now(timezone.utc)


SAMPLE_STUDENTS = [
    {
        "student_code": "STU-2026-001",
        "name": "Aarav Sharma",
        "email": "aarav.sharma@example.edu",
        "department": "Computer Science & Engineering",
        "year": "3rd Year",
        "section": "Section A"
    },
    {
        "student_code": "STU-2026-002",
        "name": "Diya Patel",
        "email": "diya.patel@example.edu",
        "department": "Computer Science & Engineering",
        "year": "3rd Year",
        "section": "Section A"
    },
    {
        "student_code": "STU-2026-003",
        "name": "Rohan Mehta",
        "email": "rohan.mehta@example.edu",
        "department": "Artificial Intelligence & Data Science",
        "year": "3rd Year",
        "section": "Section B"
    },
    {
        "student_code": "STU-2026-004",
        "name": "Ananya Iyer",
        "email": "ananya.iyer@example.edu",
        "department": "Computer Science & Engineering",
        "year": "3rd Year",
        "section": "Section A"
    },
    {
        "student_code": "STU-2026-005",
        "name": "Vikram Singh",
        "email": "vikram.singh@example.edu",
        "department": "Information Technology",
        "year": "2nd Year",
        "section": "Section A"
    },
    {
        "student_code": "STU-2026-006",
        "name": "Priya Nair",
        "email": "priya.nair@example.edu",
        "department": "Artificial Intelligence & Data Science",
        "year": "3rd Year",
        "section": "Section B"
    },
    {
        "student_code": "STU-2026-007",
        "name": "Rahul Verma",
        "email": "rahul.verma@example.edu",
        "department": "Computer Science & Engineering",
        "year": "3rd Year",
        "section": "Section A"
    },
    {
        "student_code": "STU-2026-008",
        "name": "Sneha Kapoor",
        "email": "sneha.kapoor@example.edu",
        "department": "Information Technology",
        "year": "2nd Year",
        "section": "Section B"
    }
]

SAMPLE_SESSIONS = [
    {
        "name": "CS301: Advanced Data Structures & Algorithms",
        "subject": "Data Structures",
        "class_name": "S5 CSE - A",
        "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        "start_time": "09:00:00",
        "end_time": "10:00:00",
        "status": "completed"
    },
    {
        "name": "AI402: Computer Vision & Neural Networks",
        "subject": "Computer Vision",
        "class_name": "S7 AI&DS",
        "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        "start_time": "11:15:00",
        "end_time": "12:15:00",
        "status": "completed"
    },
    {
        "name": "SE204: Software Architecture & Design Patterns",
        "subject": "Software Engineering",
        "class_name": "S5 CSE - A",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "start_time": "10:00:00",
        "end_time": None,
        "status": "active"
    }
]


def generate_synthetic_embedding(seed: int) -> list:
    """Generate deterministic synthetic 512-d unit vector."""
    np.random.seed(seed)
    vec = np.random.randn(512).astype(np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def generate_synthetic_portrait(name: str, color_seed: int, output_path: str):
    """Draw a clean stylized synthetic avatar for demo registration/testing."""
    img = np.full((320, 320, 3), 245, dtype=np.uint8)
    
    # Random gentle background color
    random.seed(color_seed)
    bg_color = (
        random.randint(220, 240),
        random.randint(220, 240),
        random.randint(230, 250)
    )
    img[:] = bg_color

    # Head / face oval
    face_color = (195, 220, 245)  # gentle skin tone
    cv2.ellipse(img, (160, 160), (75, 95), 0, 0, 360, face_color, -1)
    cv2.ellipse(img, (160, 160), (75, 95), 0, 0, 360, (140, 160, 180), 2)

    # Hair
    hair_colors = [(30, 30, 40), (20, 50, 90), (40, 30, 20)]
    h_col = random.choice(hair_colors)
    cv2.ellipse(img, (160, 100), (80, 50), 0, 180, 360, h_col, -1)

    # Eyes
    cv2.circle(img, (130, 145), 9, (255, 255, 255), -1)
    cv2.circle(img, (190, 145), 9, (255, 255, 255), -1)
    cv2.circle(img, (130, 145), 5, (30, 30, 30), -1)
    cv2.circle(img, (190, 145), 5, (30, 30, 30), -1)

    # Nose
    cv2.line(img, (160, 155), (160, 175), (140, 160, 180), 2)
    cv2.line(img, (160, 175), (153, 178), (140, 160, 180), 2)

    # Smile / Mouth
    cv2.ellipse(img, (160, 200), (25, 12), 0, 0, 180, (90, 90, 160), 2)

    # Label
    cv2.putText(img, name, (20, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 1, cv2.LINE_AA)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, img)


def create_synthetic_demo_video(output_path: str, duration_sec: int = 6):
    """
    Generate a demo classroom video with moving synthetic faces for testing
    video upload and live stream without camera hardware.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fps = 20
    total_frames = duration_sec * fps
    w, h = 640, 480

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    for f in range(total_frames):
        frame = np.full((h, w, 3), (35, 30, 28), dtype=np.uint8)

        # Classroom blackboard
        cv2.rectangle(frame, (40, 30), (600, 140), (25, 45, 30), -1)
        cv2.rectangle(frame, (40, 30), (600, 140), (70, 90, 70), 3)
        cv2.putText(frame, "CS301: AI Vision Lecture", (180, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (230, 230, 230), 2)

        # Student 1: moving gently left-right
        x1 = int(180 + 25 * np.sin(f * 0.08))
        y1 = 260
        cv2.ellipse(frame, (x1, y1), (45, 60), 0, 0, 360, (180, 210, 240), -1)
        cv2.circle(frame, (x1 - 15, y1 - 10), 5, (20, 20, 20), -1)
        cv2.circle(frame, (x1 + 15, y1 - 10), 5, (20, 20, 20), -1)
        cv2.ellipse(frame, (x1, y1 + 20), (15, 8), 0, 0, 180, (50, 50, 120), 2)

        # Student 2: seated on right
        x2 = int(460 + 15 * np.cos(f * 0.06))
        y2 = 270
        cv2.ellipse(frame, (x2, y2), (45, 60), 0, 0, 360, (190, 215, 240), -1)
        cv2.circle(frame, (x2 - 15, y2 - 10), 5, (20, 20, 20), -1)
        cv2.circle(frame, (x2 + 15, y2 - 10), 5, (20, 20, 20), -1)
        cv2.ellipse(frame, (x2, y2 + 20), (15, 8), 0, 0, 180, (50, 50, 120), 2)

        out.write(frame)

    out.release()
    print(f"Generated synthetic demo video at: {output_path}")


def populate_demo_data():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check existing data
        if db.query(Student).count() > 0:
            print("Existing students found in database. Skipping duplicate population.")
            return

        print("Populating sample students...")
        created_students = []
        for idx, s_data in enumerate(SAMPLE_STUDENTS):
            emb = generate_synthetic_embedding(seed=100 + idx)
            student = Student(
                student_code=s_data["student_code"],
                name=s_data["name"],
                email=s_data["email"],
                department=s_data["department"],
                year=s_data["year"],
                section=s_data["section"],
                face_embedding=json.dumps(emb)
            )
            db.add(student)
            created_students.append(student)

            # Generate synthetic portrait image file
            portrait_path = f"data/students/{s_data['student_code']}.jpg"
            generate_synthetic_portrait(s_data["name"], 42 + idx, portrait_path)

        db.commit()
        for s in created_students:
            db.refresh(s)
        print(f"Successfully created {len(created_students)} demo students with face embeddings.")

        print("Populating sample classroom sessions...")
        created_sessions = []
        for sess_data in SAMPLE_SESSIONS:
            sess = DbSession(
                name=sess_data["name"],
                subject=sess_data["subject"],
                class_name=sess_data["class_name"],
                date=sess_data["date"],
                start_time=sess_data["start_time"],
                end_time=sess_data["end_time"],
                status=sess_data["status"]
            )
            db.add(sess)
            created_sessions.append(sess)
        db.commit()
        for sess in created_sessions:
            db.refresh(sess)
        print(f"Successfully created {len(created_sessions)} classroom sessions.")

        print("Generating realistic attendance and engagement records...")
        for sess in created_sessions:
            for s_idx, stu in enumerate(created_students):
                is_present = (s_idx != 3) if sess.status == "completed" else (s_idx < 6)
                dur = random.uniform(2800, 3500) if is_present else 0.0
                conf = random.uniform(0.78, 0.94) if is_present else 0.0

                att = Attendance(
                    session_id=sess.id,
                    student_id=stu.id,
                    first_seen=utcnow() - timedelta(minutes=50) if is_present else None,
                    last_seen=utcnow() - timedelta(minutes=5) if is_present else None,
                    duration_seconds=round(dur, 1),
                    status="Present" if is_present else "Absent",
                    confidence=round(conf, 2)
                )
                db.add(att)

                # Engagement records
                if is_present:
                    for minute in range(0, 45, 5):
                        eng = Engagement(
                            session_id=sess.id,
                            student_id=stu.id,
                            tracking_id=s_idx + 1,
                            timestamp=utcnow() - timedelta(minutes=45 - minute),
                            face_visible=True,
                            orientation_score=round(random.uniform(0.70, 0.95), 2),
                            engagement_score=round(random.uniform(0.68, 0.92), 2)
                        )
                        db.add(eng)

        db.commit()
        print("Demo attendance & engagement records committed successfully.")

        # Create demo classroom video
        create_synthetic_demo_video("data/sessions/demo_classroom.mp4")

    finally:
        db.close()

    print("\n--- Demo Dataset Generation Complete ---")
    print("Total Students: 8 (All registered with synthetic embeddings)")
    print("Total Sessions: 3 (2 Completed, 1 Active)")
    print("Demo Video: data/sessions/demo_classroom.mp4")


if __name__ == "__main__":
    populate_demo_data()
