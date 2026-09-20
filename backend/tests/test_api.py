import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.database import Base, get_db
from app.database.models import Student, Session as DbSession, Attendance

# In-memory SQLite for fast, isolated testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ai_models" in data


def test_student_crud(client):
    # 1. Create student
    payload = {
        "student_code": "TEST-001",
        "name": "Jane Doe",
        "email": "jane@example.edu",
        "department": "Computer Science",
        "year": "3rd Year",
        "section": "A"
    }
    create_res = client.post("/api/students", json=payload)
    assert create_res.status_code == 201
    student = create_res.json()
    assert student["name"] == "Jane Doe"
    assert student["has_face"] is False
    assert "face_embedding" not in student  # Privacy guarantee!
    student_id = student["id"]

    # Duplicate code rejection
    dup_res = client.post("/api/students", json=payload)
    assert dup_res.status_code == 400

    # 2. Get student details
    get_res = client.get(f"/api/students/{student_id}")
    assert get_res.status_code == 200
    detail = get_res.json()
    assert detail["student_code"] == "TEST-001"
    assert detail["attendance_rate"] == 0.0

    # 3. Update student
    update_res = client.put(f"/api/students/{student_id}", json={"name": "Jane Smith"})
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Jane Smith"

    # 4. List students
    list_res = client.get("/api/students")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 5. Delete student
    del_res = client.delete(f"/api/students/{student_id}")
    assert del_res.status_code == 204

    # Verify gone
    get_res2 = client.get(f"/api/students/{student_id}")
    assert get_res2.status_code == 404


def test_session_lifecycle(client):
    # Create session
    sess_payload = {
        "name": "Math 101: Linear Algebra",
        "subject": "Mathematics",
        "class_name": "S1 Math",
        "date": "2026-09-20",
        "start_time": "10:00",
        "end_time": "11:00"
    }
    create_res = client.post("/api/sessions", json=sess_payload)
    assert create_res.status_code == 201
    session = create_res.json()
    assert session["status"] == "scheduled"
    sess_id = session["id"]

    # Start session
    start_res = client.post(f"/api/sessions/{sess_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "active"

    # Stop session
    stop_res = client.post(f"/api/sessions/{sess_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "completed"


def test_duplicate_attendance_prevention(client):
    # Create student and session
    stu_res = client.post("/api/students", json={
        "student_code": "AT-001",
        "name": "Alice Bob",
        "department": "ECE"
    })
    stu_id = stu_res.json()["id"]

    sess_res = client.post("/api/sessions", json={
        "name": "Robotics Lab",
        "date": "2026-09-20"
    })
    sess_id = sess_res.json()["id"]

    # Directly verify database uniqueness constraint
    db = TestingSessionLocal()
    att1 = Attendance(
        session_id=sess_id,
        student_id=stu_id,
        status="Present",
        duration_seconds=100.0,
        confidence=0.9
    )
    db.add(att1)
    db.commit()

    # Query attendance
    att_list_res = client.get(f"/api/attendance?session_id={sess_id}")
    assert att_list_res.status_code == 200
    records = att_list_res.json()
    assert len(records) == 1
    assert records[0]["status"] == "Present"

    # Export CSV
    csv_res = client.get(f"/api/attendance/export/csv?session_id={sess_id}")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Alice Bob" in csv_res.text


def test_analytics_overview(client):
    res = client.get("/api/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_students" in data
    assert "avg_attendance_rate" in data
    assert "avg_engagement_score" in data
    assert "engagement_distribution" in data
