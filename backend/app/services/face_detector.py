import os
import urllib.request
from typing import List, Tuple, Optional
import numpy as np
import cv2
from ultralytics import YOLO

from app.core.config import settings
from app.core.logging import logger


class FaceDetection:
    def __init__(self, bbox: Tuple[int, int, int, int], confidence: float, crop: np.ndarray, landmarks: Optional[np.ndarray] = None):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = float(confidence)
        self.crop = crop  # BGR numpy array
        self.landmarks = landmarks  # Optional 5 landmarks (eyes, nose, mouth corners)


class FaceDetector:
    _instance: Optional["FaceDetector"] = None

    def __init__(self, model_path: Optional[str] = None, conf_threshold: Optional[float] = None):
        self.model_path = model_path or settings.FACE_MODEL_PATH
        self.conf_threshold = conf_threshold or settings.FACE_CONFIDENCE_THRESHOLD
        self.model: Optional[YOLO] = None
        self._load_model()

    @classmethod
    def get_instance(cls) -> "FaceDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_model_file(self):
        if os.path.exists(self.model_path):
            return

        os.makedirs(os.path.dirname(self.model_path) or ".", exist_ok=True)
        # Attempt to download known YOLO face weights if not present
        weights_url = "https://huggingface.co/arnabdhar/YOLOv8-Face-Detection/resolve/main/model.pt"
        logger.info(f"YOLO Face model not found at '{self.model_path}'. Attempting download from {weights_url}...")
        try:
            req = urllib.request.Request(weights_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(self.model_path, "wb") as out_file:
                out_file.write(resp.read())
            logger.info(f"Downloaded YOLO face model to '{self.model_path}' successfully.")
        except Exception as e:
            logger.warning(f"Could not download custom YOLO face model: {e}. Falling back to standard YOLOv8n detector.")
            self.model_path = "yolov8n.pt"

    def _load_model(self):
        try:
            self._ensure_model_file()
            logger.info(f"Loading Ultralytics YOLO model from '{self.model_path}'...")
            self.model = YOLO(self.model_path)
            logger.info("FaceDetector loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}. Falling back to yolov8n.pt")
            self.model = YOLO("yolov8n.pt")

    def detect(self, frame: np.ndarray) -> List[FaceDetection]:
        """
        Detect faces in a BGR image frame using Ultralytics YOLO.
        Returns a list of FaceDetection objects containing bbox, confidence, and cropped face.
        """
        if frame is None or frame.size == 0 or self.model is None:
            return []

        h, w = frame.shape[:2]
        detections: List[FaceDetection] = []

        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                verbose=False
            )
        except Exception as e:
            logger.error(f"Error during YOLO inference: {e}")
            return []

        if not results:
            return []

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return []

        xyxy = boxes.xyxy.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        cls_ids = boxes.cls.cpu().numpy() if boxes.cls is not None else None

        for idx in range(len(xyxy)):
            box = xyxy[idx]
            conf = confs[idx]

            # If using standard YOLOv8n (detecting 'person' which is class 0), we extract face area (upper 35% of person)
            # If using a dedicated face model, class represents face directly
            if cls_ids is not None and "yolov8n.pt" in str(self.model_path) and int(cls_ids[idx]) != 0:
                continue

            x1 = max(0, int(box[0]))
            y1 = max(0, int(box[1]))
            x2 = min(w, int(box[2]))
            y2 = min(h, int(box[3]))

            # If using standard person model, approximate upper body/face region
            if "yolov8n.pt" in str(self.model_path) and not "face" in str(self.model_path):
                person_h = y2 - y1
                y2 = min(h, y1 + int(person_h * 0.35))
                # tighten width to center 60%
                person_w = x2 - x1
                x1 = max(0, x1 + int(person_w * 0.2))
                x2 = min(w, x2 - int(person_w * 0.2))

            if x2 <= x1 or y2 <= y1 or (x2 - x1) < 15 or (y2 - y1) < 15:
                continue

            crop = frame[y1:y2, x1:x2].copy()
            detections.append(FaceDetection(
                bbox=(x1, y1, x2, y2),
                confidence=float(conf),
                crop=crop
            ))

        return detections
