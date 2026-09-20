import time
import base64
import json
import os
import shutil
import tempfile
from typing import Optional
import numpy as np
import cv2
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database.database import get_db, SessionLocal
from app.database.models import Session as DbSession, Student
from app.services.video_processor import VideoProcessor
from app.core.logging import logger

router = APIRouter(tags=["Live & Inference"])


@router.post("/inference/image")
async def infer_single_image(
    file: UploadFile = File(...),
    session_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Run the unified detection, recognition, and engagement estimation pipeline on a single image.
    Returns detected students, bounding boxes, confidence, engagement metrics,
    and base64-encoded annotated image.
    """
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid or unreadable image file.")

    processor = VideoProcessor.get_instance()
    results = processor.process_frame(image, session_id=session_id, db=db, annotate=True)

    # Convert annotated image to base64 JPEG
    annotated = results.get("annotated_frame")
    b64_image = None
    if annotated is not None:
        _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64_image = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

    return {
        "success": True,
        "metrics": results["metrics"],
        "counts": results["counts"],
        "avg_engagement": results["avg_engagement"],
        "detections": results["detections"],
        "annotated_image": b64_image
    }


@router.post("/inference/video")
async def process_video_upload(
    file: UploadFile = File(...),
    session_id: int = Form(...),
    frame_skip: int = Form(2),
    db: Session = Depends(get_db)
):
    """
    Process an uploaded classroom video file.
    Runs tracking, recognition, temporal attendance confirmation, and engagement recording.
    """
    session = db.query(DbSession).filter(DbSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    suffix = os.path.splitext(file.filename or "video.mp4")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_video:
        temp_path = temp_video.name
        shutil.copyfileobj(file.file, temp_video)

    cap = cv2.VideoCapture(temp_path)
    if not cap.isOpened():
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=400, detail="Could not decode video file.")

    processor = VideoProcessor.get_instance()
    processor.reset_tracker()
    processor.reload_student_cache(db)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    processed_count = 0
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if frame_idx % frame_skip != 0:
                continue

            # Resize frame if overly high resolution for fast processing
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280.0 / w
                frame = cv2.resize(frame, (1280, int(h * scale)))

            processor.process_frame(frame, session_id=session_id, db=db, annotate=False)
            processed_count += 1
            if processed_count > 1000:  # Safety upper limit for single upload
                break
    finally:
        cap.release()
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "success": True,
        "session_id": session_id,
        "total_video_frames": total_frames,
        "frames_processed": processed_count,
        "message": f"Successfully processed {processed_count} frames and updated session attendance."
    }


@router.websocket("/live")
async def websocket_live_endpoint(websocket: WebSocket):
    """
    Bi-directional real-time WebSocket for live classroom camera streaming.
    Receives base64 frames or camera commands, runs CV pipeline,
    and broadcasts detection bounding boxes, tracking metrics, attendance, and engagement.
    """
    await websocket.accept()
    logger.info("WebSocket live client connected.")
    processor = VideoProcessor.get_instance()

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                msg = json.loads(data_text)
            except Exception:
                continue

            action = msg.get("action", "frame")

            if action == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
                continue

            if action == "reset":
                processor.reset_tracker()
                await websocket.send_text(json.dumps({"type": "reset_ack"}))
                continue

            if action == "frame":
                session_id = msg.get("session_id")
                img_data = msg.get("image")
                include_annotated = msg.get("include_annotated", False)

                if not img_data:
                    continue

                # Strip data URL header if present
                if "," in img_data:
                    img_data = img_data.split(",", 1)[1]

                try:
                    img_bytes = base64.b64decode(img_data)
                    np_arr = np.frombuffer(img_bytes, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                except Exception as e:
                    logger.error(f"Error decoding WebSocket frame: {e}")
                    continue

                if frame is None:
                    continue

                # Open a localized DB session for thread safety
                with SessionLocal() as db:
                    results = processor.process_frame(
                        frame=frame,
                        session_id=session_id,
                        db=db,
                        annotate=include_annotated
                    )

                annotated_b64 = None
                if include_annotated and results.get("annotated_frame") is not None:
                    _, buf = cv2.imencode(".jpg", results["annotated_frame"], [cv2.IMWRITE_JPEG_QUALITY, 80])
                    annotated_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf).decode('utf-8')}"

                response_payload = {
                    "type": "frame_update",
                    "session_id": session_id,
                    "timestamp": time.strftime("%H:%M:%S"),
                    "fps": results["fps"],
                    "metrics": results["metrics"],
                    "counts": results["counts"],
                    "avg_engagement": results["avg_engagement"],
                    "detections": results["detections"],
                    "annotated_image": annotated_b64
                }
                await websocket.send_text(json.dumps(response_payload))

    except WebSocketDisconnect:
        logger.info("WebSocket live client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
