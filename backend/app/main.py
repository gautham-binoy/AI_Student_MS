from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.database import engine, Base, SessionLocal
from app.api import students, sessions, attendance, analytics, live
from app.services.face_detector import FaceDetector
from app.services.face_recognition import FaceRecognizer
from app.services.video_processor import VideoProcessor

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager:
    1. Initialize database schema
    2. Load AI models once at startup
    3. Warm up VideoProcessor and student embedding cache
    """
    logger.info("Initializing AI Attendance & Engagement Analyzer backend...")
    
    # 1. Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized.")

    # 2. Warm up AI/CV models
    try:
        FaceDetector.get_instance()
        FaceRecognizer.get_instance()
        with SessionLocal() as db:
            VideoProcessor.get_instance().reload_student_cache(db)
        logger.info("AI/CV pipeline services initialized and ready.")
    except Exception as e:
        logger.error(f"Error initializing AI services: {e}")

    yield

    logger.info("Shutting down AI Attendance & Engagement Analyzer backend.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade AI Classroom Attendance & Observable Engagement Estimation System using YOLO, FaceNet, and ByteTrack.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],  # Permissive for local dev/preview
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"])
def health_check():
    """System health check endpoint."""
    detector_loaded = FaceDetector.get_instance().model is not None
    recognizer_loaded = FaceRecognizer.get_instance().model is not None
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected",
        "ai_models": {
            "face_detector": "loaded" if detector_loaded else "fallback",
            "face_recognizer": "loaded" if recognizer_loaded else "fallback"
        }
    }


# Include API Routers
app.include_router(students.router, prefix=settings.API_V1_PREFIX)
app.include_router(sessions.router, prefix=settings.API_V1_PREFIX)
app.include_router(attendance.router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
app.include_router(live.router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred. Please check server logs."}
    )
