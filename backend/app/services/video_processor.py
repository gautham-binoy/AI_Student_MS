import time
import json
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import cv2
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.database.models import Student, Attendance, Session as DbSession
from app.services.face_detector import FaceDetector, FaceDetection
from app.services.face_recognition import FaceRecognizer
from app.services.tracker import FaceTracker, Track, calculate_iou
from app.services.attendance import AttendanceService
from app.services.engagement import EngagementEstimator


class VideoProcessor:
    _instance: Optional["VideoProcessor"] = None

    def __init__(self):
        self.detector = FaceDetector.get_instance()
        self.recognizer = FaceRecognizer.get_instance()
        self.tracker = FaceTracker()
        self.attendance_service = AttendanceService()
        self.engagement_estimator = EngagementEstimator()
        
        # Cache for registered student embeddings: [{'id': int, 'name': str, 'embedding': np.ndarray}]
        self.registered_cache: List[Dict[str, Any]] = []
        self._cache_timestamp: float = 0.0
        
        # Performance tracking
        self.prev_frame_time: float = time.time()
        self.fps: float = 0.0
        self.frame_index: int = 0

    @classmethod
    def get_instance(cls) -> "VideoProcessor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload_student_cache(self, db: Session):
        """Load and cache all registered student embeddings from database."""
        students = db.query(Student).filter(Student.face_embedding.isnot(None)).all()
        cache = []
        for s in students:
            if s.face_embedding:
                try:
                    emb_list = json.loads(s.face_embedding)
                    emb_arr = np.array(emb_list, dtype=np.float32)
                    norm = np.linalg.norm(emb_arr)
                    if norm > 0:
                        emb_arr = emb_arr / norm
                    cache.append({
                        "id": s.id,
                        "name": s.name,
                        "student_code": s.student_code,
                        "embedding": emb_arr
                    })
                except Exception as e:
                    logger.error(f"Error parsing embedding for student {s.id}: {e}")
        self.registered_cache = cache
        self._cache_timestamp = time.time()
        logger.info(f"Loaded {len(cache)} registered student embeddings into memory.")

    def reset_tracker(self):
        """Reset the tracker state for a new session or video stream."""
        self.tracker = FaceTracker()
        self.frame_index = 0

    def process_frame(
        self,
        frame: np.ndarray,
        session_id: Optional[int] = None,
        db: Optional[Session] = None,
        annotate: bool = True
    ) -> Dict[str, Any]:
        """
        Unified processing pipeline:
        Frame -> Detect -> Track -> Recognize -> Attendance -> Engagement -> Overlay
        """
        t_start = time.time()
        self.frame_index += 1

        # Calculate FPS
        t_curr = time.time()
        dt = t_curr - self.prev_frame_time
        self.prev_frame_time = t_curr
        instant_fps = 1.0 / dt if dt > 0 else 30.0
        self.fps = 0.9 * self.fps + 0.1 * instant_fps if self.fps > 0 else instant_fps

        if db is not None and (len(self.registered_cache) == 0 or time.time() - self._cache_timestamp > 60):
            self.reload_student_cache(db)

        # 1. Detection
        t_det0 = time.time()
        detections = self.detector.detect(frame)
        det_time_ms = (time.time() - t_det0) * 1000.0

        # 2. Tracking
        t_track0 = time.time()
        det_tuples = [(d.bbox, d.confidence) for d in detections]
        active_tracks = self.tracker.update(det_tuples)
        track_time_ms = (time.time() - t_track0) * 1000.0

        # Map detections to active tracks
        track_crops: Dict[int, np.ndarray] = {}
        for track in active_tracks:
            best_iou = 0.0
            best_crop = None
            for d in detections:
                iou = calculate_iou(track.bbox, d.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_crop = d.crop
            if best_crop is not None:
                track_crops[track.track_id] = best_crop

        # 3. Face Recognition (intelligent invocation: on new tracks or periodic confirmation)
        t_rec0 = time.time()
        rec_count = 0
        for track in active_tracks:
            if self.tracker.should_run_recognition(track) and track.track_id in track_crops:
                crop = track_crops[track.track_id]
                emb = self.recognizer.generate_embedding(crop)
                if emb is not None and len(self.registered_cache) > 0:
                    sid, sname, sim = self.recognizer.match_face(emb, self.registered_cache)
                    track.student_id = sid
                    track.student_name = sname
                    track.recognition_confidence = sim
                    track.last_recognition_frame = self.frame_index
                    rec_count += 1
                track.recognition_attempts += 1
        rec_time_ms = (time.time() - t_rec0) * 1000.0

        # 4. Attendance & Engagement Analysis
        present_count = 0
        recognized_count = 0
        unknown_count = 0
        engagement_scores = []
        detection_results = []

        for track in active_tracks:
            crop = track_crops.get(track.track_id)
            
            # Engagement
            eng_score = self.engagement_estimator.compute_engagement(track, crop)
            engagement_scores.append(eng_score)

            # Attendance
            is_present = track.is_confirmed_present
            if session_id is not None and db is not None and track.student_id is not None:
                att_record = self.attendance_service.process_track_observation(
                    db=db,
                    session_id=session_id,
                    student_id=track.student_id,
                    track=track,
                    confidence=track.confidence
                )
                if att_record and att_record.status == "Present":
                    is_present = True

                # Persist engagement sample every 30 frames
                if self.frame_index % 30 == 0:
                    self.engagement_estimator.record_engagement_sample(
                        db=db,
                        session_id=session_id,
                        student_id=track.student_id,
                        tracking_id=track.track_id,
                        track=track
                    )

            if track.student_id is not None:
                recognized_count += 1
                if is_present:
                    present_count += 1
            else:
                unknown_count += 1

            x1, y1, x2, y2 = track.bbox
            detection_results.append({
                "track_id": track.track_id,
                "student_id": track.student_id,
                "student_name": track.student_name,
                "confidence": round(float(track.confidence), 2),
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "orientation_score": round(track.orientation_score, 2),
                "engagement_score": round(track.smoothed_engagement, 2),
                "confirmed_present": is_present
            })

        avg_engagement = float(np.mean(engagement_scores)) if engagement_scores else 0.0
        total_time_ms = (time.time() - t_start) * 1000.0

        # 5. Annotation / Visual Overlay
        annotated_frame = None
        if annotate:
            annotated_frame = frame.copy()
            self._draw_overlay(annotated_frame, detection_results, self.fps, avg_engagement)

        return {
            "annotated_frame": annotated_frame,
            "fps": round(self.fps, 1),
            "metrics": {
                "det_ms": round(det_time_ms, 1),
                "track_ms": round(track_time_ms, 1),
                "rec_ms": round(rec_time_ms, 1),
                "total_ms": round(total_time_ms, 1),
                "recognitions_run": rec_count
            },
            "counts": {
                "active_tracks": len(active_tracks),
                "recognized": recognized_count,
                "unknown": unknown_count,
                "present": present_count,
                "total_students": len(self.registered_cache)
            },
            "avg_engagement": round(avg_engagement, 2),
            "detections": detection_results
        }

    def _draw_overlay(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        fps: float,
        avg_engagement: float
    ):
        """Draw sleek, production-grade HUD bounding boxes, tags, and stats."""
        for det in detections:
            bbox = det["bbox"]
            x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
            name = det["student_name"]
            track_id = det["track_id"]
            eng = det["engagement_score"]
            is_present = det["confirmed_present"]

            # Color scheme: Emerald green for confirmed present, Cyan for recognized, Amber for unknown
            if is_present:
                box_color = (46, 204, 113)  # Emerald
            elif name != "Unknown":
                box_color = (255, 191, 0)   # Cyan / Light Blue
            else:
                box_color = (0, 165, 255)   # Amber / Orange

            # Draw sleek corner brackets rather than plain rectangle
            line_len = max(12, int((x2 - x1) * 0.2))
            thickness = 2
            
            # Top-left
            cv2.line(frame, (x1, y1), (x1 + line_len, y1), box_color, thickness)
            cv2.line(frame, (x1, y1), (x1, y1 + line_len), box_color, thickness)
            # Top-right
            cv2.line(frame, (x2, y1), (x2 - line_len, y1), box_color, thickness)
            cv2.line(frame, (x2, y1), (x2, y1 + line_len), box_color, thickness)
            # Bottom-left
            cv2.line(frame, (x1, y2), (x1 + line_len, y2), box_color, thickness)
            cv2.line(frame, (x1, y2), (x1, y2 - line_len), box_color, thickness)
            # Bottom-right
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), box_color, thickness)
            cv2.line(frame, (x2, y2), (x2, y2 - line_len), box_color, thickness)

            # Label badge
            label = f"#{track_id} {name} | Eng: {int(eng*100)}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            (tw, th), _ = cv2.getTextSize(label, font, font_scale, 1)
            
            # Badge background
            cv2.rectangle(frame, (x1, max(0, y1 - th - 8)), (x1 + tw + 10, y1), (20, 24, 33), -1)
            cv2.rectangle(frame, (x1, max(0, y1 - th - 8)), (x1 + tw + 10, y1), box_color, 1)
            cv2.putText(frame, label, (x1 + 5, y1 - 4), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        # Header HUD status
        hud_bg = (15, 18, 26)
        cv2.rectangle(frame, (10, 10), (280, 50), hud_bg, -1)
        cv2.rectangle(frame, (10, 10), (280, 50), (60, 70, 90), 1)
        hud_text = f"FPS: {fps:.1f} | Active Tracks: {len(detections)} | Eng: {int(avg_engagement*100)}%"
        cv2.putText(frame, hud_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 240, 255), 1, cv2.LINE_AA)
