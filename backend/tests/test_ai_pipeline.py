import time
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.database.models import Student, Session as DbSession, Attendance
from app.services.face_detector import FaceDetector, FaceDetection
from app.services.face_recognition import FaceRecognizer
from app.services.tracker import FaceTracker, Track, calculate_iou
from app.services.attendance import AttendanceService
from app.services.engagement import EngagementEstimator


def test_cosine_similarity():
    vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_c = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    vec_d = np.array([-1.0, 0.0, 0.0], dtype=np.float32)

    # Identical
    assert pytest.approx(FaceRecognizer.cosine_similarity(vec_a, vec_b), 0.001) == 1.0
    # Orthogonal
    assert pytest.approx(FaceRecognizer.cosine_similarity(vec_a, vec_c), 0.001) == 0.0
    # Opposite
    assert pytest.approx(FaceRecognizer.cosine_similarity(vec_a, vec_d), 0.001) == -1.0
    # None handling
    assert FaceRecognizer.cosine_similarity(None, vec_a) == 0.0


def test_face_matching_threshold():
    recognizer = FaceRecognizer(match_threshold=0.60)
    student_emb = np.array([0.6, 0.8, 0.0], dtype=np.float32)
    registered = [
        {"id": 1, "name": "Registered Student", "embedding": student_emb}
    ]

    # Similar query (cosine sim > 0.60)
    query_match = np.array([0.65, 0.75, 0.0], dtype=np.float32)
    sid, sname, sim = recognizer.match_face(query_match, registered, threshold=0.60)
    assert sid == 1
    assert sname == "Registered Student"
    assert sim >= 0.60

    # Unknown query (orthogonal / distinct)
    query_unknown = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    sid, sname, sim = recognizer.match_face(query_unknown, registered, threshold=0.60)
    assert sid is None
    assert sname == "Unknown"
    assert sim < 0.60


def test_tracker_persistence():
    tracker = FaceTracker(iou_threshold=0.3)
    
    # Frame 1: face at (100, 100, 200, 200)
    dets_f1 = [((100, 100, 200, 200), 0.95)]
    tracks1 = tracker.update(dets_f1)
    assert len(tracks1) == 1
    t1_id = tracks1[0].track_id

    # Frame 2: face moves slightly to (105, 102, 205, 202)
    dets_f2 = [((105, 102, 205, 202), 0.92)]
    tracks2 = tracker.update(dets_f2)
    assert len(tracks2) == 1
    # Track ID MUST persist!
    assert tracks2[0].track_id == t1_id
    assert tracks2[0].consecutive_frames == 2


def test_temporal_attendance_confirmation():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    att_service = AttendanceService(min_confirmation_seconds=1.5)

    track = Track(track_id=1, bbox=(50, 50, 150, 150), confidence=0.90)
    session_id = 99
    student_id = 42

    # 1. Transient appearance (< 1.5 seconds)
    track.first_seen_time = time.time()
    track.last_seen_time = track.first_seen_time + 0.5  # only 0.5 seconds
    res1 = att_service.process_track_observation(db, session_id, student_id, track, 0.90)
    # Must NOT mark present yet
    assert res1 is None
    assert track.is_confirmed_present is False

    # 2. Confirmed appearance (>= 1.5 seconds)
    track.last_seen_time = track.first_seen_time + 2.0  # 2.0 seconds
    res2 = att_service.process_track_observation(db, session_id, student_id, track, 0.90)
    assert res2 is not None
    assert res2.status == "Present"
    assert track.is_confirmed_present is True

    # 3. Disappearance and reappearance: verify same record updated, no duplicate created
    prev_id = res2.id
    time.sleep(0.01)
    track.last_seen_time = time.time() + 10.0
    res3 = att_service.process_track_observation(db, session_id, student_id, track, 0.95)
    assert res3.id == prev_id
    assert res3.status == "Present"
    # Ensure count in DB is strictly 1
    total_records = db.query(Attendance).filter(Attendance.session_id == session_id, Attendance.student_id == student_id).count()
    assert total_records == 1


def test_engagement_orientation_and_smoothing():
    estimator = EngagementEstimator(weight_orientation=0.5, weight_visibility=0.3, weight_presence=0.2, smoothing_alpha=0.3)
    track = Track(track_id=1, bbox=(100, 100, 180, 200), confidence=0.95)

    # Synthetic frontal face (aspect ratio 80/100 = 0.80)
    synthetic_frontal = np.full((100, 80, 3), 200, dtype=np.uint8)
    score1 = estimator.compute_engagement(track, synthetic_frontal, current_session_duration=60.0)
    assert 0.0 < score1 <= 1.0

    # Extreme profile box (aspect ratio 30/100 = 0.30)
    track.bbox = (100, 100, 130, 200)
    synthetic_profile = np.full((100, 30, 3), 150, dtype=np.uint8)
    synthetic_profile[:, :10] = 50  # asymmetric profile shadow
    orient_profile = estimator.estimate_orientation(synthetic_profile, track.bbox)
    assert orient_profile < 0.65  # Turned away score is lower

    # Smoothing check: score gradually adjusts rather than instant jump
    prev_eng = track.smoothed_engagement
    score2 = estimator.compute_engagement(track, synthetic_profile, current_session_duration=60.0)
    # EMA smoothing formula prevents instant jump to raw score
    assert abs(score2 - prev_eng) < 0.5


def test_empty_frame_handling():
    detector = FaceDetector.get_instance()
    # Empty frame
    assert detector.detect(None) == []
    assert detector.detect(np.array([])) == []
    # Black blank image without faces
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    res = detector.detect(blank)
    assert isinstance(res, list)
