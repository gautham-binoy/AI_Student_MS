import json
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import cv2
import torch
from app.core.config import settings
from app.core.logging import logger


class FaceRecognizer:
    _instance: Optional["FaceRecognizer"] = None

    def __init__(self, match_threshold: Optional[float] = None):
        self.match_threshold = match_threshold or settings.FACE_MATCH_THRESHOLD
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self._load_model()

    @classmethod
    def get_instance(cls) -> "FaceRecognizer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_model(self):
        try:
            from facenet_pytorch import InceptionResnetV1
            logger.info("Initializing FaceNet InceptionResnetV1 (vggface2)...")
            self.model = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)
            logger.info(f"FaceNet loaded on device: {self.device}")
        except Exception as e:
            logger.error(f"Could not load InceptionResnetV1: {e}. Using fallback feature extractor.")
            self.model = None

    def generate_embedding(self, face_crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract a normalized 512-d face embedding vector from a cropped face image.
        """
        if face_crop is None or face_crop.size == 0:
            return None

        # Preprocessing: resize to 160x160 RGB
        try:
            rgb_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb_crop, (160, 160), interpolation=cv2.INTER_LINEAR)
        except Exception as e:
            logger.error(f"Error resizing face crop: {e}")
            return None

        if self.model is not None:
            try:
                # Standardize to [-1, 1]
                tensor = torch.from_numpy(resized).permute(2, 0, 1).float()
                tensor = (tensor - 127.5) / 128.0
                tensor = tensor.unsqueeze(0).to(self.device)

                with torch.no_grad():
                    embedding = self.model(tensor).cpu().numpy().flatten()

                # L2 normalize
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                return embedding.astype(np.float32)
            except Exception as e:
                logger.error(f"FaceNet inference error: {e}. Using fallback embedding.")

        # Fallback 512-dim embedding using multi-channel gradient & spatial histograms
        return self._fallback_embedding(resized)

    def _fallback_embedding(self, rgb_crop: np.ndarray) -> np.ndarray:
        """Lightweight spatial & gradient histogram embedding as fallback."""
        gray = cv2.cvtColor(rgb_crop, cv2.COLOR_RGB2GRAY)
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy)
        
        # 16x16 grid histograms = 256 + color stats = 512
        grid_feats = []
        for i in range(4):
            for j in range(4):
                cell_m = mag[i*40:(i+1)*40, j*40:(j+1)*40]
                cell_a = ang[i*40:(i+1)*40, j*40:(j+1)*40]
                hist, _ = np.histogram(cell_a, bins=16, range=(0, 2*np.pi), weights=cell_m)
                grid_feats.extend(hist)
        
        # Color moments
        color_feats = []
        for c in range(3):
            ch = rgb_crop[:, :, c].astype(np.float32)
            color_feats.extend([np.mean(ch), np.std(ch), np.median(ch)])
        
        combined = np.array(grid_feats + color_feats, dtype=np.float32)
        if len(combined) < 512:
            combined = np.pad(combined, (0, 512 - len(combined)))
        else:
            combined = combined[:512]
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        return combined

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two normalized vectors."""
        if emb1 is None or emb2 is None:
            return 0.0
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    def match_face(
        self,
        query_embedding: np.ndarray,
        registered_students: List[Dict[str, Any]],
        threshold: Optional[float] = None
    ) -> Tuple[Optional[int], str, float]:
        """
        Compare query embedding against registered students.
        registered_students is a list of dicts: [{'id': int, 'name': str, 'embedding': np.ndarray}, ...]
        Returns: (student_id, student_name, similarity)
        If similarity < threshold, returns (None, 'Unknown', similarity).
        """
        match_thresh = threshold if threshold is not None else self.match_threshold

        if query_embedding is None or not registered_students:
            return None, "Unknown", 0.0

        best_sim = -1.0
        best_student = None

        for student in registered_students:
            reg_emb = student.get("embedding")
            if reg_emb is None:
                continue
            sim = self.cosine_similarity(query_embedding, reg_emb)
            if sim > best_sim:
                best_sim = sim
                best_student = student

        if best_sim >= match_thresh and best_student is not None:
            return best_student["id"], best_student["name"], round(float(best_sim), 4)

        return None, "Unknown", max(0.0, round(float(best_sim), 4))
