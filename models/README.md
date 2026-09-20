# Model Management & Architecture Guide

This directory holds the deep learning model weights used by the **AI Attendance & Engagement Analyzer** pipeline.

---

## 1. Required AI Models

### A. Face Detection — Ultralytics YOLOv8 Face
- **Target File:** `models/yolov8n-face.pt`
- **Architecture:** YOLOv8 Nano Face Detector (Ultralytics PyTorch)
- **Role:** High-speed, high-recall face detection across varied lighting, scale, and classroom densities.
- **Output:** Bounding box coordinates `(x1, y1, x2, y2)`, detection confidence score, and cropped face RGB tensors.
- **Auto-Download:** Automatically downloaded upon startup or via `python scripts/download_models.py`.
- **Source:** [Hugging Face arnabdhar/YOLOv8-Face-Detection](https://huggingface.co/arnabdhar/YOLOv8-Face-Detection)
- **Fallback:** If custom face weights are absent, the system automatically falls back to base `yolov8n.pt` with upper-body crop extraction.

### B. Face Recognition & Embedding — FaceNet InceptionResnetV1
- **Architecture:** Inception-ResNet-v1 (pretrained on VGGFace2)
- **Role:** Deep facial feature extraction into a 512-dimensional continuous metric space.
- **Output:** L2-normalized 512-d floating point vector.
- **Similarity Metric:** Vector Cosine Similarity:
  $$\text{sim}(u, v) = \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$
- **Identification:** Face is matched to registered identity if $\text{sim} \ge \text{FACE\_MATCH\_THRESHOLD}$ (default: `0.55`). If below threshold, categorized as `Unknown`.

### C. Multi-Object Tracking — ByteTrack
- **Role:** Temporal association across video frames.
- **Output:** Persistent unique integer tracking IDs (`#1`, `#2`, ...).
- **Optimization:** Caches recognized student identity per `track_id`. Eliminates the need to run 512-d FaceNet inference on every frame, reducing inference latency by over 70%.

---

## 2. Automated Download

To download and cache all weights ahead of time, run:

```bash
python scripts/download_models.py
```

---

## 3. Configuration (.env)

Adjust model behavior via `.env` or system environment variables:

```ini
# Path to face detection model
FACE_MODEL_PATH=models/yolov8n-face.pt

# Minimum confidence required for face detection
FACE_CONFIDENCE_THRESHOLD=0.50

# Minimum cosine similarity required to match a registered student
FACE_MATCH_THRESHOLD=0.55
```

---

## 4. Biometric Privacy & Security

- Model weights are cached locally.
- **Raw face embeddings are strictly private**: never logged, never exposed via API endpoints, and never transmitted over public networks.
- No facial recognition data or student biometrics should ever be committed to git repositories.
