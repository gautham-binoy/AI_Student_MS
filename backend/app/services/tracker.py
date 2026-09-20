import time
from typing import List, Dict, Optional, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment

from app.core.logging import logger


class Track:
    def __init__(self, track_id: int, bbox: Tuple[int, int, int, int], confidence: float):
        self.track_id = track_id
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = confidence
        
        # Identity association
        self.student_id: Optional[int] = None
        self.student_name: str = "Unknown"
        self.recognition_confidence: float = 0.0
        self.recognition_attempts: int = 0
        self.last_recognition_frame: int = 0
        
        # Temporal tracking
        self.first_seen_time: float = time.time()
        self.last_seen_time: float = time.time()
        self.consecutive_frames: int = 1
        self.total_frames: int = 1
        self.missed_frames: int = 0
        self.is_confirmed_present: bool = False
        
        # Engagement observation metrics
        self.orientation_score: float = 0.8
        self.smoothed_engagement: float = 0.5
        self.recent_orientations: List[float] = [0.8]
        self.recent_visibilities: List[float] = [1.0]

    def update(self, bbox: Tuple[int, int, int, int], confidence: float, current_frame: int):
        self.bbox = bbox
        self.confidence = confidence
        self.last_seen_time = time.time()
        self.consecutive_frames += 1
        self.total_frames += 1
        self.missed_frames = 0

    def mark_missed(self):
        self.missed_frames += 1
        self.consecutive_frames = 0


def calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
    """Compute Intersection over Union between two bounding boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return float(inter_area / union_area)


class FaceTracker:
    def __init__(self, iou_threshold: float = 0.35, max_missed_frames: int = 30):
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self.next_track_id: int = 1
        self.tracks: Dict[int, Track] = {}
        self.frame_count: int = 0

    def update(self, detections: List[Tuple[Tuple[int, int, int, int], float]]) -> List[Track]:
        """
        Update tracker with new detections.
        detections: List of (bbox, confidence)
        Returns: List of currently active matched tracks
        """
        self.frame_count += 1

        if not detections:
            # Mark all tracks missed
            expired = []
            for track_id, track in self.tracks.items():
                track.mark_missed()
                if track.missed_frames > self.max_missed_frames:
                    expired.append(track_id)
            for track_id in expired:
                del self.tracks[track_id]
            return [t for t in self.tracks.values() if t.missed_frames == 0]

        existing_track_ids = list(self.tracks.keys())
        active_tracks = [self.tracks[tid] for tid in existing_track_ids]

        if not active_tracks:
            # Create new tracks for all detections
            matched_tracks = []
            for bbox, conf in detections:
                t = Track(self.next_track_id, bbox, conf)
                self.tracks[self.next_track_id] = t
                matched_tracks.append(t)
                self.next_track_id += 1
            return matched_tracks

        # Cost matrix based on 1 - IoU
        num_tracks = len(active_tracks)
        num_dets = len(detections)
        cost_matrix = np.ones((num_tracks, num_dets), dtype=np.float32)

        for i, track in enumerate(active_tracks):
            for j, (det_bbox, _) in enumerate(detections):
                iou = calculate_iou(track.bbox, det_bbox)
                cost_matrix[i, j] = 1.0 - iou

        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        matched_track_indices = set()
        matched_det_indices = set()

        for r, c in zip(row_indices, col_indices):
            iou = 1.0 - cost_matrix[r, c]
            if iou >= self.iou_threshold:
                track = active_tracks[r]
                det_bbox, det_conf = detections[c]
                track.update(det_bbox, det_conf, self.frame_count)
                matched_track_indices.add(r)
                matched_det_indices.add(c)

        # Unmatched tracks
        for r, track in enumerate(active_tracks):
            if r not in matched_track_indices:
                track.mark_missed()

        # Unmatched detections -> create new tracks
        for c, (det_bbox, det_conf) in enumerate(detections):
            if c not in matched_det_indices:
                new_track = Track(self.next_track_id, det_bbox, det_conf)
                self.tracks[self.next_track_id] = new_track
                self.next_track_id += 1

        # Remove dead tracks
        expired = [tid for tid, trk in self.tracks.items() if trk.missed_frames > self.max_missed_frames]
        for tid in expired:
            del self.tracks[tid]

        return [t for t in self.tracks.values() if t.missed_frames == 0]

    def should_run_recognition(self, track: Track) -> bool:
        """
        Determine if face recognition should run for this track:
        1. Brand new track (never recognized yet)
        2. Was 'Unknown' and has been observed for several frames
        3. Periodic re-check every 60 frames (~2-3s) to confirm identity
        """
        if track.student_id is None and track.recognition_attempts < 5:
            return True
        if track.student_id is not None and (self.frame_count - track.last_recognition_frame) >= 60:
            return True
        return False
