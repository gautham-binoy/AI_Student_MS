import time
from typing import Optional, Tuple, List
import numpy as np
import cv2
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.database.models import Engagement
from app.services.tracker import Track


class EngagementEstimator:
    """
    Computes an observable, visual-signal-based Engagement Estimate.
    DISCLAIMER: This metric is purely an observable computer-vision estimate
    derived from facial orientation, detection clarity, and presence duration.
    It does not measure psychological attention, internal focus, or cognitive state.
    """

    def __init__(
        self,
        weight_orientation: Optional[float] = None,
        weight_visibility: Optional[float] = None,
        weight_presence: Optional[float] = None,
        smoothing_alpha: float = 0.25
    ):
        self.w_orient = weight_orientation or settings.ENGAGEMENT_ORIENTATION_WEIGHT
        self.w_vis = weight_visibility or settings.ENGAGEMENT_VISIBILITY_WEIGHT
        self.w_pres = weight_presence or settings.ENGAGEMENT_PRESENCE_WEIGHT
        self.smoothing_alpha = smoothing_alpha

    def estimate_orientation(self, face_crop: Optional[np.ndarray], bbox: Tuple[int, int, int, int]) -> float:
        """
        Estimate orientation score based on geometric aspect ratio and bilateral facial symmetry.
        1.0: Facing directly forward towards camera/instructor
        0.6: Moderately turned
        0.2: Strongly turned away / profile view
        """
        if face_crop is None or face_crop.size == 0:
            return 0.3

        x1, y1, x2, y2 = bbox
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        aspect_ratio = w / float(h)

        # Frontal human faces typically have aspect ratio around 0.70 - 0.90
        # Extreme profile faces narrow down below 0.55
        if 0.68 <= aspect_ratio <= 0.95:
            aspect_score = 0.95
        elif 0.55 <= aspect_ratio < 0.68 or 0.95 < aspect_ratio <= 1.15:
            aspect_score = 0.70
        else:
            aspect_score = 0.40

        # Bilateral symmetry analysis via left/right image halves
        try:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            gh, gw = gray.shape
            mid = gw // 2
            if mid > 10:
                left_half = gray[:, :mid]
                right_half = cv2.flip(gray[:, mid:2*mid], 1)
                # Compute normalized cross-correlation
                res = cv2.matchTemplate(left_half, right_half, cv2.TM_CCOEFF_NORMED)
                sym_score = float(np.clip(res[0][0], 0.0, 1.0))
            else:
                sym_score = 0.7
        except Exception:
            sym_score = 0.7

        orientation_score = 0.6 * aspect_score + 0.4 * sym_score
        return float(np.clip(orientation_score, 0.1, 1.0))

    def compute_engagement(
        self,
        track: Track,
        face_crop: Optional[np.ndarray],
        current_session_duration: float = 60.0
    ) -> float:
        """
        Calculates the observable engagement estimate for a track using weighted multi-modal CV signals
        and applies exponential temporal smoothing.
        """
        # 1. Orientation score
        orient_score = self.estimate_orientation(face_crop, track.bbox)
        track.orientation_score = orient_score
        track.recent_orientations.append(orient_score)
        if len(track.recent_orientations) > 30:
            track.recent_orientations.pop(0)

        # 2. Visibility score based on detection confidence and bounding box size
        x1, y1, x2, y2 = track.bbox
        box_area = (x2 - x1) * (y2 - y1)
        size_factor = min(1.0, box_area / 4000.0)  # penalize tiny indistinct faces
        vis_score = float(np.clip(track.confidence * 0.7 + size_factor * 0.3, 0.1, 1.0))
        track.recent_visibilities.append(vis_score)
        if len(track.recent_visibilities) > 30:
            track.recent_visibilities.pop(0)

        # 3. Presence score
        observed_time = track.last_seen_time - track.first_seen_time
        pres_score = float(np.clip(observed_time / max(10.0, current_session_duration), 0.2, 1.0))

        # Weighted combination
        raw_score = (
            self.w_orient * orient_score +
            self.w_vis * vis_score +
            self.w_pres * pres_score
        )

        # Temporal smoothing (Exponential Moving Average)
        smoothed = (self.smoothing_alpha * raw_score) + ((1.0 - self.smoothing_alpha) * track.smoothed_engagement)
        track.smoothed_engagement = float(np.clip(smoothed, 0.05, 1.0))

        return track.smoothed_engagement

    def record_engagement_sample(
        self,
        db: Session,
        session_id: int,
        student_id: Optional[int],
        tracking_id: int,
        track: Track
    ):
        """Persist periodic engagement sample to database."""
        try:
            sample = Engagement(
                session_id=session_id,
                student_id=student_id,
                tracking_id=tracking_id,
                face_visible=True,
                orientation_score=round(track.orientation_score, 3),
                engagement_score=round(track.smoothed_engagement, 3)
            )
            db.add(sample)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error persisting engagement sample: {e}")
